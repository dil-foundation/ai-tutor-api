import asyncio
import json
import base64
import websockets
import os
import struct
from typing import Dict, Any
from fastapi import WebSocket, WebSocketDisconnect, APIRouter
from app.services.audio_utils import validate_and_convert_audio
import logging
from pydub import AudioSegment
import io
import base64


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def convert_pcm_to_mp3(pcm_bytes: bytes, sample_rate=16000) -> str:
    audio_segment = AudioSegment(
        data=pcm_bytes,
        sample_width=2,      # 16-bit
        frame_rate=sample_rate,
        channels=1           # Mono
    )
    
    mp3_buffer = io.BytesIO()
    audio_segment.export(mp3_buffer, format="mp3")
    mp3_bytes = mp3_buffer.getvalue()
    
    return base64.b64encode(mp3_bytes).decode('utf-8')

class RealtimeConversationManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.openai_connections: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.audio_buffers: Dict[str, bytes] = {}
        
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"Client {client_id} connected to realtime conversation")
        
        # Initialize OpenAI WebSocket connection
        await self._connect_to_openai(client_id)
        
    async def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        if client_id in self.openai_connections:
            await self.openai_connections[client_id].close()
            del self.openai_connections[client_id]
        if client_id in self.audio_buffers:
            del self.audio_buffers[client_id]
        logger.info(f"Client {client_id} disconnected from realtime conversation")
        
    async def _connect_to_openai(self, client_id: str):
        """Connect to OpenAI Realtime API"""
        try:
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if not openai_api_key:
                logger.error("OPENAI_API_KEY not found in environment variables")
                return
                
            # Connect to OpenAI Realtime API
            openai_ws_url = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2025-06-03"
            headers = {
                "Authorization": f"Bearer {openai_api_key}",
                "OpenAI-Beta": "realtime=v1"
            }
            
            openai_ws = await websockets.connect(
                openai_ws_url,
                additional_headers=headers
            )
            
            self.openai_connections[client_id] = openai_ws
            logger.info(f"Connected to OpenAI Realtime API for client {client_id}")
            
            # Send initial session configuration
            await self._send_session_update(client_id)
            
            # Start listening for OpenAI messages
            asyncio.create_task(self._handle_openai_messages(client_id))
            
        except Exception as e:
            logger.error(f"Failed to connect to OpenAI Realtime API: {e}")
            
    async def _send_session_update(self, client_id: str):
        """Send initial session configuration"""
        try:
            session_update = {
                "type": "session.update",
                "session": {
                    "modalities": ["audio", "text"],
                    "input_audio_format": "pcm16",
                    "output_audio_format": "pcm16",
                    "instructions": "You are a helpful English tutor. Help the user improve their English speaking skills through natural conversation. Be encouraging and provide gentle corrections when needed.",
                    "voice": "echo"
                }
            }
            
            if client_id in self.openai_connections:
                openai_ws = self.openai_connections[client_id]
                await openai_ws.send(json.dumps(session_update))
                logger.info(f"Sent session update for client {client_id}")
                
        except Exception as e:
            logger.error(f"Error sending session update: {e}")
            
    async def _handle_openai_messages(self, client_id: str):
        """Handle messages from OpenAI Realtime API"""
        try:
            openai_ws = self.openai_connections.get(client_id)
            if not openai_ws:
                logger.error(f"❌ [OPENAI] No OpenAI WebSocket found for client {client_id}")
                return
                
            logger.info(f"🔄 [OPENAI] Starting message listener for client {client_id}")
            async for message in openai_ws:
                try:
                    data = json.loads(message)
                    event_type = data.get('type', 'unknown')
                    logger.info(f"🤖 [OPENAI] Received from OpenAI: {event_type}")
                    
                    # Log specific event details
                    if event_type == 'response.created':
                        logger.info(f"🤖 [OPENAI] Response created: {data}")
                    elif event_type == 'response.text.delta':
                        logger.info(f"🤖 [OPENAI] Text delta: {data.get('response', {}).get('output', [{}])[0].get('text', '')}")
                    elif event_type == 'response.audio.delta':
                        raw_base64 = data.get("delta", "")
                        if raw_base64:
                            try:
                                pcm_bytes = base64.b64decode(raw_base64)
                                mp3_base64 = convert_pcm_to_mp3(pcm_bytes)

                                # ✅ Send MP3-encoded audio
                                if client_id in self.active_connections:
                                    await self.active_connections[client_id].send_json({
                                        "type": "audio",
                                        "data": mp3_base64
                                    })
                                    logger.info(f"📤 [OPENAI] Forwarded MP3 audio to client {client_id}")
                            except Exception as e:
                                logger.error(f"❌ [AUDIO] Failed to convert/send MP3 audio: {e}")

                        # ❌ Do not forward the original PCM message
                        continue
                    elif event_type == 'response.done':
                        logger.info(f"🤖 [OPENAI] Response done: {data}")
                    elif event_type == 'error':
                        logger.error(f"❌ [OPENAI] Error from OpenAI: {data}")
                    
                    # Forward the message to the client
                    # Only forward non-audio-delta events to the frontend
                    if event_type != 'response.audio.delta':
                        if client_id in self.active_connections:
                            await self.active_connections[client_id].send_text(message)
                            logger.info(f"📤 [OPENAI] Forwarded {event_type} to client {client_id}")
                    else:
                        logger.error(f"❌ [OPENAI] No active client connection for {client_id}")
                        
                except json.JSONDecodeError:
                    logger.error(f"❌ [OPENAI] Failed to parse OpenAI message as JSON: {message[:100]}...")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"🔄 [OPENAI] OpenAI WebSocket connection closed for client {client_id}")
        except Exception as e:
            logger.error(f"❌ [OPENAI] Error handling OpenAI messages for client {client_id}: {e}")
            import traceback
            logger.error(f"❌ [OPENAI] Traceback: {traceback.format_exc()}")
            
    async def handle_client_message(self, client_id: str, message: str):
        """Handle messages from the client"""
        try:
            data = json.loads(message)
            message_type = data.get('type')
            
            logger.info(f"📨 [CLIENT] Received client message type: {message_type} from client {client_id}")
            logger.info(f"📨 [CLIENT] Message content: {message[:200]}...")  # Log first 200 chars
            
            if message_type == 'input_audio':
                if client_id in self.openai_connections:
                    audio_base64 = data.get("audio")
                    print("audio_base64 of mk: ",audio_base64[:10])
                    # Check for missing or empty audio payload
                    if not audio_base64:
                        logger.warning(f"⚠️ [CLIENT] Received empty or missing audio payload for client {client_id}")
                        return

                    try:
                        audio_bytes = base64.b64decode(audio_base64)
                    except Exception as e:
                        logger.error(f"❌ [CLIENT] Failed to decode audio for client {client_id}: {e}")
                        return

                    # Log how much audio was received
                    logger.info(f"🎤 [CLIENT] Decoded {len(audio_bytes)} bytes of audio for client {client_id}")
                    logger.debug(f"📦 [CLIENT] base64 starts with: {audio_base64[:10]}...")

                    # Append to buffer
                    if client_id not in self.audio_buffers:
                        self.audio_buffers[client_id] = b''
                    self.audio_buffers[client_id] += audio_bytes

                    logger.info(f"🎧 [CLIENT] Buffered total: {len(self.audio_buffers[client_id])} bytes")

                    
                return  # Do not forward original message


            # Handle audio buffer commit specially
            if message_type == 'input_audio_buffer.commit':
                logger.info(f"🎤 [CLIENT] Committing audio buffer for client {client_id}")
                
                # Send accumulated audio data to OpenAI first
                if client_id in self.openai_connections:
                    openai_ws = self.openai_connections[client_id]
                    
                    if client_id in self.audio_buffers and len(self.audio_buffers[client_id]) > 0:
                        buffer_size = len(self.audio_buffers[client_id])
                        logger.info(f"🎤 [CLIENT] Sending accumulated audio data: {buffer_size} bytes")
                        
                        # ✅ Convert and validate audio before sending
                        try:
                            converted_audio = validate_and_convert_audio(self.audio_buffers[client_id])
                            logger.info(f"✅ [AUDIO] Audio successfully validated and converted (length: {len(converted_audio)} bytes)")
                        except ValueError as ve:
                            logger.error(f"❌ [AUDIO] Audio validation/conversion failed: {ve}")
                            return  # Skip sending if audio is invalid

                        # Encode converted audio as base64
                        audio_base64 = base64.b64encode(converted_audio).decode('utf-8')
                        logger.info(f"🎤 [CLIENT] Encoded converted audio to base64, length: {len(audio_base64)} characters")
                        
                        # Create input_audio_buffer.append event
                        append_event = {
                            "type": "input_audio_buffer.append",
                            "audio": audio_base64
                        }
                        
                        # Send append event to OpenAI
                        await openai_ws.send(json.dumps(append_event))
                        logger.info(f"🎤 [CLIENT] Sent input_audio_buffer.append to OpenAI")
                        
                        # Now send the commit message
                        await openai_ws.send(message)
                        logger.info(f"🎤 [CLIENT] Sent input_audio_buffer.commit to OpenAI")
                        
                        # Clear the buffer after sending
                        self.audio_buffers[client_id] = b''
                        logger.info(f"🎤 [CLIENT] Cleared audio buffer after sending")
                    else:
                        logger.warning(f"🎤 [CLIENT] No audio buffer found for client {client_id}")
                        # Still send the commit message even if no audio
                        await openai_ws.send(message)
                        logger.info(f"🎤 [CLIENT] Sent input_audio_buffer.commit to OpenAI (no audio)")
                    
                    # Don't forward the original message since we've already sent it
                    return
                else:
                    logger.error(f"❌ [CLIENT] No OpenAI connection found for client {client_id}")
                    return
            
            # Forward other messages to OpenAI
            if client_id in self.openai_connections:
                openai_ws = self.openai_connections[client_id]
                await openai_ws.send(message)
                logger.info(f"📨 [CLIENT] Forwarded message to OpenAI for client {client_id}")
            else:
                logger.error(f"❌ [CLIENT] No OpenAI connection found for client {client_id}")
                
        except json.JSONDecodeError:
            logger.error(f"❌ [CLIENT] Failed to parse client message as JSON: {message[:100]}...")
        except Exception as e:
            logger.error(f"❌ [CLIENT] Error handling client message: {e}")
            import traceback
            logger.error(f"❌ [CLIENT] Traceback: {traceback.format_exc()}")
            
# Global manager instance
manager = RealtimeConversationManager()

# Create router
router = APIRouter()

@router.websocket("/ws/realtime-conversation")
async def realtime_conversation_websocket(websocket: WebSocket):
    client_id = f"realtime_{id(websocket)}"
    
    try:
        await manager.connect(websocket, client_id)
        
        while True:
            try:
                # Check if the message is binary (audio) or text (JSON)
                message = await websocket.receive()
                
                if message["type"] == "websocket.receive":
                    if "bytes" in message:
                        # Audio is now sent via text, so we can ignore binary messages
                        logger.info(f"🎤 [AUDIO] Received binary message from {client_id}, ignoring.")
                        pass
                    elif "text" in message:
                        # Handle JSON text message
                        await manager.handle_client_message(client_id, message["text"])
                        
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error in websocket loop: {e}")
                break
                
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await manager.disconnect(client_id) 