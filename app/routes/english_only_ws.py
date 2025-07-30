"""
English-Only AI Tutor WebSocket Handler

This module provides a ChatGPT-like voice mode experience for English learning:
- Personalized greetings with user's name
- Thick accent detection and correction
- Broken English detection and correction
- Natural conversation flow
- Prolonged pause detection (7+ seconds)
- Friendly, human-like tone
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.tts import synthesize_speech_bytes
from app.services.feedback import analyze_english_input_eng_only
from app.services import stt
from app.utils.profiler import Profiler
import json
import base64
import asyncio
from concurrent.futures import ThreadPoolExecutor
import httpx

router = APIRouter()

# Global thread pool for CPU-intensive tasks
thread_pool = ThreadPoolExecutor(max_workers=10)

# Cache for frequently used corrections and TTS
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

# Async wrapper for English feedback analysis, now aware of conversation stage and topic
async def async_analyze_english_input(user_text: str, stage: str, topic: str = None):
    """Run English analysis in thread pool"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        thread_pool,
        analyze_english_input_eng_only,
        user_text,
        stage,
        topic
    )

@router.websocket("/ws/english-only")
async def english_only_conversation(websocket: WebSocket):
    await websocket.accept()
    profiler = Profiler()
    
    # --- State Management ---
    conversation_stage = "greeting"  # Initial conversation stage
    current_topic = None # To store the topic for topic-based discussion

    try:
        while True:
            # Step 1: Receive base64 audio as JSON
            data = await websocket.receive_text()
            profiler.mark("📥 Received audio JSON")

            try:
                message = json.loads(data)
                message_type = message.get("type")
            except Exception as e:
                await safe_send_json(websocket, {
                    "response": "Invalid JSON format.",
                    "step": "error"
                })
                continue
            
            # Handle greeting message
            if message_type == "greeting":
                conversation_stage = "intent_detection"  # Move to intent detection after greeting

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
            
            # --- Keep existing message type handlers from the old file ---
            if message_type == "prolonged_pause":
                user_name = message.get("user_name", "there")
                pause_text = f"Would you like to learn anything else, {user_name}?"
                if pause_text not in tts_cache:
                    tts_cache[pause_text] = await synthesize_speech_bytes(pause_text)
                await safe_send_json(websocket, {"response": pause_text, "step": "pause_detected", "user_name": user_name})
                await safe_send_bytes(websocket, tts_cache[pause_text])
                continue

            if message_type == "user_silent_after_ai":
                user_name = message.get("user_name", "there")
                reminder_text = f"Are you still there, {user_name}?"
                if reminder_text not in tts_cache:
                    tts_cache[reminder_text] = await synthesize_speech_bytes(reminder_text)
                await safe_send_json(websocket, {"response": reminder_text, "step": "user_reminded", "user_name": user_name})
                await safe_send_bytes(websocket, tts_cache[reminder_text])
                continue

            if message_type == "no_speech_detected":
                no_speech_text = "No speech detected. Please try speaking again."
                if no_speech_text not in tts_cache:
                    tts_cache[no_speech_text] = await synthesize_speech_bytes(no_speech_text)
                await safe_send_json(websocket, {"response": no_speech_text, "step": "no_speech_detected"})
                await safe_send_bytes(websocket, tts_cache[no_speech_text])
                continue

            if message_type == "processing_started":
                processing_text = "Great! I'm listening."
                if processing_text not in tts_cache:
                    tts_cache[processing_text] = await synthesize_speech_bytes(processing_text)
                await safe_send_json(websocket, {"response": processing_text, "step": "processing_started"})
                await safe_send_bytes(websocket, tts_cache[processing_text])
                continue

            # --- Main Audio Processing Block ---
            audio_base64 = message.get("audio_base64")
            user_name = message.get("user_name", "there")

            if not audio_base64:
                continue

            audio_bytes = await asyncio.get_event_loop().run_in_executor(thread_pool, base64.b64decode, audio_base64)
            profiler.mark("🎙️ Audio decoded")

            transcription_result = await async_transcribe_audio_eng_only(audio_bytes)
            transcribed_text = transcription_result["text"]
            profiler.mark("📝 STT completed")

            if not transcribed_text.strip():
                no_speech_text = f"I didn't catch that. Could you please repeat, {user_name}?"
                if no_speech_text not in tts_cache:
                    tts_cache[no_speech_text] = await synthesize_speech_bytes(no_speech_text)
                await safe_send_json(websocket, {"response": no_speech_text, "step": "no_speech_detected_after_processing"})
                await safe_send_bytes(websocket, tts_cache[no_speech_text])
                continue
            
            print(f"🔍 [ENGLISH_ONLY] Processing: '{transcribed_text}' at stage: {conversation_stage}")

            # Analyze English input using the new stage-aware logic
            analysis_result = await async_analyze_english_input(
                user_text=transcribed_text,
                stage=conversation_stage,
                topic=current_topic
            )
            profiler.mark("🧠 AI analysis completed")

            # Update state based on AI's response
            conversation_stage = analysis_result.get("next_stage", "main_conversation")
            extracted_topic = analysis_result.get("extracted_topic")
            if extracted_topic:
                current_topic = extracted_topic
                print(f"✅ New topic set: {current_topic}")

            # Get the AI's response text
            conversation_text = analysis_result.get("conversation_text", "Let's continue.")
            print(f"🎯 [ENGLISH_ONLY] AI Response: {conversation_text}")

            # Generate TTS for the AI's response
            if conversation_text in tts_cache:
                response_audio = tts_cache[conversation_text]
            else:
                response_audio = await synthesize_speech_bytes(conversation_text)
                tts_cache[conversation_text] = response_audio
            profiler.mark("🔊 TTS response generated")

            # Send back the response, adapting to the old JSON structure but using the new stage logic
            await safe_send_json(websocket, {
                "response": conversation_text,
                "conversation_text": conversation_text,
                "step": conversation_stage,  # Use the new stage as the "step"
                "original_text": transcribed_text,
                "user_name": user_name,
                "analysis": { # Provide a simplified analysis object
                    "next_stage": conversation_stage,
                    "current_topic": current_topic
                }
            })
            await safe_send_bytes(websocket, response_audio)

            profiler.summary()
            
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"Unexpected error in WebSocket: {e}")
    finally:
        # The thread_pool is a global resource for the app, so we don't shut it down here.
        # It will be cleaned up when the application itself terminates.
        print("WebSocket for a client closed.")
