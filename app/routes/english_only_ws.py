"""
English-Only AI Tutor WebSocket Handler

This module provides a ChatGPT-like voice mode experience for English learning:
- Personalized greetings with user's name
- Thick accent detection and correction
- Broken English detection and correction
- Natural conversation flow
- Prolonged pause detection (7+ seconds)
- Friendly, human-like tone

Features:
1. Greet user by name
2. Listen continuously to user input
3. Detect accent/grammar issues
4. Provide corrections with pronunciation
5. Stay in listening mode for next input
6. Handle prolonged silence with gentle prompts
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.translation import translate_urdu_to_english, translate_to_urdu
from app.services.tts import synthesize_speech_bytes,synthesize_speech
from app.services.feedback import analyze_english_input_eng_only
from app.services import stt
from app.utils.profiler import Profiler
import json
import base64
import asyncio
from functools import lru_cache
import httpx
from concurrent.futures import ThreadPoolExecutor
import threading

# OpenTelemetry imports
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

router = APIRouter()

# Initialize OpenTelemetry tracer
tracer = trace.get_tracer(__name__)

# Global thread pool for CPU-intensive tasks
thread_pool = ThreadPoolExecutor(max_workers=4)

# Cache for frequently used corrections and TTS
correction_cache = {}
tts_cache = {}

# Connection pool for HTTP clients
http_client = None

def get_http_client():
    global http_client
    if http_client is None:
        http_client = httpx.AsyncClient(timeout=30.0)
    return http_client

async def safe_send_json(websocket: WebSocket, data: dict):
    try:
        await websocket.send_json(data)
    except Exception as e:
        print(f"Failed to send JSON: {e}")

async def safe_send_bytes(websocket: WebSocket, data: bytes):
    try:
        await websocket.send_bytes(data)
    except Exception as e:
        print(f"Failed to send binary: {e}")

# Async wrapper for CPU-intensive STT
async def async_transcribe_audio_eng_only(audio_bytes: bytes):
    """Run English-Only STT in thread pool to avoid blocking"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        thread_pool, 
        stt.transcribe_audio_bytes_eng_only, 
        audio_bytes
    )

