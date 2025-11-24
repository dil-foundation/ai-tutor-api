"""
Gemini Live API WebSocket Handler
Implements high-speed bidirectional audio streaming for real-time conversation
Using Gemini 2.5 Flash Live API with native audio
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
from app.config import GEMINI_API_KEY

router = APIRouter()

# System prompt for the AI tutor
SYSTEM_PROMPT = (
    "You are a kind, encouraging, and patient English tutor for learners. "
    "Engage in natural, conversational English practice. "
    "Speak clearly and at a moderate pace. "
    "Provide gentle corrections when needed and praise good efforts. "
    "Keep responses concise and conversational."
)

# Gemini Live API configuration
# Using Gemini 2.5 Flash Live API with native audio
# IMPORTANT: The correct model name format for Live API
# Based on Google's documentation, Live API models follow the pattern:
# - gemini-2.5-flash-preview-09-2025 (preview version)
# - gemini-2.5-flash (stable version)
# The "live" and "native-audio" are not part of the model name
# Live API automatically enables native audio when using the correct model
# IMPORTANT: Use stable version first - it's most compatible with Live API
GEMINI_MODEL = "gemini-2.5-flash"  # Stable version (RECOMMENDED - most compatible)
# Alternative models to try if the above doesn't work:
# GEMINI_MODEL = "gemini-2.5-flash-preview-09-2025"  # Preview version
# GEMINI_MODEL = "gemini-2.0-flash-exp"  # Experimental version
# GEMINI_MODEL = "gemini-1.5-flash"  # Older stable version

# The correct WebSocket endpoint format for Gemini Live API
# IMPORTANT: Based on Google AI documentation (ai.google.dev)
# The Live API uses a specific WebSocket endpoint format
# According to the documentation, the endpoint uses dots (.) not slashes (/)
GEMINI_LIVE_URI_BASE = "wss://generativelanguage.googleapis.com"

# Try multiple endpoint formats based on documentation
# IMPORTANT: v1alpha might not support all models - try v1beta if v1alpha fails
# Format 1: v1beta BidiGenerateContent (RECOMMENDED - supports more models)
GEMINI_LIVE_URI_V1BETA_DOT = f"{GEMINI_LIVE_URI_BASE}/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent"

# Format 2: v1beta BidiGenerateContent with slash
GEMINI_LIVE_URI_V1BETA_SLASH = f"{GEMINI_LIVE_URI_BASE}/ws/google.ai.generativelanguage.v1beta.GenerativeService/BidiGenerateContent"

# Format 3: v1alpha BidiGenerateContent with dots (may not support all models)
GEMINI_LIVE_URI_V1ALPHA_DOT = f"{GEMINI_LIVE_URI_BASE}/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent"

# Format 4: v1alpha BidiGenerateContent with slash (alternative)
GEMINI_LIVE_URI_V1ALPHA_SLASH = f"{GEMINI_LIVE_URI_BASE}/ws/google.ai.generativelanguage.v1alpha.GenerativeService/BidiGenerateContent"

# Format 5: v1beta streamGenerateContent (alternative endpoint)
GEMINI_LIVE_URI_V1BETA_STREAM = f"{GEMINI_LIVE_URI_BASE}/ws/v1beta/models/{GEMINI_MODEL}:streamGenerateContent"

# Use v1alpha with dots first (most likely correct format)
GEMINI_LIVE_URI = GEMINI_LIVE_URI_V1ALPHA_DOT

# Note: If you get 404 errors, it likely means:
# 1. The endpoint format has changed or is incorrect
# 2. Gemini Live API requires Vertex AI setup (not API key)
# 3. The model requires special access approval
# 4. The API might not be available in your region

# Audio format configuration for Gemini Live API
INPUT_SAMPLE_RATE = 16000  # Gemini requires 16kHz input
OUTPUT_SAMPLE_RATE = 24000  # Gemini outputs 24kHz
INPUT_AUDIO_FORMAT = "pcm16"  # 16-bit PCM, little-endian
OUTPUT_AUDIO_FORMAT = "pcm16"  # 16-bit PCM, little-endian


async def convert_audio_to_pcm16_16khz(audio_bytes: bytes) -> bytes:
    """
    Convert audio bytes to 16kHz mono 16-bit PCM format required by Gemini Live API.
    """
    try:
        print(f"🔄 Loading audio from {len(audio_bytes)} bytes...")
        audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
        
        print(f"📊 Original audio: {audio.frame_rate}Hz, {audio.channels} channels, {audio.sample_width * 8}-bit, {len(audio.raw_data)} bytes")
        
        # Convert to 16kHz (Gemini Live API requirement)
        audio = audio.set_frame_rate(INPUT_SAMPLE_RATE)
        
        # Convert to single channel (mono)
        audio = audio.set_channels(1)
        
        # Convert to 16-bit PCM
        audio = audio.set_sample_width(2)
        
        # Export as raw PCM16 (little-endian)
        buf = io.BytesIO()
        audio.export(buf, format="raw")
        
        pcm16_data = buf.getvalue()
        
        # Calculate duration
        duration_seconds = len(pcm16_data) / (INPUT_SAMPLE_RATE * 2)  # 2 bytes per sample
        duration_ms = duration_seconds * 1000
        
        print(f"✅ Converted to PCM16: {INPUT_SAMPLE_RATE}Hz, mono, 16-bit, {len(pcm16_data)} bytes ({duration_ms:.1f}ms)")
        
        # Validate minimum duration
        if duration_ms < 100:
            print(f"⚠️ Warning: Audio duration ({duration_ms:.1f}ms) is less than 100ms minimum")
        
        return pcm16_data
    except Exception as e:
        print(f"❌ Error converting audio to PCM16: {e}")
        import traceback
        traceback.print_exc()
        raise


async def convert_pcm16_to_wav(pcm_data: bytes, sample_rate: int = OUTPUT_SAMPLE_RATE) -> bytes:
    """
    Convert PCM16 audio data to WAV format for mobile playback.
    """
    try:
        audio_segment = AudioSegment(
            data=pcm_data,
            sample_width=2,  # 16-bit = 2 bytes
            frame_rate=sample_rate,
            channels=1
        )
        
        wav_buffer = io.BytesIO()
        audio_segment.export(wav_buffer, format="wav")
        
        return wav_buffer.getvalue()
    except Exception as e:
        print(f"❌ Error converting PCM16 to WAV: {e}")
        raise


class GeminiLiveBridge:
    """
    Bridges between client WebSocket and Gemini Live API.
    Handles bidirectional audio streaming for optimal performance.
    """
    
    def __init__(self, client_ws: WebSocket):
        self.client_ws = client_ws
        self.gemini_ws: Optional[websockets.WebSocketClientProtocol] = None
        self.session_id: Optional[str] = None
        self.is_connected = False
        self.session_ready = False
        self.response_audio_chunks: list = []
        self.response_text: str = ""
        self.response_done = True
        # Track audio buffer to ensure we have enough before committing
        self.audio_buffer_size_bytes: int = 0
        self.audio_chunks_count: int = 0
        # Minimum audio required: 100ms at 16kHz, 16-bit, mono = 1600 samples * 2 bytes = 3200 bytes
        self.MIN_AUDIO_BYTES = 3200  # ~100ms of audio at 16kHz
        # Track listening task and control flag to prevent excessive logging
        self._listening_task: Optional[asyncio.Task] = None
        self._should_stop_listening = False
        self._disconnection_logged = False
        
    async def connect_to_gemini(self):
        """Establish connection to Gemini Live API"""
        # Try multiple endpoint formats
        # IMPORTANT: Try v1beta first as it supports more models than v1alpha
        # Order matters: try most likely correct format first
        endpoints_to_try = [
            (GEMINI_LIVE_URI_V1BETA_DOT, "v1beta with dots (recommended)"),
            (GEMINI_LIVE_URI_V1BETA_SLASH, "v1beta with slash"),
            (GEMINI_LIVE_URI_V1ALPHA_DOT, "v1alpha with dots"),
            (GEMINI_LIVE_URI_V1ALPHA_SLASH, "v1alpha with slash"),
            (GEMINI_LIVE_URI_V1BETA_STREAM, "v1beta streamGenerateContent"),
        ]
        
        last_error = None
        connection_successful = False
        
        for endpoint_uri, endpoint_name in endpoints_to_try:
            try:
                # Build WebSocket URL with API key
                ws_url = f"{endpoint_uri}?key={GEMINI_API_KEY}"
                
                # Additional headers for Gemini API
                additional_headers = {
                    "Content-Type": "application/json",
                }
                
                print(f"🔌 Attempting connection ({endpoint_name})...")
                print(f"📡 Endpoint: {endpoint_uri.split('/')[-1]}")
                print(f"🔑 API key: {GEMINI_API_KEY[:10]}...{GEMINI_API_KEY[-4:] if len(GEMINI_API_KEY) > 14 else '***'}")
                
                try:
                    self.gemini_ws = await websockets.connect(
                        ws_url,
                        additional_headers=additional_headers,
                        ping_interval=20,
                        ping_timeout=10,
                        close_timeout=10
                    )
                    print(f"✅ WebSocket connection established using {endpoint_name}")
                    connection_successful = True
                    break  # Success, exit the loop
                    
                except websockets.exceptions.InvalidStatus as status_error:
                    # Extract status code from the exception
                    # InvalidStatus has a response attribute with status_code
                    status_code = getattr(status_error, 'status_code', None)
                    if status_code is None:
                        # Try to get from response object
                        response = getattr(status_error, 'response', None)
                        if response:
                            status_code = getattr(response, 'status_code', None) or getattr(response, 'code', None)
                    if status_code is None:
                        # Last resort: parse from error message
                        error_str = str(status_error)
                        if '404' in error_str:
                            status_code = 404
                        elif '401' in error_str:
                            status_code = 401
                        elif '403' in error_str:
                            status_code = 403
                        else:
                            status_code = 'Unknown'
                    
                    print(f"❌ {endpoint_name} failed with HTTP {status_code}")
                    print(f"   Error: {status_error}")
                    last_error = status_error
                    
                    # If this is not a 404, it might be an auth issue, don't try other endpoints
                    if status_code != 404 and status_code != 'Unknown':
                        print(f"   Non-404 error ({status_code}), stopping endpoint attempts")
                        raise
                    
                    # If 404 or Unknown, try next endpoint
                    print(f"   {status_code} error, trying next endpoint format...")
                    continue
                    
            except websockets.exceptions.InvalidStatus:
                # Re-raise non-404 errors
                raise
            except Exception as e:
                last_error = e
                print(f"❌ Error with {endpoint_name}: {e}")
                continue
        
        # If connection failed, provide detailed error information
        if not connection_successful:
            # Extract status code from last error
            status_code = 'Unknown'
            if last_error:
                status_code = getattr(last_error, 'status_code', None)
                if status_code is None:
                    response = getattr(last_error, 'response', None)
                    if response:
                        status_code = getattr(response, 'status_code', None) or getattr(response, 'code', None)
                if status_code is None:
                    error_str = str(last_error)
                    if '404' in error_str:
                        status_code = 404
                    elif '401' in error_str:
                        status_code = 401
                    elif '403' in error_str:
                        status_code = 403
                    else:
                        status_code = 'Unknown'
            
            print(f"❌ All endpoint formats failed. Last error: HTTP {status_code}")
            print(f"   Model: {GEMINI_MODEL}")
            print(f"   Tried endpoints:")
            for endpoint_uri, endpoint_name in endpoints_to_try:
                endpoint_display = endpoint_uri.split('/')[-1] if '/' in endpoint_uri else endpoint_uri.split('.')[-1]
                print(f"     - {endpoint_name}: {endpoint_display}")
            print(f"   Full endpoint URLs:")
            for endpoint_uri, endpoint_name in endpoints_to_try:
                print(f"     - {endpoint_name}: {endpoint_uri}")
            print(f"   Possible issues:")
            print(f"   1. API key is invalid or expired")
            print(f"   2. Model '{GEMINI_MODEL}' is not available or requires special access")
            print(f"   3. Live API access not enabled for your Google Cloud project")
            print(f"   4. All endpoint formats are incorrect")
            print(f"   5. Region restrictions (model only available in us-central1)")
            print(f"   6. Gemini Live API requires Vertex AI setup (not API key)")
            print(f"   💡 IMPORTANT: Gemini Live API typically requires:")
            print(f"      - Vertex AI setup with service account credentials")
            print(f"      - Or use Google Generative AI SDK (google-generativeai package)")
            print(f"      - API key authentication may not be supported for Live API")
            print(f"   💡 Check: https://ai.google.dev/api/live for latest documentation")
            raise Exception(f"Gemini Live API connection failed: All endpoint formats returned errors. Last status: HTTP {status_code}. Gemini Live API may require Vertex AI authentication instead of API key.")
        
        # Initialize session with configuration
        # Gemini Live API expects a specific message format
        # IMPORTANT: Use camelCase for field names (not snake_case)
        # The setup message format for Gemini Live API
        # Note: Model name should NOT include "live" or "native-audio" - those are features, not part of model name
        # IMPORTANT: toolConfig is NOT a valid field in setup message - remove it
        session_config = {
            "setup": {
                "model": f"models/{GEMINI_MODEL}",
                "generationConfig": {
                    "temperature": 0.8,
                    "maxOutputTokens": 4096,
                    "responseModalities": ["AUDIO", "TEXT"]  # Request both audio and text
                },
                "systemInstruction": {
                    "parts": [{"text": SYSTEM_PROMPT}]
                },
                "tools": []  # tools array is valid, but toolConfig is not
            }
        }
        
        # Log the exact model being used
        print(f"📤 Using model: models/{GEMINI_MODEL}")
        print(f"   Note: If this fails, try: gemini-2.5-flash or gemini-2.0-flash-exp")
        
        print(f"📤 Sending session configuration to Gemini Live API...")
        print(f"   Model: models/{GEMINI_MODEL}")
        print(f"   Config: {json.dumps(session_config, indent=2)}")
        await self.gemini_ws.send(json.dumps(session_config))
        
        self.is_connected = True
        self.session_ready = False
        
        print("✅ Connected to Gemini Live API, waiting for session confirmation...")
        
        # Start listening for Gemini messages
        self._should_stop_listening = False
        self._disconnection_logged = False
        self._listening_task = asyncio.create_task(self._listen_to_gemini())
        
        # Wait a moment for setup confirmation
        await asyncio.sleep(0.5)
    
    async def _listen_to_gemini(self):
        """Listen for messages from Gemini Live API and forward to client"""
        try:
            async for message in self.gemini_ws:
                # Check if we should stop listening
                if self._should_stop_listening:
                    break
                try:
                    # Handle both text and binary messages
                    if isinstance(message, bytes):
                        # Binary audio data - might be raw audio
                        print(f"📥 Received binary message: {len(message)} bytes")
                        # Try to parse as JSON first (some APIs send binary JSON)
                        try:
                            data = json.loads(message.decode('utf-8'))
                        except:
                            # It's actual binary audio data
                            print("   Binary audio data received")
                            continue
                    else:
                        data = json.loads(message)
                except json.JSONDecodeError as e:
                    print(f"⚠️ Failed to parse message as JSON: {e}")
                    print(f"   Message type: {type(message)}, length: {len(message) if hasattr(message, '__len__') else 'N/A'}")
                    continue
                
                print(f"📨 Received message from Gemini: {list(data.keys())}")
                
                # Handle different message types from Gemini Live API
                if "setupComplete" in data:
                    print("✅ Gemini session setup complete")
                    print(f"   Setup response: {json.dumps(data, indent=2)}")
                    self.session_ready = True
                    await self.client_ws.send_json({
                        "type": "connected"
                    })
                elif "setupError" in data:
                    error_info = data.get("setupError", {})
                    error_msg = error_info.get("message", "Unknown setup error")
                    print(f"❌ Gemini setup error: {error_msg}")
                    print(f"   Error details: {json.dumps(data, indent=2)}")
                    await self.client_ws.send_json({
                        "type": "error",
                        "message": f"Setup error: {error_msg}",
                        "code": "setup_error"
                    })
                    self.is_connected = False
                    break
                    
                elif "serverContent" in data:
                    # Handle server content (responses)
                    server_content = data.get("serverContent", {})
                    print(f"📥 Server content: {list(server_content.keys())}")
                    
                    if "modelTurn" in server_content:
                        model_turn = server_content["modelTurn"]
                        print(f"   Model turn: {list(model_turn.keys())}")
                        
                        # Handle audio chunks
                        # Audio can be in different formats depending on API version
                        if "audio" in model_turn:
                            audio_data = model_turn["audio"]
                            print(f"   Audio data keys: {list(audio_data.keys()) if isinstance(audio_data, dict) else 'not a dict'}")
                            
                            if "bytes" in audio_data:
                                # Decode base64 audio
                                audio_bytes = base64.b64decode(audio_data["bytes"])
                                print(f"   Decoded audio: {len(audio_bytes)} bytes")
                                # Convert 24kHz PCM16 to WAV and send to client
                                wav_audio = await convert_pcm16_to_wav(audio_bytes, OUTPUT_SAMPLE_RATE)
                                await self.client_ws.send_bytes(wav_audio)
                            elif "data" in audio_data:
                                # Alternative format
                                audio_bytes = base64.b64decode(audio_data["data"])
                                wav_audio = await convert_pcm16_to_wav(audio_bytes, OUTPUT_SAMPLE_RATE)
                                await self.client_ws.send_bytes(wav_audio)
                                
                        # Handle text/transcript
                        if "parts" in model_turn:
                            for part in model_turn["parts"]:
                                if "text" in part:
                                    text_delta = part["text"]
                                    self.response_text += text_delta
                                    await self.client_ws.send_json({
                                        "type": "transcript_delta",
                                        "text": self.response_text
                                    })
                                    
                    elif "turnComplete" in server_content:
                        # Turn complete
                        print("✅ Turn complete received")
                        if self.response_text:
                            await self.client_ws.send_json({
                                "type": "transcript_done",
                                "text": self.response_text
                            })
                        self.response_done = True
                        self.response_text = ""
                        await self.client_ws.send_json({
                            "type": "response_done"
                        })
                        
                elif "error" in data:
                    error_info = data.get("error", {})
                    error_msg = error_info.get("message", "Unknown error")
                    error_code = error_info.get("code", "unknown")
                    print(f"❌ Gemini Error: {error_msg} (Code: {error_code})")
                    
                    await self.client_ws.send_json({
                        "type": "error",
                        "message": error_msg,
                        "code": error_code
                    })
                    
        except websockets.exceptions.ConnectionClosed as e:
            # Only log disconnection once to prevent excessive logging
            if not self._disconnection_logged:
                self._disconnection_logged = True
                reason = e.reason or "Unknown reason"
                code = e.code or "Unknown"
                print(f"🔌 Gemini WebSocket connection closed (Code: {code}, Reason: {reason})")
            self.is_connected = False
            self.session_ready = False
            self._should_stop_listening = True
            try:
                await self.client_ws.send_json({
                    "type": "error",
                    "message": f"Connection closed: {e.reason or 'Unknown reason'}",
                    "code": "connection_closed"
                })
            except:
                pass  # Client might have disconnected
        except Exception as e:
            # Only log errors if we're still supposed to be listening
            if not self._should_stop_listening:
                print(f"❌ Error listening to Gemini: {e}")
            self.is_connected = False
            self.session_ready = False
            self._should_stop_listening = True
            try:
                await self.client_ws.send_json({
                    "type": "error",
                    "message": f"Gemini connection error: {str(e)}"
                })
            except:
                pass  # Client might have disconnected
    
    async def send_audio_to_gemini(self, audio_bytes: bytes):
        """Send audio data to Gemini Live API"""
        if not self.is_connected or not self.gemini_ws:
            raise Exception("Not connected to Gemini Live API")
        
        # Wait for session to be ready (max 5 seconds)
        if not self.session_ready:
            print("⏳ Waiting for session to be ready...")
            for _ in range(50):  # Wait up to 5 seconds
                await asyncio.sleep(0.1)
                if self.session_ready:
                    break
            if not self.session_ready:
                print("⚠️ Session not ready after waiting, proceeding anyway...")
        
        try:
            print(f"🔄 Converting {len(audio_bytes)} bytes of audio to PCM16 16kHz...")
            pcm16_audio = await convert_audio_to_pcm16_16khz(audio_bytes)
            
            if not pcm16_audio or len(pcm16_audio) == 0:
                print("⚠️ Audio conversion resulted in empty PCM16 data")
                return False
            
            # Encode audio as base64
            audio_base64 = base64.b64encode(pcm16_audio).decode('utf-8')
            
            # Send audio to Gemini Live API
            # Gemini expects audio in clientContent with audio bytes
            audio_message = {
                "clientContent": {
                    "turn": {
                        "parts": [
                            {
                                "inlineData": {
                                    "mimeType": "audio/pcm",
                                    "data": audio_base64
                                }
                            }
                        ]
                    }
                }
            }
            
            await self.gemini_ws.send(json.dumps(audio_message))
            
            self.audio_buffer_size_bytes += len(pcm16_audio)
            self.audio_chunks_count += 1
            
            print(f"📊 Audio buffer: {self.audio_buffer_size_bytes} bytes ({self.audio_chunks_count} chunks)")
            print(f"✅ Successfully sent {len(pcm16_audio)} bytes to Gemini buffer")
            return True
            
        except Exception as e:
            print(f"❌ Error sending audio to Gemini: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def commit_audio_and_get_response(self):
        """Commit audio buffer and request response from Gemini"""
        if not self.is_connected or not self.gemini_ws:
            raise Exception("Not connected to Gemini Live API")
        
        # Check if we have enough audio
        if self.audio_buffer_size_bytes < self.MIN_AUDIO_BYTES:
            error_msg = f"Insufficient audio: {self.audio_buffer_size_bytes} bytes < {self.MIN_AUDIO_BYTES} bytes minimum"
            print(f"❌ {error_msg}")
            await self.client_ws.send_json({
                "type": "error",
                "message": error_msg,
                "code": "insufficient_audio"
            })
            return False
        
        # Check if response is already in progress
        if not self.response_done:
            error_msg = "Conversation already has an active response in progress"
            print(f"❌ {error_msg}")
            await self.client_ws.send_json({
                "type": "error",
                "message": error_msg,
                "code": "response_in_progress"
            })
            return False
        
        try:
            print(f"✅ Committing {self.audio_buffer_size_bytes} bytes ({self.audio_chunks_count} chunks) of audio")
            
            # Reset buffer tracking
            self.audio_buffer_size_bytes = 0
            self.audio_chunks_count = 0
            self.response_done = False
            
            # Gemini processes audio automatically when sent
            # No explicit commit needed - the turn is complete when we send the audio
            print("📤 Audio sent, waiting for Gemini response...")
            
            return True
            
        except Exception as e:
            print(f"❌ Error committing audio: {e}")
            import traceback
            traceback.print_exc()
            # Reset on error
            self.audio_buffer_size_bytes = 0
            self.audio_chunks_count = 0
            return False
    
    async def close(self):
        """Close connections"""
        # Stop listening task first
        self._should_stop_listening = True
        
        # Cancel listening task if it's still running
        if self._listening_task and not self._listening_task.done():
            try:
                self._listening_task.cancel()
                try:
                    await self._listening_task
                except asyncio.CancelledError:
                    pass
            except Exception:
                pass
        
        # Close Gemini WebSocket connection
        try:
            if self.gemini_ws:
                await self.gemini_ws.close()
        except Exception:
            pass
        
        self.is_connected = False
        self.session_ready = False


@router.websocket("/ws/gemini-realtime")
async def gemini_realtime_conversation(websocket: WebSocket):
    """
    WebSocket endpoint for Gemini Live API real-time conversation.
    Handles bidirectional audio streaming between client and Gemini.
    """
    await websocket.accept()
    print("✅ Client connected to Gemini Realtime endpoint")
    
    bridge = GeminiLiveBridge(websocket)
    
    try:
        # Connect to Gemini Live API
        await bridge.connect_to_gemini()
        
        # Main message loop
        while True:
            try:
                # Receive message from client
                message = await websocket.receive()
                
                if "bytes" in message:
                    # Binary audio data
                    audio_bytes = message["bytes"]
                    print(f"📥 Received binary audio: {len(audio_bytes)} bytes")
                    await bridge.send_audio_to_gemini(audio_bytes)
                    
                elif "text" in message:
                    # JSON message
                    try:
                        data = json.loads(message["text"])
                        msg_type = data.get("type")
                        
                        if msg_type == "audio_commit":
                            # Client wants to commit audio and get response
                            print("📤 Committing audio and requesting response")
                            await bridge.commit_audio_and_get_response()
                        else:
                            print(f"📨 Received message: {msg_type}")
                            
                    except json.JSONDecodeError:
                        print(f"⚠️ Invalid JSON message: {message.get('text', '')}")
                        
            except WebSocketDisconnect:
                print("🔌 Client disconnected from Gemini Realtime endpoint")
                break
            except Exception as e:
                # Only log if not already stopping
                if bridge.is_connected:
                    print(f"❌ Error processing message: {e}")
                try:
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e)
                    })
                except:
                    pass
                    
    except Exception as e:
        print(f"❌ Unexpected error in Gemini Realtime endpoint: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await bridge.close()
        print("🔌 Gemini Realtime connection closed")

