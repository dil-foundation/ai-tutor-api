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
from app.services.tts import synthesize_speech_bytes
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

router = APIRouter()

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

async def pre_generate_common_tts():
    """Pre-generate common TTS responses for better performance"""
    common_phrases = [
        "No speech detected. Please try speaking again.",
        "I didn't catch that. Could you please repeat?",
        "Great! I'm listening.",
        "Perfect! Your English is clear.",
    ]
    
    for phrase in common_phrases:
        if phrase not in tts_cache:
            try:
                audio = await synthesize_speech_bytes(phrase)
                tts_cache[phrase] = audio
                print(f"✅ Pre-generated TTS for: {phrase}")
            except Exception as e:
                print(f"❌ Failed to pre-generate TTS for '{phrase}': {e}")

@router.websocket("/ws/english-only")
async def english_only_conversation(websocket: WebSocket):
    await websocket.accept()
    profiler = Profiler()
    
    # Pre-generate common TTS responses
    await pre_generate_common_tts()

    try:
        while True:
            # Step 1: Receive base64 audio as JSON
            data = await websocket.receive_text()
            profiler.mark("📥 Received audio JSON")

            try:
                message = json.loads(data)
                message_type = message.get("type")
                
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
                
            except Exception:
                await safe_send_json(websocket, {
                    "response": "Invalid JSON format.",
                    "step": "error"
                })
                continue

            if not audio_base64:
                await safe_send_json(websocket, {
                    "response": "No audio_base64 found.",
                    "step": "error"
                })
                continue

            try:
                # Move base64 decoding to thread pool for better performance
                audio_bytes = await asyncio.get_event_loop().run_in_executor(
                    thread_pool,
                    base64.b64decode,
                    audio_base64
                )
                profiler.mark("🎙️ Audio decoded from base64")
            except Exception as e:
                print("Error decoding audio:", e)
                await safe_send_json(websocket, {
                    "response": "Failed to decode audio.",
                    "step": "error"
                })
                continue

            # Use English-Only STT (no language detection needed)
            transcription_result = await async_transcribe_audio_eng_only(audio_bytes)
            transcribed_text = transcription_result["text"]
            profiler.mark("📝 STT completed")

            if not transcribed_text.strip():
                await safe_send_json(websocket, {
                    "response": "No speech detected.",
                    "step": "no_speech"
                })
                continue

            # Process English input with new feedback analysis
            print(f"🔍 [ENGLISH_ONLY] Processing input: '{transcribed_text}'")
            
            # Analyze English input for accent and grammar issues
            analysis_result = await async_analyze_english_input(transcribed_text)
            profiler.mark("🔍 English analysis completed")

            # Extract analysis results
            has_accent_issues = analysis_result.get("has_accent_issues", False)
            has_grammar_issues = analysis_result.get("has_grammar_issues", False)
            corrected_text = analysis_result.get("corrected_text", transcribed_text)
            accent_feedback = analysis_result.get("accent_feedback", "")
            grammar_feedback = analysis_result.get("grammar_feedback", "")
            response_type = analysis_result.get("response_type", "perfect")
            ai_response = analysis_result.get("ai_response", f"Great! I understood: '{transcribed_text}'.")
            conversation_text = analysis_result.get("conversation_text", f"Great! I understood: '{transcribed_text}'. Your English is clear!")

            # Use conversation_text for TTS (what the AI actually says out loud)
            tts_text = conversation_text
            
            print(f"🎯 [ENGLISH_ONLY] TTS Text (conversation_text): {tts_text}")
            print(f"📝 [ENGLISH_ONLY] AI Response (for display): {ai_response}")

            print(f"✅ [ENGLISH_ONLY] Analysis Results:")
            print(f"   - Has Accent Issues: {has_accent_issues}")
            print(f"   - Has Grammar Issues: {has_grammar_issues}")
            print(f"   - Response Type: {response_type}")
            print(f"   - AI Response: {ai_response}")

            # Generate TTS for conversation_text (what the AI actually says)
            if tts_text in tts_cache:
                response_audio = tts_cache[tts_text]
            else:
                response_audio = await synthesize_speech_bytes(tts_text)
                tts_cache[tts_text] = response_audio
            
            profiler.mark("🔊 TTS response generated")

            # Send response
            await safe_send_json(websocket, {
                "response": ai_response,
                "conversation_text": conversation_text,  # What the AI actually says
                "step": "correction",
                "original_text": transcribed_text,
                "corrected_text": corrected_text,
                "has_accent_issues": has_accent_issues,
                "has_grammar_issues": has_grammar_issues,
                "accent_feedback": accent_feedback,
                "grammar_feedback": grammar_feedback,
                "response_type": response_type,
                "user_name": user_name
            })
            await safe_send_bytes(websocket, response_audio)

            profiler.summary()
            
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        # Clean up resources
        if http_client:
            await http_client.aclose() 