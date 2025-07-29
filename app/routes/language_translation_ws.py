"""
Language Translation AI Tutor WebSocket Handler

This module provides a ChatGPT-like voice mode experience for language learning:
- Personalized greetings with user's name
- Multi-language support (Urdu/English)
- Language detection and translation
- Teaching responses with corrections
- Natural conversation flow
- Prolonged pause detection (7+ seconds)
- Friendly, human-like tone

Features:
1. Greet user by name
2. Listen continuously to user input
3. Detect language (Urdu/English)
4. Translate and provide teaching responses
5. Stay in listening mode for next input
6. Handle prolonged silence with gentle prompts
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.translation import translate_urdu_to_english, translate_to_urdu
from app.services.tts import synthesize_speech_bytes, synthesize_speech
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
import openai
import requests
import tempfile
import os
import time
from langdetect import detect

router = APIRouter()

# Global thread pool for CPU-intensive tasks
thread_pool = ThreadPoolExecutor(max_workers=4)

# Cache for frequently used corrections and TTS
correction_cache = {}
tts_cache = {}

# Connection pool for HTTP clients
http_client = None

# === CONFIG ===
OPENAI_API_KEY = "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"
ELEVEN_API_KEY = "sk_4e27e104fea9895cd1b7c6fd64da1da48de599dfed693e9a"
ELEVEN_VOICE_ID = "EXAVITQu4vr4xnSDxMaL"

openai.api_key = OPENAI_API_KEY

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
async def async_transcribe_audio_language(audio_bytes: bytes):
    """Run Language Translation STT in thread pool to avoid blocking"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        thread_pool, 
        stt.transcribe_audio_bytes_language, 
        audio_bytes
    )

# Async wrapper for language detection
async def async_detect_language(text: str):
    """Run language detection in thread pool"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        thread_pool,
        detect,
        text
    )

# Async wrapper for teaching response generation
async def async_generate_teaching_response(text: str, lang: str):
    """Run teaching response generation in thread pool"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        thread_pool,
        generate_teaching_response,
        text,
        lang
    )

def generate_teaching_response(text: str, lang: str):
    """Generate teaching response based on detected language"""
    start = time.time()
    print("🧠 Sending prompt to GPT-4o...")

    # Generalized prompt logic
    if lang != "en":
        prompt = (
            f"The user said in a non-English language (likely '{lang}'): \"{text}\".\n"
            "Translate this to English and provide a clear, natural English sentence for communication. "
            "Also provide a brief teaching response explaining the translation and any cultural context if relevant."
        )
    else:
        prompt = (
            f"The user said in English: \"{text}\".\n"
            "Correct the grammar if needed and provide a polished English sentence for communication. "
            "Also provide a brief teaching response explaining any corrections made."
        )

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an expert language tutor helping users improve their English and Urdu communication skills."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )

    answer = response.choices[0].message.content
    print(f"📘 GPT Response:\n{answer}")

    end = time.time()
    print(f"⏱️ GPT Response Time: {end - start:.2f} seconds")

    return answer

@router.websocket("/ws/language-translation")
async def language_translation_conversation(websocket: WebSocket):
    await websocket.accept()
    profiler = Profiler()

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
                    greeting_text = f"Hi {user_name}, I'm your AI Language Translation Tutor. I can help you with both Urdu and English. How can I assist you today?"
                    
                    # Use cached TTS if available
                    if greeting_text in tts_cache:
                        greeting_audio = tts_cache[greeting_text]
                    else:
                        greeting_audio = await synthesize_speech(greeting_text)
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
                    pause_text = f"Would you like to learn anything else, {user_name}? I'm here to help with both Urdu and English."
                    
                    # Use cached TTS if available
                    if pause_text in tts_cache:
                        pause_audio = tts_cache[pause_text]
                    else:
                        pause_audio = await synthesize_speech(pause_text)
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
                    reminder_text = f"Are you still there, {user_name}? Feel free to speak in Urdu or English."
                    
                    if reminder_text in tts_cache:
                        reminder_audio = tts_cache[reminder_text]
                    else:
                        reminder_audio = await synthesize_speech(reminder_text)
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
                    no_speech_text = "No speech detected. Please try speaking again in Urdu or English."
                    
                    # Use cached TTS if available
                    if no_speech_text in tts_cache:
                        no_speech_audio = tts_cache[no_speech_text]
                    else:
                        no_speech_audio = await synthesize_speech(no_speech_text)
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
                    processing_text = "Great! I'm listening and processing your speech."
                    
                    # Use cached TTS if available
                    if processing_text in tts_cache:
                        processing_audio = tts_cache[processing_text]
                    else:
                        processing_audio = await synthesize_speech(processing_text)
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

            # 🎯 NEW: Send immediate processing feedback
            processing_text = "Please wait... Your audio is processing..."
            if processing_text in tts_cache:
                processing_audio = tts_cache[processing_text]
            else:
                processing_audio = await synthesize_speech(processing_text)
                tts_cache[processing_text] = processing_audio
            
            # Send processing started message immediately
            await safe_send_json(websocket, {
                "response": processing_text,
                "step": "processing_started",
                "user_name": user_name
            })
            await safe_send_bytes(websocket, processing_audio)
            profiler.mark("🔄 Processing feedback sent")

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

            # Use Language Translation STT
            transcription_result = await async_transcribe_audio_language(audio_bytes)
            transcribed_text = transcription_result["text"]
            profiler.mark("📝 STT completed")

            if not transcribed_text.strip():
                # STT returned empty text after processing started - send no speech detected response
                print("🔇 STT returned empty text after processing started - sending no speech detected response")
                
                # Send no speech detected response with "I didn't catch that" message including user's name
                no_speech_text = f"I didn't catch that. Could you please repeat, {user_name}? You can speak in Urdu or English."
                
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

            # Detect language
            detected_lang = await async_detect_language(transcribed_text)
            profiler.mark("🌐 Language detection completed")

            print(f"🔍 [LANGUAGE_TRANSLATION] Processing input: '{transcribed_text}' in language: {detected_lang}")
            
            # Generate teaching response based on detected language
            teaching_response = await async_generate_teaching_response(transcribed_text, detected_lang)
            profiler.mark("🧠 Teaching response generated")

            # Extract response components
            ai_response = teaching_response
            conversation_text = teaching_response
            
            # Use conversation_text for TTS (what the AI actually says out loud)
            tts_text = conversation_text
            
            print(f"🎯 [LANGUAGE_TRANSLATION] TTS Text (conversation_text): {tts_text}")
            print(f"📝 [LANGUAGE_TRANSLATION] AI Response (for display): {ai_response}")

            print(f"✅ [LANGUAGE_TRANSLATION] Analysis Results:")
            print(f"   - Detected Language: {detected_lang}")
            print(f"   - Original Text: {transcribed_text}")
            print(f"   - AI Response: {ai_response}")

            # Generate TTS for conversation_text (what the AI actually says)
            if tts_text in tts_cache:
                response_audio = tts_cache[tts_text]
            else:
                response_audio = await synthesize_speech(tts_text)
                tts_cache[tts_text] = response_audio
            
            profiler.mark("🔊 TTS response generated")

            # Send response
            await safe_send_json(websocket, {
                "response": ai_response,
                "conversation_text": conversation_text,  # What the AI actually says
                "step": "translation",
                "original_text": transcribed_text,
                "detected_language": detected_lang,
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