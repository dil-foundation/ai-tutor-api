"""
OpenAI Realtime API WebSocket Handler
Implements high-speed bidirectional audio streaming for real-time conversation
"""

import asyncio
import json
import base64
import os
import io
from typing import Optional, Dict, Any
from pydub import AudioSegment
import websockets
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.audio_utils import validate_and_convert_audio
from app.config import OPENAI_API_KEY

router = APIRouter()

# System prompt for the AI tutor
SYSTEM_PROMPT = (
    "You are a kind, encouraging, and patient English tutor for learners. "
    "Engage in natural, conversational English practice. "
    "Speak clearly and at a moderate pace. "
    "Provide gentle corrections when needed and praise good efforts. "
    "Keep responses concise and conversational."
)

# OpenAI Realtime API configuration
# Using the same model version as the working example
OPENAI_REALTIME_URI = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17"
OPENAI_HEADERS = {
    "Authorization": f"Bearer {OPENAI_API_KEY}",
    "OpenAI-Beta": "realtime=v1"
}

# Audio format configuration
INPUT_AUDIO_FORMAT = "pcm16"  # 16-bit PCM
OUTPUT_AUDIO_FORMAT = "pcm16"
SAMPLE_RATE = 24000  # OpenAI Realtime API uses 24kHz


async def convert_audio_to_pcm16(audio_bytes: bytes) -> bytes:
    """
    Convert audio bytes to 24kHz mono 16-bit PCM format required by OpenAI Realtime API.
    """
    try:
        print(f"🔄 Loading audio from {len(audio_bytes)} bytes...")
        audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
        
        print(f"📊 Original audio: {audio.frame_rate}Hz, {audio.channels} channels, {audio.sample_width * 8}-bit, {len(audio.raw_data)} bytes")
        
        # Convert to 24kHz (OpenAI Realtime API requirement)
        audio = audio.set_frame_rate(SAMPLE_RATE)
        
        # Convert to single channel (mono)
        audio = audio.set_channels(1)
        
        # Convert to 16-bit PCM
        audio = audio.set_sample_width(2)
        
        # Export as raw PCM16
        buf = io.BytesIO()
        audio.export(buf, format="raw")
        
        pcm16_data = buf.getvalue()
        
        # Calculate duration
        duration_seconds = len(pcm16_data) / (SAMPLE_RATE * 2)  # 2 bytes per sample
        duration_ms = duration_seconds * 1000
        
        print(f"✅ Converted to PCM16: {SAMPLE_RATE}Hz, mono, 16-bit, {len(pcm16_data)} bytes ({duration_ms:.1f}ms)")
        
        # Validate minimum duration
        if duration_ms < 100:
            print(f"⚠️ Warning: Audio duration ({duration_ms:.1f}ms) is less than 100ms minimum")
        
        return pcm16_data
    except Exception as e:
        print(f"❌ Error converting audio to PCM16: {e}")
        import traceback
        traceback.print_exc()
        raise


async def convert_pcm16_to_wav(pcm_data: bytes) -> bytes:
    """
    Convert PCM16 audio data to WAV format for mobile playback.
    """
    try:
        audio_segment = AudioSegment(
            data=pcm_data,
            sample_width=2,  # 16-bit = 2 bytes
            frame_rate=SAMPLE_RATE,
            channels=1
        )
        
        wav_buffer = io.BytesIO()
        audio_segment.export(wav_buffer, format="wav")
        
        return wav_buffer.getvalue()
    except Exception as e:
        print(f"❌ Error converting PCM16 to WAV: {e}")
        raise


