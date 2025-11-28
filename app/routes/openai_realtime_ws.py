"""
OpenAI Realtime API WebSocket Handler
Implements high-speed bidirectional audio streaming for real-time conversation
"""

import asyncio
import json
import base64
import os
import io
import re
import time
from contextlib import suppress
from typing import Optional, Dict, Any, Tuple, Awaitable, Callable
from pydub import AudioSegment
import websockets
import httpx
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK
from app.config import (
    OPENAI_API_KEY,
    ELEVEN_API_KEY,
    ELEVEN_REALTIME_VOICE_ID,
    ELEVEN_REALTIME_MODEL_ID,
)

router = APIRouter()

NON_ENGLISH_SCRIPT_PATTERN = re.compile(
    r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF\u0900-\u097F]"
)
OPENAI_CHAT_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"
TRANSLATION_MODEL = os.getenv("OPENAI_TRANSLATION_MODEL", "gpt-4o-mini")
ENGLISH_ENFORCEMENT_SYSTEM_PROMPT = (
    "You convert tutor replies into English-only messages for Pakistani students. "
    "Always respond ONLY in English and follow this structure:\n"
    "In English you say this: <translated sentence>.\n"
    "Add one short grammar or word-choice reminder in English.\n"
    "Ask the learner to repeat the sentence in English.\n"
    "Keep tone warm, encouraging, and concise. Never include non-English text."
)
ENGLISH_FALLBACK_MESSAGE = (
    "In English you say this: Let's keep speaking in English only. "
    "Remember to translate your sentence, then repeat it in English for me."
)
_translation_http_client: Optional[httpx.AsyncClient] = None


async def get_translation_http_client() -> httpx.AsyncClient:
    """Return a singleton HTTP client for translation fallbacks."""
    global _translation_http_client
    if _translation_http_client is None:
        _translation_http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(20.0, connect=5.0)
        )
    return _translation_http_client


# Base persona for all modes
BASE_PERSONA = (
    "You are an AI English Tutor for Pakistani students (Grades 6–12).\n\n"
    "Your tone is warm, gentle, encouraging, and locally relatable (cricket, chai, city life, exams, rural Pakistan experiences).\n\n"
    "### ABSOLUTE RULE — ENGLISH ONLY\n"
    "You must ALWAYS respond in English. Never reply in Urdu, Hindi, Roman Urdu, or any non-English language.\n\n"
    "### Urdu / Roman Urdu Bridge\n"
    "If the learner speaks in Urdu / Roman Urdu / Hindi or mixes languages:\n"
    "1. Translate their message to English.\n"
    "2. Respond EXACTLY in this format: \"In English you say this: [translated sentence].\"\n"
    "3. Provide a short, friendly grammar or word choice reminder (in ENGLISH).\n"
    "4. Ask them to repeat the sentence in English.\n"
    "5. Never reply in the non-English language — ever.\n\n"
    "### Conversational Style\n"
    "- Replies are concise (1–2 sentences) unless teaching requires an example.\n"
    "- Encourage often, correct gently.\n"
    "- Sound like a supportive Pakistani teacher/mentor.\n"
    "- Acknowledge good effort even while correcting.\n"
    "- Keep the pacing natural and interactive.\n\n"
)


# Mode-specific instructions
SENTENCE_STRUCTURE_INSTRUCTION = """
You are an AI English Tutor operating in STRICT "Sentence Structure Mode".

RULES:
1. If the user speaks or types an incorrect English sentence, you must NOT respond to the meaning. 
   Your ONLY job is to correct the structure by replying:
   “A better way to say that is: ‘{corrected sentence}’. Try repeating this.”

2. Do NOT continue the conversation until the user correctly repeats the corrected sentence.
   - If the user repeats it correctly → respond normally to that sentence.
   - If the user repeats it incorrectly → correct again using the same format.

3. Corrections must be simple, gentle, and A1-A2 level.

4. You must NOT:
   - guess their intent  
   - add extra meaning  
   - change the topic  
   - start small talk  
   - explain grammar unless needed  

WORKFLOW:
- Incorrect → correct + ask to repeat  
- Correct repeat → reply normally  
- Incorrect repeat → correct again  

Stay fully consistent. Prioritize structure correction over conversation.
Note: Correct the user speaked sentence.
"""


GRAMMAR_INSTRUCTION = (
    BASE_PERSONA +
    "### ROLE: The Grammar Detective\n\n"
    "- **Goal**: Identify and fix grammatical errors (Tenses, Prepositions, Articles, Plurals).\n\n"
    "- **Methodology**:\n"
    "  1. If they make a grammar mistake, gently pause the conversation.\n"
    "  2. Example: If they say 'She don't like it', say: 'Ah, remember for She, we say doesn't. Try saying: She doesn't like it.'\n"
    "  3. **Strictness**: Be more precise than usual. Do not let errors slide.\n\n"
    "- **Key Areas**: Past vs Present tense, He/She/It rules, In/On/At usage.\n"
)