# Async wrapper for English feedback analysis
async def async_analyze_english_input(user_text: str):
    """Run English analysis in thread pool"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        thread_pool,
        analyze_english_input_eng_only,
        user_text
    )

# async def pre_generate_common_tts():
#     """Pre-generate common TTS responses for better performance"""
#     common_phrases = [
#         "No speech detected. Please try speaking again.",
#         "I didn't catch that. Could you please repeat?",
#         "Great! I'm listening.",
#         "Perfect! Your English is clear.",
#         "Please wait... Your audio is processing...",
#     ]
    
#     for phrase in common_phrases:
#         if phrase not in tts_cache:
#             try:
#                 audio = await synthesize_speech(phrase)
#                 tts_cache[phrase] = audio
#                 print(f"✅ Pre-generated TTS for: {phrase}")
#             except Exception as e:
#                 print(f"❌ Failed to pre-generate TTS for '{phrase}': {e}")

@router.websocket("/ws/english-only")
async def english_only_conversation(websocket: WebSocket):
    with tracer.start_as_current_span("english_only_session") as session_span:
        session_span.set_attribute("websocket.endpoint", "/ws/english-only")
        
        await websocket.accept()
        profiler = Profiler()
        
        # Pre-generate common TTS responses
        # await pre_generate_common_tts()

        try:
            while True:
                with tracer.start_as_current_span("receive_and_process_audio") as process_span:
                    # Step 1: Receive base64 audio as JSON
                    data = await websocket.receive_text()
                    profiler.mark("📥 Received audio JSON")
                    process_span.set_attribute("audio.received", True)

                    try:
                        with tracer.start_as_current_span("parse_json") as parse_span:
                            message = json.loads(data)
                            message_type = message.get("type")
                            parse_span.set_attribute("message.type", message_type or "audio_input")
                    except Exception as e:
                        parse_span.set_status(Status(StatusCode.ERROR, str(e)))
                        await safe_send_json(websocket, {
                            "response": "Invalid JSON format.",
                            "step": "error"
                        })
                        continue
                    
                    # Handle greeting message
                    if message_type == "greeting":
                        user_name = message.get("user_name", "there")
                        greeting_text = f"Hi {user_name}, I'm your AI English tutor. How can I help?"
                        
                        # Use cached TTS if available
                        if greeting_text in tts_cache:
                            greeting_audio = tts_cache[greeting_text]
                        else:
                            greeting_audio = await synthesize_speech_bytes(greeting_text)
                            tts_cache[greeting_text] = greeting_audio
                        
                        profiler.mark("👋 Greeting generated")
                        
                        await safe_send_json(websocket, {
                            "response": greeting_text,
                            "step": "greeting",
                            "user_name": user_name
                        })
                        await safe_send_bytes(websocket, greeting_audio)
                        continue
                    
                    # Handle prolonged pause message
                    if message_type == "prolonged_pause":
                        user_name = message.get("user_name", "there")
                        pause_text = f"Would you like to learn anything else, {user_name}?"
                        
                        # Use cached TTS if available
                        if pause_text in tts_cache:
                            pause_audio = tts_cache[pause_text]
                        else:
                            pause_audio = await synthesize_speech_bytes(pause_text)
                            tts_cache[pause_text] = pause_audio
                        
                        profiler.mark("⏸️ Pause prompt generated")
                        
                        await safe_send_json(websocket, {
                            "response": pause_text,
                            "step": "pause_detected",
                            "user_name": user_name
                        })
                        await safe_send_bytes(websocket, pause_audio)
                        continue
                    
                    # Handle user being silent after AI speaks
                    if message_type == "user_silent_after_ai":
                        user_name = message.get("user_name", "there")
                        # The user requested "Would you be there?". A more natural phrase might be "Are you still there?".
                        # For now, implementing as requested.
                        reminder_text = f"Would you be there, {user_name}?"
                        
                        if reminder_text in tts_cache:
                            reminder_audio = tts_cache[reminder_text]
                        else:
                            reminder_audio = await synthesize_speech_bytes(reminder_text)
                            tts_cache[reminder_text] = reminder_audio
                        
                        profiler.mark("⏰ User silent reminder generated")
                        
                        await safe_send_json(websocket, {
                            "response": reminder_text,
                            "step": "user_reminded",
                            "user_name": user_name
                        })
                        await safe_send_bytes(websocket, reminder_audio)
                        continue

                    # Handle no speech detected message
                    if message_type == "no_speech_detected":
                        user_name = message.get("user_name", "there")
                        no_speech_text = "No speech detected. Please try speaking again."
                        
                        # Use cached TTS if available
                        if no_speech_text in tts_cache:
                            no_speech_audio = tts_cache[no_speech_text]
                        else:
                            no_speech_audio = await synthesize_speech_bytes(no_speech_text)
                            tts_cache[no_speech_text] = no_speech_audio
                        
                        profiler.mark("🔇 No speech detected response generated")
                        
                        await safe_send_json(websocket, {
                            "response": no_speech_text,
                            "step": "no_speech_detected",
                            "user_name": user_name
                        })
                        await safe_send_bytes(websocket, no_speech_audio)
                        continue
                    
                    # Handle processing started message
                    if message_type == "processing_started":
                        user_name = message.get("user_name", "there")
                        processing_text = "Great! I'm listening."
                        
                        # Use cached TTS if available
                        if processing_text in tts_cache:
                            processing_audio = tts_cache[processing_text]
                        else:
                            processing_audio = await synthesize_speech_bytes(processing_text)
                            tts_cache[processing_text] = processing_audio
                        
                        profiler.mark("🔄 Processing started response generated")
                        
                        await safe_send_json(websocket, {
                            "response": processing_text,
                            "step": "processing_started",
                            "user_name": user_name
                        })
                        await safe_send_bytes(websocket, processing_audio)
                        continue
                    
                    # Handle regular audio input
                    audio_base64 = message.get("audio_base64")
                    user_name = message.get("user_name", "there")

                if not audio_base64:
                    await safe_send_json(websocket, {
                        "response": "No audio_base64 found.",
                        "step": "error"
                    })
                    continue

                # 🎯 REMOVED: No longer sending processing feedback from backend
                # Frontend will handle playing pre-generated audio file

                try:
                    with tracer.start_as_current_span("decode_audio") as decode_span:
                        # Move base64 decoding to thread pool for better performance
                        audio_bytes = await asyncio.get_event_loop().run_in_executor(
                            thread_pool,
                            base64.b64decode,
                            audio_base64
                        )
                        profiler.mark("🎙️ Audio decoded from base64")
                        decode_span.set_attribute("audio.bytes_length", len(audio_bytes))
                except Exception as e:
                    print("Error decoding audio:", e)
                    decode_span.set_status(Status(StatusCode.ERROR, str(e)))
                    await safe_send_json(websocket, {
                        "response": "Failed to decode audio.",
                        "step": "error"
                    })
                    continue

                # Use English-Only STT (no language detection needed)
                with tracer.start_as_current_span("stt_transcription") as stt_span:
                    transcription_result = await async_transcribe_audio_eng_only(audio_bytes)
                    transcribed_text = transcription_result["text"]
                    profiler.mark("📝 STT completed")
                    stt_span.set_attribute("stt.text_length", len(transcribed_text))
                    stt_span.set_attribute("stt.confidence", transcription_result.get("confidence", 0.0))

                if not transcribed_text.strip():
                    # STT returned empty text after processing started - send no speech detected response
                    print("🔇 STT returned empty text after processing started - sending no speech detected response")
                    
                    # Send no speech detected response with "I didn't catch that" message
                    no_speech_text = f"I didn't catch that. Could you please repeat, {user_name}?"
                    
                    # Use cached TTS if available
                    if no_speech_text in tts_cache:
                        no_speech_audio = tts_cache[no_speech_text]
                    else:
                        no_speech_audio = await synthesize_speech_bytes(no_speech_text)
                        tts_cache[no_speech_text] = no_speech_audio
                    
                    profiler.mark("🔇 No speech detected response generated")
                    
                    await safe_send_json(websocket, {
                        "response": no_speech_text,
                        "step": "no_speech_detected_after_processing",
                        "user_name": user_name
                    })

                    print("no speech detected has sended")
                    await safe_send_bytes(websocket, no_speech_audio)
                    continue

                # Process English input with new feedback analysis
                print(f"🔍 [ENGLISH_ONLY] Processing input: '{transcribed_text}'")
                
                # Analyze English input for accent and grammar issues
                with tracer.start_as_current_span("analyze_english_input") as analysis_span:
                    analysis_result = await async_analyze_english_input(transcribed_text)
                    profiler.mark("🔍 English analysis completed")
                    analysis_span.set_attribute("analysis.input_length", len(transcribed_text))
                    analysis_span.set_attribute("analysis.has_corrections", bool(analysis_result.get("corrections")))

                # Extract conversation data from analysis result
                conversation_text = analysis_result.get("conversation_text", f"Great! I understood: '{transcribed_text}'. Let's continue our conversation!")
                is_correct = analysis_result.get("is_correct", True)
                intent = analysis_result.get("intent", "general_conversation")
                should_continue = analysis_result.get("should_continue_conversation", True)

                # Use conversation_text for TTS (what the AI actually says out loud)
                tts_text = conversation_text
                
                print(f"🎯 [ENGLISH_ONLY] TTS Text: {tts_text}")
                print(f"🎯 [ENGLISH_ONLY] Analysis: correct={is_correct}, intent={intent}, continue={should_continue}")

                # Generate TTS for conversation_text (what the AI actually says)
                with tracer.start_as_current_span("synthesize_response_audio") as tts_span:
                    if tts_text in tts_cache:
                        response_audio = tts_cache[tts_text]
                    else:
                        response_audio = await synthesize_speech_bytes(tts_text)
                        tts_cache[tts_text] = response_audio
                    
                    profiler.mark("🔊 TTS response generated")
                    tts_span.set_attribute("tts.text_length", len(tts_text))
                    tts_span.set_attribute("tts.audio_bytes_length", len(response_audio))

                # Send enhanced response with analysis data
                with tracer.start_as_current_span("send_response") as send_span:
                    await safe_send_json(websocket, {
                        "response": conversation_text,
                        "conversation_text": conversation_text,
                        "step": "correction" if not is_correct else "conversation",
                        "original_text": transcribed_text,
                        "user_name": user_name,
                        "analysis": {
                            "is_correct": is_correct,
                            "intent": intent,
                            "should_continue_conversation": should_continue
                        }
                    })
                    await safe_send_bytes(websocket, response_audio)
                    send_span.set_attribute("response.sent", True)

                profiler.summary()
                
        except WebSocketDisconnect:
            print("Client disconnected")
            session_span.set_attribute("session.disconnected", True)
        except Exception as e:
            print(f"Unexpected error: {e}")
            session_span.set_status(Status(StatusCode.ERROR, str(e)))
        finally:
            # Clean up resources
            if http_client:
                await http_client.aclose() 