class OpenAIRealtimeBridge:
    """
    Bridges between client WebSocket and OpenAI Realtime API.
    Handles bidirectional audio streaming for optimal performance.
    """
    
    def __init__(self, client_ws: WebSocket):
        self.client_ws = client_ws
        self.openai_ws: Optional[websockets.WebSocketClientProtocol] = None
        self.session_id: Optional[str] = None
        self.is_connected = False
        self.session_ready = False  # Track if session is fully configured
        self.response_audio_chunks: list = []
        self.response_text: str = ""
        self.response_done = True  # Start as True so first commit can proceed
        # Track audio buffer to ensure we have enough before committing
        self.audio_buffer_size_bytes: int = 0
        self.audio_chunks_count: int = 0
        # Minimum audio required: 100ms at 24kHz, 16-bit, mono = 2400 samples * 2 bytes = 4800 bytes
        self.MIN_AUDIO_BYTES = 4800  # ~100ms of audio
        # Track if we've received any errors after appending
        self.append_errors: list = []
        
    async def connect_to_openai(self):
        """Establish connection to OpenAI Realtime API"""
        try:
            self.openai_ws = await websockets.connect(
                OPENAI_REALTIME_URI,
                additional_headers=OPENAI_HEADERS
            )
            
            # Configure session
            # IMPORTANT: Disable automatic turn detection to prevent buffer clearing
            # We'll manually commit when ready
            session_config = {
                "type": "session.update",
                "session": {
                    "modalities": ["audio", "text"],
                    "input_audio_format": INPUT_AUDIO_FORMAT,
                    "output_audio_format": OUTPUT_AUDIO_FORMAT,
                    "instructions": SYSTEM_PROMPT,
                    "voice": "alloy",  # Default voice
                    "temperature": 0.8,
                    "turn_detection": None  # Disable automatic VAD - we'll commit manually
                }
            }
            
            print(f"📤 Sending session configuration (VAD disabled for manual commit)...")
            await self.openai_ws.send(json.dumps(session_config))
            
            self.is_connected = True
            self.session_ready = False  # Will be set to True when session.updated is received
            print("✅ Connected to OpenAI Realtime API, waiting for session confirmation...")
            
            # Start listening for OpenAI messages
            asyncio.create_task(self._listen_to_openai())
            
            # Wait a moment for session.updated to arrive
            await asyncio.sleep(0.5)
            
        except Exception as e:
            print(f"❌ Error connecting to OpenAI Realtime API: {e}")
            self.is_connected = False
            raise
    
    async def _listen_to_openai(self):
        """Listen for messages from OpenAI Realtime API and forward to client"""
        try:
            async for message in self.openai_ws:
                data = json.loads(message)
                message_type = data.get("type")
                
                if message_type == "session.created":
                    self.session_id = data.get("session", {}).get("id")
                    print(f"✅ OpenAI session created: {self.session_id}")
                    
                elif message_type == "session.updated":
                    print("✅ OpenAI session updated")
                    self.session_ready = True  # Session is now ready to receive audio
                    
                elif message_type == "input_audio_buffer.speech_started":
                    print("🎤 Speech detected in audio buffer")
                    
                elif message_type == "input_audio_buffer.speech_stopped":
                    print("🔇 Speech stopped in audio buffer")
                    
                elif message_type == "input_audio_buffer.commit":
                    # Confirmation that commit was received
                    print("✅ Input audio buffer commit confirmed by OpenAI")
                    
                elif message_type == "response.audio.delta":
                    # Stream audio chunks to client immediately for low latency
                    audio_delta = base64.b64decode(data.get("delta", ""))
                    if audio_delta:
                        # Convert PCM16 to WAV and send to client
                        wav_audio = await convert_pcm16_to_wav(audio_delta)
                        await self.client_ws.send_bytes(wav_audio)
                        
                elif message_type == "response.audio_transcript.delta":
                    # Stream transcription text
                    transcript_delta = data.get("delta", "")
                    if transcript_delta:
                        self.response_text += transcript_delta
                        # Send text update to client
                        await self.client_ws.send_json({
                            "type": "transcript_delta",
                            "text": self.response_text
                        })
                        
                elif message_type == "response.audio_transcript.done":
                    # Final transcript
                    final_text = data.get("text", "")
                    self.response_text = final_text
                    await self.client_ws.send_json({
                        "type": "transcript_done",
                        "text": final_text
                    })
                    
                elif message_type == "response.done":
                    # Response complete
                    self.response_done = True
                    await self.client_ws.send_json({
                        "type": "response_done"
                    })
                    
                elif message_type == "error":
                    error_details = data.get("error", {})
                    error_msg = error_details.get("message", "Unknown error")
                    error_code = error_details.get("code", "unknown")
                    print(f"❌ OpenAI Error: {error_msg} (Code: {error_code})")
                    
                    # Track append errors
                    if "input_audio_buffer" in error_code.lower() or "append" in error_msg.lower():
                        self.append_errors.append({
                            "code": error_code,
                            "message": error_msg,
                            "timestamp": asyncio.get_event_loop().time()
                        })
                        print(f"⚠️ Append error tracked: {error_code}")
                    
                    # Handle specific errors
                    if error_code == "input_audio_buffer_commit_empty":
                        # Buffer was cleared or not properly set - reset our tracking
                        print("⚠️ OpenAI buffer was empty - resetting our buffer tracking")
                        print(f"   Recent append errors: {len(self.append_errors)}")
                        if self.append_errors:
                            print(f"   Last append error: {self.append_errors[-1]}")
                        self.audio_buffer_size_bytes = 0
                        self.audio_chunks_count = 0
                        self.append_errors.clear()
                    elif error_code == "conversation_already_has_active_response":
                        # Response in progress - mark as such
                        print("⚠️ Response already in progress - marking response_done as False")
                        self.response_done = False
                    
                    await self.client_ws.send_json({
                        "type": "error",
                        "message": error_msg,
                        "code": error_code
                    })
                    
        except websockets.exceptions.ConnectionClosed:
            print("⚠️ OpenAI WebSocket connection closed")
            self.is_connected = False
            self.session_ready = False
        except Exception as e:
            print(f"❌ Error listening to OpenAI: {e}")
            import traceback
            traceback.print_exc()
            self.is_connected = False
            self.session_ready = False
            try:
                await self.client_ws.send_json({
                    "type": "error",
                    "message": f"OpenAI connection error: {str(e)}"
                })
            except:
                pass  # Client might have disconnected
    
    async def send_audio_to_openai(self, audio_bytes: bytes):
        """Send audio data to OpenAI Realtime API"""
        if not self.is_connected or not self.openai_ws:
            raise Exception("Not connected to OpenAI Realtime API")
        
        # Wait for session to be ready (max 5 seconds)
        if not self.session_ready:
            print("⏳ Waiting for session to be ready...")
            for _ in range(50):  # Wait up to 5 seconds (50 * 0.1s)
                await asyncio.sleep(0.1)
                if self.session_ready:
                    break
            if not self.session_ready:
                print("⚠️ Session not ready after waiting, proceeding anyway...")
        
        try:
            print(f"🔄 Converting {len(audio_bytes)} bytes of audio to PCM16...")
            
            # Convert audio to PCM16 format
            pcm16_audio = await convert_audio_to_pcm16(audio_bytes)
            
            if not pcm16_audio or len(pcm16_audio) == 0:
                print("⚠️ Audio conversion resulted in empty PCM16 data")
                return False
            
            # Encode entire audio to base64
            # OpenAI Realtime API can handle large audio in a single append
            # Splitting into chunks can cause issues if not done correctly
            audio_base64 = base64.b64encode(pcm16_audio).decode('utf-8')
            
            # Calculate duration for logging
            # 24kHz, 16-bit, mono: 1 second = 24,000 samples * 2 bytes = 48,000 bytes
            duration_ms = (len(pcm16_audio) / 48000) * 1000
            
            print(f"📤 Sending {len(pcm16_audio)} bytes PCM16 ({duration_ms:.1f}ms) as single append")
            print(f"   Base64 length: {len(audio_base64)} chars")
            
            # Clear any previous append errors
            self.append_errors.clear()
            
            # Send audio to OpenAI in a single append operation
            # This matches the working example in conversation_ws_2.py
            append_message = {
                "type": "input_audio_buffer.append",
                "audio": audio_base64
            }
            
            print(f"📤 Sending append message to OpenAI...")
            await self.openai_ws.send(json.dumps(append_message))
            
            print(f"✅ Audio append message sent to OpenAI")
            
            # Wait a bit and check for errors
            await asyncio.sleep(0.08)  # Short delay keeps end-to-end latency under 3s
            
            # Check if we received any errors during the wait
            if self.append_errors:
                last_error = self.append_errors[-1]
                print(f"⚠️ Received error after append: {last_error['code']} - {last_error['message']}")
                # Don't track this audio in buffer if there was an error
                return False
            
            print(f"✅ No errors received, audio should be in buffer")
            
            # Track buffer size ONLY after successful send
            self.audio_buffer_size_bytes += len(pcm16_audio)
            self.audio_chunks_count += 1
            
            print(f"📊 Audio buffer: {self.audio_buffer_size_bytes} bytes ({self.audio_chunks_count} chunks) - Total PCM16: {len(pcm16_audio)} bytes")
            print(f"✅ Successfully appended {len(pcm16_audio)} bytes to OpenAI buffer")
            return True
            
        except Exception as e:
            print(f"❌ Error sending audio to OpenAI: {e}")
            import traceback
            traceback.print_exc()
            # Don't increment buffer size if conversion/send failed
            return False
    
    async def commit_audio_and_get_response(self):
        """Commit audio buffer and request response from OpenAI"""
        if not self.is_connected or not self.openai_ws:
            raise Exception("Not connected to OpenAI Realtime API")
        
        try:
            # Check if there's already a response in progress
            if not self.response_done:
                error_msg = "A response is already in progress. Please wait for it to complete."
                print(f"⚠️ {error_msg}")
                await self.client_ws.send_json({
                    "type": "error",
                    "message": error_msg,
                    "code": "response_in_progress"
                })
                return
            
            # Check if we have enough audio before committing
            if self.audio_buffer_size_bytes < self.MIN_AUDIO_BYTES:
                error_msg = f"Not enough audio to commit. Have {self.audio_buffer_size_bytes} bytes, need at least {self.MIN_AUDIO_BYTES} bytes (~100ms)"
                print(f"⚠️ {error_msg}")
                await self.client_ws.send_json({
                    "type": "error",
                    "message": error_msg,
                    "code": "insufficient_audio"
                })
                # Reset buffer tracking
                self.audio_buffer_size_bytes = 0
                self.audio_chunks_count = 0
                return
            
            print(f"✅ Committing {self.audio_buffer_size_bytes} bytes ({self.audio_chunks_count} chunks) of audio")
            
            # Reset response state BEFORE committing (mark as in progress)
            self.response_audio_chunks = []
            self.response_text = ""
            self.response_done = False  # Mark that we're waiting for a response
            
            # Store buffer info for logging
            buffer_size = self.audio_buffer_size_bytes
            chunk_count = self.audio_chunks_count
            
            # DON'T reset buffer tracking yet - keep it until after successful commit
            # This way if commit fails, we still know how much audio we tried to send
            
            # Commit the audio buffer
            # This tells OpenAI we're done sending audio and ready for response
            commit_message = {
                "type": "input_audio_buffer.commit"
            }
            
            print(f"📤 Committing buffer with {buffer_size} bytes ({chunk_count} chunks)...")
            await self.openai_ws.send(json.dumps(commit_message))
            
            # Small delay to allow OpenAI to process the commit
            await asyncio.sleep(0.1)
            
            # Now reset buffer tracking after commit is sent
            self.audio_buffer_size_bytes = 0
            self.audio_chunks_count = 0
            
            print("📤 Audio buffer committed, requesting response...")
            
            # Request response immediately after commit
            response_message = {
                "type": "response.create",
                "response": {
                    "modalities": ["audio", "text"],
                    "instructions": "Respond naturally and conversationally."
                }
            }
            
            await self.openai_ws.send(json.dumps(response_message))
            
            print("✅ Response creation requested")
            
        except Exception as e:
            print(f"❌ Error committing audio: {e}")
            import traceback
            traceback.print_exc()
            # Reset buffer tracking on error
            self.audio_buffer_size_bytes = 0
            self.audio_chunks_count = 0
            # Reset response state on error
            self.response_done = True
            raise
    
    async def close(self):
        """Close connections"""
        try:
            if self.openai_ws:
                await self.openai_ws.close()
            self.is_connected = False
        except Exception as e:
            print(f"⚠️ Error closing OpenAI connection: {e}")


