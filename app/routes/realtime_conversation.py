import asyncio
import json
import base64
import websockets
import os
import struct
from typing import Dict, Any
from fastapi import WebSocket, WebSocketDisconnect, APIRouter
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_pcm16_from_audio(audio_data: bytes) -> bytes:
    """Extract raw PCM16 data from audio file (WAV or raw PCM)"""
    try:
        # Check if it's a valid WAV file
        if len(audio_data) >= 44 and audio_data[:4] == b'RIFF' and audio_data[8:12] == b'WAVE':
            logger.info("🎤 [AUDIO] Detected WAV file, extracting PCM data")
            # Parse WAV header
            # Skip RIFF header (12 bytes)
            # Look for 'data' chunk
            data_start = 12
            while data_start < len(audio_data) - 8:
                chunk_id = audio_data[data_start:data_start + 4]
                chunk_size = struct.unpack('<I', audio_data[data_start + 4:data_start + 8])[0]
                
                if chunk_id == b'data':
                    # Found data chunk, extract PCM data
                    pcm_data = audio_data[data_start + 8:data_start + 8 + chunk_size]
                    logger.info(f"🎤 [AUDIO] Extracted {len(pcm_data)} bytes of PCM16 data from WAV")
                    return pcm_data
                
                data_start += 8 + chunk_size
            
            logger.warning("🎤 [AUDIO] No data chunk found in WAV file")
            return audio_data
        else:
            # Assume it's already raw PCM data
            logger.info(f"🎤 [AUDIO] Detected raw PCM data, size: {len(audio_data)} bytes")
            return audio_data
        
    except Exception as e:
        logger.error(f"🎤 [AUDIO] Error processing audio data: {e}")
        return audio_data

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
            
            # Start listening for OpenAI messages
            asyncio.create_task(self._handle_openai_messages(client_id))
            
            # Send initial session configuration
            await self._send_session_update(client_id)
            
        except Exception as e:
            logger.error(f"Failed to connect to OpenAI Realtime API: {e}")
            
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
                        logger.info(f"🤖 [OPENAI] Audio delta received, size: {len(data.get('response', {}).get('output', [{}])[0].get('audio', ''))}")
                    elif event_type == 'response.done':
                        logger.info(f"🤖 [OPENAI] Response done: {data}")
                    elif event_type == 'error':
                        logger.error(f"❌ [OPENAI] Error from OpenAI: {data}")
                    
                    # Forward the message to the client
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
            
    async def _send_session_update(self, client_id: str):
        """Send initial session configuration"""
        try:
            session_update = {
                "type": "session.update",
                "session": {
                    "instructions": "You are a helpful English tutor. Help the user improve their English speaking skills through natural conversation. Be encouraging and provide gentle corrections when needed.",
                    "voice": "alloy"
                }
            }
            
            if client_id in self.openai_connections:
                openai_ws = self.openai_connections[client_id]
                await openai_ws.send(json.dumps(session_update))
                logger.info(f"Sent session update for client {client_id}")
                
        except Exception as e:
            logger.error(f"Error sending session update: {e}")
            
    async def handle_client_message(self, client_id: str, message: str):
        """Handle messages from the client"""
        try:
            data = json.loads(message)
            message_type = data.get('type')
            
            logger.info(f"📨 [CLIENT] Received client message type: {message_type} from client {client_id}")
            logger.info(f"📨 [CLIENT] Message content: {message[:200]}...")  # Log first 200 chars
            
            # Handle audio buffer commit specially
            if message_type == 'input_audio_buffer.commit':
                logger.info(f"🎤 [CLIENT] Committing audio buffer for client {client_id}")
                
                # Send accumulated audio data to OpenAI first
                if client_id in self.openai_connections:
                    openai_ws = self.openai_connections[client_id]
                    
                    if client_id in self.audio_buffers and len(self.audio_buffers[client_id]) > 0:
                        buffer_size = len(self.audio_buffers[client_id])
                        logger.info(f"🎤 [CLIENT] Sending accumulated audio data: {buffer_size} bytes")
                        
                        # Encode accumulated audio data as base64
                        audio_base64 = base64.b64encode(self.audio_buffers[client_id]).decode('utf-8')
                        logger.info(f"🎤 [CLIENT] Encoded audio to base64, length: {len(audio_base64)} characters")
                        
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
            
    async def handle_audio_data(self, client_id: str, audio_data: bytes):
        """Handle audio data from the client"""
        try:
            logger.info(f"🎤 [AUDIO] Received audio data from client {client_id}, size: {len(audio_data)} bytes")
            
            # Extract raw PCM16 data from WAV file
            pcm_data = extract_pcm16_from_audio(audio_data)
            logger.info(f"🎤 [AUDIO] PCM16 data size: {len(pcm_data)} bytes")
            
            # Accumulate audio data in buffer (don't send immediately)
            if client_id not in self.audio_buffers:
                self.audio_buffers[client_id] = b''
            
            self.audio_buffers[client_id] += pcm_data
            logger.info(f"🎤 [AUDIO] Accumulated audio buffer size: {len(self.audio_buffers[client_id])} bytes")
            
            # Don't send to OpenAI yet - wait for input_audio_buffer.commit
            logger.info(f"🎤 [AUDIO] Audio data accumulated, waiting for commit signal")
                
        except Exception as e:
            logger.error(f"❌ [AUDIO] Error handling audio data: {e}")
            import traceback
            logger.error(f"❌ [AUDIO] Traceback: {traceback.format_exc()}")

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
                        # Handle binary audio data
                        await manager.handle_audio_data(client_id, message["bytes"])
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