VOCABULARY_INSTRUCTION = (
    BASE_PERSONA +
    "### ROLE: The Vocabulary Builder\n\n"
    "- **Critical Rule**: After greeting, you MUST stay in vocabulary-building mode. Do NOT drift into general conversation, topic discussion, or casual chat.\n"
    "- **Opening Hook**: The greeting already includes an engaging hook. After the greeting, immediately proceed with vocabulary activities.\n"
    "- **Goal**: Expand the student's word bank by swapping simple words with vivid vocabulary. This is your ONLY focus.\n"
    "- **What NOT to do**:\n"
    "  - Do NOT ask open-ended questions like \"What would you like to discuss?\" or \"Tell me about your day\"\n"
    "  - Do NOT engage in general conversation topics\n"
    "  - Do NOT drift away from vocabulary building activities\n"
    "  - Do NOT let the conversation become casual chat\n"
    "- **What TO do**:\n"
    "  1. After greeting, immediately introduce ONE new word at a time (definition + example tied to Pakistani life).\n"
    "  2. Ask the learner to use that word in a sentence.\n"
    "  3. When they use a basic word (good, big, sad, happy, nice, bad), immediately offer 2-3 richer synonyms and have them repeat.\n"
    "  4. Use mini challenges: \"Give me a stronger word for [basic word]!\"\n"
    "  5. Keep the conversation focused on vocabulary expansion only.\n"
    "  6. After teaching a word, move to the next word or vocabulary activity.\n"
    "- **Response Pattern**:\n"
    "  - If learner says something unrelated to vocabulary, gently redirect: \"Great! Now let's learn a new word. [introduce word]\"\n"
    "  - If learner uses a basic word, immediately correct: \"Instead of '[basic word]', try using '[advanced word]' or '[synonym]'. Can you say that?\"\n"
    "  - Always bring the conversation back to vocabulary building.\n"
    "- **Level Guidance**:\n"
    "  - Grades 6–8: words like delicious, massive, exhausted, brilliant, enormous, thrilled.\n"
    "  - Grades 9–12: words like exquisite, resilient, intricate, profound, magnificent, sophisticated.\n"
    "- **Flow**: Greeting → Introduce Word 1 → Practice → Introduce Word 2 → Practice → Introduce Word 3 → Practice → Continue with vocabulary activities.\n"
)

TOPIC_MODERATOR_INSTRUCTION = (
    BASE_PERSONA +
    "### ROLE: Topic Discussion Moderator\n\n"
    "- **Goal**: Deep dive into a specific topic to improve fluency and critical thinking.\n\n"
    "- **Methodology**:\n"
    "  1. Once a topic is picked, stay on it.\n"
    "  2. Ask 'Why' and 'How' questions to force longer answers.\n"
    "  3. **Correction**: minimal correction. Focus on CONFIDENCE and FLOW. Only correct if the meaning is lost.\n"
)

# Default system prompt (general conversation)
SYSTEM_PROMPT = (
    BASE_PERSONA +
    "### ROLE: General Conversation Partner\n"
    "- **Goal**: Casual English conversation that builds confidence.\n"
    "- **Corrections**: Use gentle recasting. If learner says \"Me go market\", say \"Oh, you go to the market? What do you buy there?\"\n"
    "- **Flow**: Ask open-ended questions about school, hobbies, cities, sports, community life.\n"
    "- **Language Guard**: Even when learner uses Urdu/Hindi, always switch to English with the bridge format.\n"
)

# Mode to system prompt mapping
MODE_PROMPTS = {
    "sentence_structure": SENTENCE_STRUCTURE_INSTRUCTION,
    "grammar_practice": GRAMMAR_INSTRUCTION,
    "vocabulary_builder": VOCABULARY_INSTRUCTION,
    "topic_discussion": TOPIC_MODERATOR_INSTRUCTION,
    "general": SYSTEM_PROMPT,
}

# Mode-specific greeting messages
MODE_GREETINGS = {
    "sentence_structure": "Hello {name}! We’re going to build precise sentences together. Tell me one thing you did today and we will polish the sentence step by step.",
    "grammar_practice": "Hi {name}! Let's polish your grammar. Tell me about your favorite hobby.",
    "vocabulary_builder": "Hello {name}! Let's grow your vocabulary! I have 3 new words ready for you. Ready for your first one?",
    "topic_discussion": "Hi {name}! I'm ready to chat. Pick a topic: 1) Cricket & Sports, 2) Food & Cooking, or 3) Travel & Cities. Or suggest your own!",
    "general": "Hi {name}, I'm your AI English tutor. How can I help you today?",
}

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