@router.websocket("/ws/openai-realtime")
async def openai_realtime_conversation(websocket: WebSocket):
    """
    WebSocket endpoint for OpenAI Realtime API conversation.
    Handles bidirectional audio streaming for ultra-low latency.
    """
    await websocket.accept()
    print("✅ Client connected to OpenAI Realtime endpoint")
    
    bridge: Optional[OpenAIRealtimeBridge] = None
    
    try:
        # Initialize bridge
        bridge = OpenAIRealtimeBridge(websocket)
        await bridge.connect_to_openai()
        
        # Send connection confirmation
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to OpenAI Realtime API"
        })
        
        # Main message loop
        while True:
            try:
                # Receive message from client
                message_data = await websocket.receive()
                
                # Handle binary audio data
                if "bytes" in message_data:
                    audio_bytes = message_data["bytes"]
                    print(f"📥 Received binary audio: {len(audio_bytes)} bytes")
                    
                    # Check if connection is still valid
                    if not bridge.is_connected or not bridge.openai_ws:
                        print("⚠️ OpenAI connection lost, cannot send audio")
                        await websocket.send_json({
                            "type": "error",
                            "message": "OpenAI connection lost. Please reconnect.",
                            "code": "connection_lost"
                        })
                        continue
                    
                    # Send audio to OpenAI immediately for streaming
                    success = await bridge.send_audio_to_openai(audio_bytes)
                    if not success:
                        print("⚠️ Failed to send audio to OpenAI, but continuing...")
                        # Don't send error to client - they can retry by sending more audio
                    
                # Handle text messages (JSON)
                elif "text" in message_data:
                    try:
                        message = json.loads(message_data["text"])
                        message_type = message.get("type")
                        
                        if message_type == "audio_commit":
                            # Client is done sending audio, commit and get response
                            print("📤 Committing audio and requesting response")
                            await bridge.commit_audio_and_get_response()
                            
                        elif message_type == "ping":
                            # Keep-alive ping
                            await websocket.send_json({"type": "pong"})
                            
                        elif message_type == "close":
                            # Client requested close
                            break
                            
                    except json.JSONDecodeError:
                        print("⚠️ Invalid JSON received")
                        await websocket.send_json({
                            "type": "error",
                            "message": "Invalid JSON format"
                        })
                        
            except WebSocketDisconnect:
                print("⚠️ Client disconnected")
                break
            except Exception as e:
                print(f"❌ Error processing message: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": f"Processing error: {str(e)}"
                })
                
    except Exception as e:
        print(f"❌ Unexpected error in OpenAI Realtime endpoint: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": f"Server error: {str(e)}"
            })
        except:
            pass
    finally:
        # Cleanup
        if bridge:
            await bridge.close()
        print("🔌 OpenAI Realtime connection closed")