# ElevenLabs TTS configuration
ELEVENLABS_WS_BASE = "wss://api.elevenlabs.io/v1"
ELEVENLABS_OUTPUT_FORMAT = "pcm_24000"
ELEVENLABS_CHUNK_SCHEDULE = [50]  # Minimum 50ms for fastest response
ELEVENLABS_MIN_PARTIAL_CHARS = 60
ELEVENLABS_DEFAULT_VOICE_SETTINGS = {
    "stability": 0.7,
    "similarity_boost": 0.8,
    "style": 0.0,
    "use_speaker_boost": True,
    "speed": 0.90,  # Slow down voice to 85% speed (range: 0.25-4.0, 1.0 = normal)
}


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
    Now uses ElevenLabs TTS for audio output instead of OpenAI audio.
    """
    
    def __init__(self, client_ws: WebSocket, mode: str = "general"):
        self.client_ws = client_ws
        self.mode = mode  # Store the learning mode
        self.openai_ws: Optional[websockets.WebSocketClientProtocol] = None
        self.session_id: Optional[str] = None
        self.is_connected = False
        self.session_ready = False  # Track if session is fully configured
        self.response_audio_chunks: list = []
        self.response_text: str = ""
        self.raw_response_text: str = ""
        self.non_english_detected: bool = False
        self.non_english_buffer: str = ""
        self.response_done = True  # Start as True so first commit can proceed
        self.partial_text_buffer: str = ""
        self.min_partial_segment_chars = ELEVENLABS_MIN_PARTIAL_CHARS
        self.ws_send_lock = asyncio.Lock()
        # Track audio buffer to ensure we have enough before committing
        self.audio_buffer_size_bytes: int = 0
        self.audio_chunks_count: int = 0
        # Minimum audio required: 100ms at 24kHz, 16-bit, mono = 2400 samples * 2 bytes = 4800 bytes
        
        # PCM audio buffering for smooth playback (reduce gaps)
        self.pcm_audio_buffer: list[bytes] = []  # Buffer PCM chunks before converting to WAV
        self.pcm_buffer_size_bytes: int = 0  # Total bytes in buffer
        self.pcm_buffer_lock = asyncio.Lock()  # Lock for buffer operations
        self.pcm_buffer_last_flush_time: float = 0  # Track last flush time for timeout
        # Minimum buffer size before sending: ~100ms = 4800 bytes at 24kHz, 16-bit, mono
        # Reduced from 200ms to 100ms for faster response while still reducing gaps
        self.MIN_PCM_BUFFER_BYTES = 4800  # ~100ms of audio
        # Maximum buffer size: ~500ms = 24000 bytes (prevents too much latency)
        self.MAX_PCM_BUFFER_BYTES = 24000  # ~500ms of audio
        # Maximum time to wait before flushing (even if buffer is small): 100ms
        # Reduced from 150ms to 100ms for faster response
        self.PCM_BUFFER_MAX_WAIT_MS = 100
        self.MIN_AUDIO_BYTES = 4800  # ~100ms of audio
        # Track if we've received any errors after appending
        self.append_errors: list = []
        # ElevenLabs streaming session
        self.tts_stream: Optional["ElevenLabsStreamSession"] = None
        
    async def connect_to_openai(self):
        """Establish connection to OpenAI Realtime API"""
        try:
            self.openai_ws = await websockets.connect(
                OPENAI_REALTIME_URI,
                additional_headers=OPENAI_HEADERS
            )
            
            # Configure session - TEXT ONLY output (no audio from OpenAI)
            # IMPORTANT: Disable automatic turn detection to prevent buffer clearing
            # We'll manually commit when ready
            # Get mode-specific system prompt
            system_prompt = MODE_PROMPTS.get(self.mode, SYSTEM_PROMPT)
            print(f"📝 Using system prompt for mode: {self.mode}")
            
            session_config = {
                "type": "session.update",
                "session": {
                    "modalities": ["audio", "text"],  # Input: audio, Output: text only
                    "input_audio_format": INPUT_AUDIO_FORMAT,
                    "output_audio_format": OUTPUT_AUDIO_FORMAT,
                    "instructions": system_prompt,
                    "temperature": 0.8,
                    "turn_detection": None  # Disable automatic VAD - we'll commit manually
                }
            }
            
            print(f"📤 Sending session configuration (TEXT-ONLY output, VAD disabled for manual commit)...")
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
                    
                    # If mode was set before session was ready, update instructions now
                    if hasattr(self, '_pending_mode_update'):
                        mode = self._pending_mode_update
                        system_prompt = MODE_PROMPTS.get(mode, SYSTEM_PROMPT)
                        update_config = {
                            "type": "session.update",
                            "session": {
                                "instructions": system_prompt,
                            }
                        }
                        print(f"📝 Applying pending mode update: {mode}")
                        await self.openai_ws.send(json.dumps(update_config))
                        delattr(self, '_pending_mode_update')
                    
                elif message_type == "input_audio_buffer.speech_started":
                    print("🎤 Speech detected in audio buffer")
                    
                elif message_type == "input_audio_buffer.speech_stopped":
                    print("🔇 Speech stopped in audio buffer")
                    
                elif message_type == "input_audio_buffer.commit":
                    # Confirmation that commit was received
                    print("✅ Input audio buffer commit confirmed by OpenAI")
                    
                elif message_type == "response.audio.delta":
                    # OpenAI audio output - IGNORE (we use ElevenLabs instead)
                    # This should not happen if we configured text-only, but handle gracefully
                    print("⚠️ Received audio delta from OpenAI (unexpected - using ElevenLabs TTS)")
                    
                elif message_type in {
                    "response.output_text.delta",
                    "response.text.delta",
                    "response.audio_transcript.delta",
                }:
                    # Normalize delta payloads - OpenAI can send str, dict, or list segments
                    delta_payload = data.get("delta", "")
                    delta_text = ""
                    if isinstance(delta_payload, str):
                        delta_text = delta_payload
                    elif isinstance(delta_payload, dict):
                        delta_text = delta_payload.get("text") or delta_payload.get("content", "")
                    elif isinstance(delta_payload, list):
                        delta_text = "".join(
                            segment.get("text", "") if isinstance(segment, dict) else str(segment)
                            for segment in delta_payload
                        )
                    else:
                        delta_text = str(delta_payload or "")

                    if delta_text:
                        self.raw_response_text += delta_text
                        if self._contains_non_english_script(delta_text):
                            if not self.non_english_detected:
                                print("⚠️ Detected non-English script in OpenAI response, enforcing English-only fallback")
                            self.non_english_detected = True
                            self.non_english_buffer += delta_text
                            # Clear any partial English so we can regenerate later
                            self.response_text = ""
                            self.partial_text_buffer = ""
                            continue
                        
                        if self.non_english_detected:
                            self.non_english_buffer += delta_text
                            continue
                        
                        self.response_text += delta_text
                        self.partial_text_buffer += delta_text
                        await self._try_flush_partial_segment()
                        print(f"📝 Text delta received ({len(delta_text)} chars) | total so far {len(self.response_text)} chars")
                        await self._send_json({
                            "type": "transcript_delta",
                            "text": self.response_text
                        })
                        
                elif message_type in {
                    "response.audio_transcript.done",
                    "response.output_text.done",
                    "response.text.done",
                }:
                    # Final transcript - flush remaining text but DON'T finalize stream yet
                    text_payload = data.get("text")
                    raw_final_text = ""
                    if isinstance(text_payload, str):
                        raw_final_text = text_payload
                    elif isinstance(text_payload, dict):
                        raw_final_text = text_payload.get("text", "")
                    elif text_payload is None:
                        raw_final_text = self.raw_response_text or self.response_text
                    else:
                        raw_final_text = str(text_payload or "")

                    self.raw_response_text = raw_final_text
                    needs_enforcement = self.non_english_detected or self._contains_non_english_script(raw_final_text)
                    final_text = raw_final_text

                    if needs_enforcement:
                        print("⚠️ Final response contained non-English text. Regenerating with enforcement...")
                        translated = await self._rewrite_text_to_english(raw_final_text)
                        if translated:
                            final_text = translated
                            print("✅ English enforcement succeeded for final response")
                        else:
                            final_text = ENGLISH_FALLBACK_MESSAGE
                            print("⚠️ English enforcement failed, using fallback message")
                        # Reset buffers to the enforced English output
                        self.non_english_detected = False
                        self.non_english_buffer = ""
                        self.partial_text_buffer = final_text
                    # When no enforcement is needed we leave the partial buffer untouched

                    self.response_text = final_text
                    print(f"✅ Text response complete ({len(final_text)} chars)")
                    
                    # Send final transcript to client
                    await self._send_json({
                        "type": "transcript_done",
                        "text": final_text
                    })
                    
                    # Flush remaining buffered text to ElevenLabs stream (but don't finalize yet)
                    await self._try_flush_partial_segment(force=True)
                    
                elif message_type == "response.done":
                    # Response complete - NOW finalize the ElevenLabs stream
                    print("✅ OpenAI response done - finalizing ElevenLabs TTS stream")
                    await self._finalize_tts_stream(force=True)

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
                    
                    await self._send_json({
                        "type": "error",
                        "message": error_msg,
                        "code": error_code
                    })
                    if error_code not in {"response_in_progress", "conversation_already_has_active_response"}:
                        await self._finalize_tts_stream(force=True)
                else:
                    # Log any unexpected message types for debugging
                    print(f"ℹ️ Unhandled OpenAI message type: {message_type} | payload keys: {list(data.keys())}")
                    
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
                await self._send_json({
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
                await self._send_json({
                    "type": "error",
                    "message": error_msg,
                    "code": "response_in_progress"
                })
                return
            
            # Check if we have enough audio before committing
            if self.audio_buffer_size_bytes < self.MIN_AUDIO_BYTES:
                error_msg = f"Not enough audio to commit. Have {self.audio_buffer_size_bytes} bytes, need at least {self.MIN_AUDIO_BYTES} bytes (~100ms)"
                print(f"⚠️ {error_msg}")
                await self._send_json({
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
            self.raw_response_text = ""
            self.non_english_detected = False
            self.non_english_buffer = ""
            self.partial_text_buffer = ""
            self.response_done = False  # Mark that we're waiting for a response
            self.tts_finalized = False
            
            # Clear PCM buffer for new response (prevent mixing audio from different responses)
            async with self.pcm_buffer_lock:
                self.pcm_audio_buffer.clear()
                self.pcm_buffer_size_bytes = 0
            
            # Abort any existing TTS stream from previous response (shouldn't happen, but safety check)
            if self.tts_stream:
                print("⚠️ Aborting previous TTS stream before starting new response")
                await self.tts_stream.abort()
                self.tts_stream = None
            
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
            
            # Request response immediately after commit - TEXT ONLY (no audio)
            response_message = {
                "type": "response.create",
                "response": {
                    "modalities": ["text"],  # Only text output - audio comes from ElevenLabs
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
            if self.tts_stream:
                await self.tts_stream.abort()
                self.tts_stream = None
            self.is_connected = False
        except Exception as e:
            print(f"⚠️ Error closing connections: {e}")

    async def _ensure_tts_stream(self):
        if self.tts_stream is None:
            print("🎧 Starting ElevenLabs realtime stream session")
            self.tts_stream = ElevenLabsStreamSession(
                api_key=ELEVEN_API_KEY,
                voice_id=ELEVEN_REALTIME_VOICE_ID,
                model_id=ELEVEN_REALTIME_MODEL_ID,
                voice_settings=ELEVENLABS_DEFAULT_VOICE_SETTINGS,
                output_format=ELEVENLABS_OUTPUT_FORMAT,
                chunk_schedule=ELEVENLABS_CHUNK_SCHEDULE,
                audio_callback=self._handle_elevenlabs_audio_chunk,
            )
            await self.tts_stream.start()

    async def _handle_elevenlabs_audio_chunk(self, pcm_chunk: bytes):
        """Buffer PCM chunks and send as larger WAV files to reduce gaps."""
        print(f"🎵 Received PCM chunk from ElevenLabs: {len(pcm_chunk)} bytes")
        current_time = time.time()
        
        # Prepare data to flush (if needed) while holding lock
        should_flush = False
        flush_force = False
        combined_pcm = None
        buffer_size = 0
        chunk_count = 0
        
        async with self.pcm_buffer_lock:
            # Initialize last flush time if this is the first chunk
            if not self.pcm_audio_buffer:
                self.pcm_buffer_last_flush_time = current_time
                print(f"🎧 Initializing PCM buffer (first chunk)")
            
            self.pcm_audio_buffer.append(pcm_chunk)
            self.pcm_buffer_size_bytes += len(pcm_chunk)
            
            # Check if we should flush:
            # 1. Buffer is large enough (size-based flush)
            # 2. Too much time has passed since last flush (timeout-based flush)
            time_since_flush_ms = (current_time - self.pcm_buffer_last_flush_time) * 1000
            size_based = self.pcm_buffer_size_bytes >= self.MIN_PCM_BUFFER_BYTES
            timeout_based = time_since_flush_ms >= self.PCM_BUFFER_MAX_WAIT_MS and self.pcm_buffer_size_bytes > 0
            
            should_flush = size_based or timeout_based
            
            print(f"🎧 PCM buffer: {self.pcm_buffer_size_bytes} bytes, {len(self.pcm_audio_buffer)} chunks, {time_since_flush_ms:.0f}ms since last flush (size={size_based}, timeout={timeout_based})")
            
            if should_flush:
                print(f"🔄 Flushing PCM buffer ({'size' if size_based else 'timeout'})")
                # Check if we should actually flush
                if not timeout_based and self.pcm_buffer_size_bytes < self.MIN_PCM_BUFFER_BYTES:
                    should_flush = False
                else:
                    # Extract data to flush while holding lock
                    combined_pcm = b''.join(self.pcm_audio_buffer)
                    buffer_size = self.pcm_buffer_size_bytes
                    chunk_count = len(self.pcm_audio_buffer)
                    flush_force = timeout_based
                    
                    # Clear buffer
                    self.pcm_audio_buffer.clear()
                    self.pcm_buffer_size_bytes = 0
                    self.pcm_buffer_last_flush_time = time.time()
        
        # Now do async operations outside the lock
        if should_flush and combined_pcm:
            print(f"🔄 Converting {buffer_size} bytes PCM ({chunk_count} chunks) to WAV...")
            wav_chunk = await convert_pcm16_to_wav(combined_pcm)
            await self._send_bytes(wav_chunk)
            print(f"📤 Sent buffered WAV chunk: {buffer_size} bytes PCM → {len(wav_chunk)} bytes WAV")

    def _contains_non_english_script(self, text: str) -> bool:
        if not text:
            return False
        return bool(NON_ENGLISH_SCRIPT_PATTERN.search(text))

    async def _rewrite_text_to_english(self, original_text: str) -> Optional[str]:
        cleaned = (original_text or "").strip()
        if not cleaned:
            return None
        try:
            client = await get_translation_http_client()
            payload = {
                "model": TRANSLATION_MODEL,
                "temperature": 0.1,
                "messages": [
                    {
                        "role": "system",
                        "content": ENGLISH_ENFORCEMENT_SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": (
                            "Rewrite the tutor reply below so it strictly follows the rules.\n"
                            "Original tutor reply:\n"
                            f"{cleaned}"
                        ),
                    },
                ],
                "max_tokens": min(512, max(160, len(cleaned) // 2 + 60)),
            }
            headers = {
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            }
            response = await client.post(
                OPENAI_CHAT_COMPLETIONS_URL,
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
            choices = data.get("choices") or []
            if not choices:
                return None
            english_text = (choices[0]
                            .get("message", {})
                            .get("content", "")
                            .strip())
            return english_text or None
        except Exception as exc:
            print(f"⚠️ English enforcement failed: {exc}")
            return None
    
    def _flush_pcm_buffer_internal(self, force: bool = False):
        """Internal flush function - assumes lock is already held. Returns data to process."""
        if not self.pcm_audio_buffer:
            print("⚠️ Flush requested but buffer is empty")
            return None, 0, 0
        
        # Only flush if we have enough data OR if forced (timeout or final flush)
        if not force and self.pcm_buffer_size_bytes < self.MIN_PCM_BUFFER_BYTES:
            print(f"⚠️ Buffer too small ({self.pcm_buffer_size_bytes} < {self.MIN_PCM_BUFFER_BYTES}), not flushing")
            return None, 0, 0
        
        # Concatenate all PCM chunks
        combined_pcm = b''.join(self.pcm_audio_buffer)
        buffer_size = self.pcm_buffer_size_bytes
        chunk_count = len(self.pcm_audio_buffer)
        
        # Clear buffer
        self.pcm_audio_buffer.clear()
        self.pcm_buffer_size_bytes = 0
        self.pcm_buffer_last_flush_time = time.time()
        
        return combined_pcm, buffer_size, chunk_count
    
    async def _flush_pcm_buffer(self, force: bool = False):
        """Public flush function - acquires lock before flushing."""
        combined_pcm = None
        buffer_size = 0
        chunk_count = 0
        
        async with self.pcm_buffer_lock:
            combined_pcm, buffer_size, chunk_count = self._flush_pcm_buffer_internal(force=force)
        
        # Do async operations outside the lock
        if combined_pcm:
            print(f"🔄 Converting {buffer_size} bytes PCM ({chunk_count} chunks) to WAV...")
            wav_chunk = await convert_pcm16_to_wav(combined_pcm)
            await self._send_bytes(wav_chunk)
            print(f"📤 Sent buffered WAV chunk: {buffer_size} bytes PCM → {len(wav_chunk)} bytes WAV")

    async def _send_tts_text(self, text: str):
        cleaned = text.strip()
        if not cleaned:
            return
        await self._ensure_tts_stream()
        # Add trailing space to help word separation
        payload_text = cleaned if cleaned.endswith(" ") else cleaned + " "
        await self.tts_stream.send_text(payload_text)

    async def _try_flush_partial_segment(self, force: bool = False):
        """Flush buffered sentences to ElevenLabs as soon as possible."""
        if self.non_english_detected and not force:
            print("⏸️ Skipping TTS flush due to pending English enforcement")
            return
        buffer = self.partial_text_buffer
        if not buffer.strip():
            return
        if not force:
            if len(buffer.strip()) < self.min_partial_segment_chars:
                return
            last_sentence_idx = max(buffer.rfind("."), buffer.rfind("!"), buffer.rfind("?"))
            if last_sentence_idx == -1:
                return
            segment = buffer[: last_sentence_idx + 1].strip()
            self.partial_text_buffer = buffer[last_sentence_idx + 1 :]
        else:
            segment = buffer.strip()
            self.partial_text_buffer = ""

        if segment:
            print(f"🔊 Flushing TTS segment ({len(segment)} chars, force={force})")
            await self._send_tts_text(segment)

    async def send_greeting(self, greeting_text: str):
        """Send greeting message through ElevenLabs TTS stream."""
        try:
            print(f"👋 [GREETING] Sending greeting text: '{greeting_text}'")
            
            # Ensure TTS stream is ready
            await self._ensure_tts_stream()
            
            # Send greeting text to ElevenLabs
            await self._send_tts_text(greeting_text)
            
            # Finalize the stream after greeting is sent
            await self._finalize_tts_stream(force=True)
            
            # Send greeting completion message
            await self._send_json({
                "type": "greeting_done",
                "text": greeting_text
            })
            
            print("✅ [GREETING] Greeting sent successfully")
        except Exception as e:
            print(f"❌ [GREETING] Error sending greeting: {e}")
            import traceback
            traceback.print_exc()
            await self._send_json({
                "type": "error",
                "message": f"Failed to send greeting: {str(e)}",
                "code": "greeting_error"
            })

    async def _finalize_tts_stream(self, force: bool = False):
        """Finalize ElevenLabs stream and notify client."""
        try:
            await self._try_flush_partial_segment(force=force)
            if self.tts_stream:
                await self.tts_stream.finalize()
                self.tts_stream = None
            
            # Flush any remaining PCM buffer (force flush)
            await self._flush_pcm_buffer(force=True)
            
            if not self.response_done:
                self.response_done = True
                # Only send if connection is still open
                if self.is_connected:
                    await self._send_json({
                        "type": "response_done"
                    })
        except Exception as e:
            print(f"⚠️ Error finalizing TTS stream: {e}")
            # Mark as done even if we can't send the message
            self.response_done = True

    async def _send_json(self, payload: Dict[str, Any]):
        try:
            async with self.ws_send_lock:
                await self.client_ws.send_json(payload)
        except RuntimeError as e:
            # Connection already closed - this is expected when client disconnects
            if "websocket.send" in str(e) or "websocket.close" in str(e):
                print("⚠️ Client WebSocket closed, skipping send_json")
            else:
                print(f"⚠️ RuntimeError sending JSON: {e}")
            self.is_connected = False
        except Exception as e:
            # Other connection errors
            print(f"⚠️ Error sending JSON (connection may be closed): {e}")
            self.is_connected = False

    async def _send_bytes(self, payload: bytes):
        try:
            async with self.ws_send_lock:
                await self.client_ws.send_bytes(payload)
        except RuntimeError as e:
            # Connection already closed - this is expected when client disconnects
            if "websocket.send" in str(e) or "websocket.close" in str(e):
                print("⚠️ Client WebSocket closed, skipping send_bytes")
            else:
                print(f"⚠️ RuntimeError sending bytes: {e}")
            self.is_connected = False
        except Exception as e:
            # Other connection errors
            print(f"⚠️ Error sending bytes (connection may be closed): {e}")
            self.is_connected = False


class ElevenLabsStreamSession:
    """Manage a realtime ElevenLabs TTS WebSocket session."""

    def __init__(
        self,
        *,
        api_key: str,
        voice_id: str,
        model_id: str,
        voice_settings: Dict[str, Any],
        output_format: str,
        chunk_schedule: list[int],
        audio_callback: Callable[[bytes], Awaitable[None]],
    ):
        self.api_key = api_key
        self.voice_id = voice_id
        self.model_id = model_id
        self.voice_settings = voice_settings or {}
        self.output_format = output_format
        self.chunk_schedule = chunk_schedule
        self.audio_callback = audio_callback
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.receiver_task: Optional[asyncio.Task] = None
        self.closed = False
        self.finalizing = False

    async def start(self):
        query = f"model_id={self.model_id}&output_format={self.output_format}"
        uri = f"{ELEVENLABS_WS_BASE}/text-to-speech/{self.voice_id}/stream-input?{query}"
        headers = [("xi-api-key", self.api_key)]
        self.ws = await websockets.connect(uri, additional_headers=headers, max_queue=None)
        init_payload = {
            "text": " ",
            "voice_settings": self.voice_settings,
            "generation_config": {
                "chunk_length_schedule": self.chunk_schedule,
                "optimize_streaming_latency": 4,
            },
            "try_trigger_generation": True,
        }
        await self.ws.send(json.dumps(init_payload))
        self.receiver_task = asyncio.create_task(self._receive_loop())

    async def send_text(self, text: str):
        if not self.ws or self.closed:
            return
        payload = {
            "text": text,
            "try_trigger_generation": True,
        }
        await self.ws.send(json.dumps(payload))

    async def finalize(self):
        if not self.ws or self.closed:
            return
        if not self.finalizing:
            self.finalizing = True
            await self.ws.send(json.dumps({"text": ""}))
        if self.receiver_task:
            await self.receiver_task
        if not self.closed:
            await self.ws.close()
            self.closed = True

    async def abort(self):
        if self.receiver_task:
            self.receiver_task.cancel()
            with suppress(asyncio.CancelledError):
                await self.receiver_task
        if self.ws and not self.closed:
            await self.ws.close()
        self.closed = True

    async def _receive_loop(self):
        assert self.ws is not None
        try:
            async for message in self.ws:
                data = json.loads(message)
                
                # Handle error messages from ElevenLabs
                if "error" in data:
                    error_msg = data.get("error", {})
                    print(f"❌ ElevenLabs error: {error_msg}")
                    self.closed = True
                    break
                
                # Handle audio chunks
                audio_b64 = data.get("audio")
                if audio_b64:
                    chunk = base64.b64decode(audio_b64)
                    print(f"🎵 Received audio from ElevenLabs: {len(chunk)} bytes PCM")
                    await self.audio_callback(chunk)
                else:
                    # Log other message types for debugging
                    msg_type = data.get("type", "unknown")
                    if msg_type != "pong":  # Ignore pong messages
                        print(f"ℹ️ ElevenLabs message: {msg_type} | keys: {list(data.keys())}")
        except ConnectionClosedError as exc:
            print(f"⚠️ ElevenLabs stream closed unexpectedly: {exc}")
        except ConnectionClosedOK:
            pass
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse ElevenLabs message: {e}")
        finally:
            self.closed = True


@router.websocket("/ws/openai-realtime")
async def openai_realtime_conversation(websocket: WebSocket):
    """
    WebSocket endpoint for OpenAI Realtime API conversation.
    Handles bidirectional audio streaming for ultra-low latency.
    """
    await websocket.accept()
    print("✅ Client connected to OpenAI Realtime endpoint")
    
    bridge: Optional[OpenAIRealtimeBridge] = None
    mode_initialized = False  # Track if mode has been set and OpenAI connected
    
    try:
        # Send connection confirmation immediately
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
                    # Check if bridge is initialized (should have been initialized by greeting)
                    if not mode_initialized or bridge is None:
                        print("⚠️ Bridge not initialized yet. Please send greeting first.")
                        await websocket.send_json({
                            "type": "error",
                            "message": "Please send greeting message first to initialize the session.",
                            "code": "not_initialized"
                        })
                        continue
                    
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
                            # Check if bridge is initialized
                            if not mode_initialized or bridge is None:
                                print("⚠️ Bridge not initialized yet. Please send greeting first.")
                                await websocket.send_json({
                                    "type": "error",
                                    "message": "Please send greeting message first to initialize the session.",
                                    "code": "not_initialized"
                                })
                                continue
                            
                            # Client is done sending audio, commit and get response
                            print("📤 Committing audio and requesting response")
                            await bridge.commit_audio_and_get_response()
                            
                        elif message_type == "greeting":
                            # Handle greeting message
                            user_name = message.get("user_name", "there")
                            mode = message.get("mode", "general")
                            
                            # Initialize bridge with correct mode if not already initialized
                            if not mode_initialized:
                                print(f"🎯 Initializing bridge with mode: {mode}")
                                bridge = OpenAIRealtimeBridge(websocket, mode=mode)
                                await bridge.connect_to_openai()  # Connect with correct mode from start
                                mode_initialized = True
                                print(f"✅ Bridge initialized and OpenAI connected with mode: {mode}")
                            else:
                                # Bridge already initialized, update mode if different
                                if mode != bridge.mode:
                                    print(f"🔄 Updating bridge mode from {bridge.mode} to {mode}")
                                    bridge.mode = mode
                                    
                                    # Update system prompt in OpenAI session if connected and ready
                                    if bridge.is_connected and bridge.openai_ws:
                                        system_prompt = MODE_PROMPTS.get(mode, SYSTEM_PROMPT)
                                        if bridge.session_ready:
                                            # Session is ready, update immediately
                                            update_config = {
                                                "type": "session.update",
                                                "session": {
                                                    "instructions": system_prompt,
                                                }
                                            }
                                            print(f"📝 Updating OpenAI session with new system prompt for mode: {mode}")
                                            await bridge.openai_ws.send(json.dumps(update_config))
                                        else:
                                            # Session not ready yet, store for later
                                            bridge._pending_mode_update = mode
                                            print(f"📝 Storing mode update for when session is ready: {mode}")
                            
                            print(f"👋 [GREETING] Processing greeting for user: {user_name}, mode: {mode}")
                            
                            # Get mode-specific greeting
                            greeting_template = MODE_GREETINGS.get(mode, MODE_GREETINGS["general"])
                            greeting_text = greeting_template.format(name=user_name)
                            
                            # Send greeting text through ElevenLabs TTS stream
                            await bridge.send_greeting(greeting_text)
                            
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
