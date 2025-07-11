from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.translation import translate_urdu_to_english, translate_to_urdu
from app.services.tts import synthesize_speech_bytes
from app.services.feedback import evaluate_response
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

# Cache for frequently used translations and TTS
translation_cache = {}
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

# Cached translation function
@lru_cache(maxsize=1000)
def cached_translate_urdu_to_english(text: str) -> str:
    """Cached version of translation to avoid repeated API calls"""
    return translate_urdu_to_english(text)

@lru_cache(maxsize=1000)
def cached_translate_to_urdu(text: str) -> str:
    """Cached version of translation to avoid repeated API calls"""
    return translate_to_urdu(text)

# Async wrapper for CPU-intensive STT
async def async_transcribe_audio(audio_bytes: bytes):
    """Run STT in thread pool to avoid blocking"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        thread_pool, 
        stt.transcribe_audio_bytes_eng, 
        audio_bytes
    )

# Async wrapper for translation
async def async_translate_urdu_to_english(text: str):
    """Run translation in thread pool"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        thread_pool,
        cached_translate_urdu_to_english,
        text
    )

async def async_translate_to_urdu(text: str):
    """Run translation in thread pool"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        thread_pool,
        cached_translate_to_urdu,
        text
    )

# Pre-generate common TTS responses
async def pre_generate_common_tts():
    """Pre-generate common TTS responses for faster response"""
    common_texts = [
        "Great job speaking English! However, please say the Urdu sentence to proceed.",
        "No speech detected.",
        "Invalid JSON format.",
        "No audio_base64 found.",
        "Failed to decode audio.",
        "No valid audio found in user response."
    ]
    
    tts_tasks = []
    for text in common_texts:
        task = synthesize_speech_bytes(text)
        tts_tasks.append(task)
    
    results = await asyncio.gather(*tts_tasks, return_exceptions=True)
    
    for text, result in zip(common_texts, results):
        if isinstance(result, bytes):
            tts_cache[text] = result

# Optimized conversation handler
@router.websocket("/ws/learn")
async def learn_conversation(websocket: WebSocket):
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
                audio_base64 = message.get("audio_base64")
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

            # Parallel STT processing
            transcription_task = async_transcribe_audio(audio_bytes)
            transcription_result = await transcription_task
            transcribed_text = transcription_result["text"]
            detected_language = transcription_result["language_code"]
            is_english = transcription_result["is_english"]
            profiler.mark("📝 STT completed")

            if not transcribed_text.strip():
                await safe_send_json(websocket, {
                    "response": "No speech detected.",
                    "step": "no_speech"
                })
                continue

            if is_english:
                english_feedback = "Great job speaking English! However, please say the Urdu sentence to proceed."
                
                # Use cached TTS if available
                if english_feedback in tts_cache:
                    feedback_audio = tts_cache[english_feedback]
                else:
                    feedback_audio = await synthesize_speech_bytes(english_feedback)
                    tts_cache[english_feedback] = feedback_audio
                
                profiler.mark("⚠️ English input handled")

                await safe_send_json(websocket, {
                    "response": english_feedback,
                    "step": "english_input_edge_case",
                    "detected_language": detected_language
                })
                await safe_send_bytes(websocket, feedback_audio)
                continue

            # Parallel translation processing
            urdu_translation_task = async_translate_to_urdu(transcribed_text)
            english_translation_task = async_translate_urdu_to_english(transcribed_text.strip())
            
            # Wait for both translations to complete
            transcribed_urdu, translated_en = await asyncio.gather(
                urdu_translation_task, 
                english_translation_task
            )
            profiler.mark("🔄 Translations completed")

            you_said_text = f"آپ نے کہا: {transcribed_urdu} اب میرے بعد دہرائیں۔"
            
            # Generate TTS in parallel with sending JSON
            tts_task = synthesize_speech_bytes(you_said_text)
            
            words = translated_en.split()

            # Send JSON immediately
            await safe_send_json(websocket, {
                "response": you_said_text,
                "step": "you_said_audio",
                "english_sentence": translated_en,
                "urdu_sentence": transcribed_urdu,
                "words": words
            })
            
            # Wait for TTS and send audio
            you_said_audio = await tts_task
            profiler.mark("🔊 TTS you_said completed")
            await safe_send_bytes(websocket, you_said_audio)

            # Wait for "you_said_complete"
            while True:
                next_msg = await websocket.receive_text()
                if json.loads(next_msg).get("type") == "you_said_complete":
                    break
            profiler.mark("✅ Frontend played you_said")

            # Send repeat prompt
            ai_text = f"The English sentence is \"{translated_en}\". Can you repeat after me?"
            await safe_send_json(websocket, {
                "response": ai_text,
                "step": "repeat_prompt",
                "english_sentence": translated_en,
                "urdu_sentence": transcribed_urdu,
                "words": words
            })

            # Wait for word_by_word_complete
            while True:
                next_msg = await websocket.receive_text()
                if json.loads(next_msg).get("type") == "word_by_word_complete":
                    break
            profiler.mark("✅ Word-by-word completed")

            # Full sentence - pre-generate TTS
            urdu_prompt = "\u200Fاب مکمل جملہ دہرائیں: "
            english_text = f"\u200E{translated_en}."
            full_sentence_text = f"اب مکمل جملہ دہرائیں: {translated_en}."
            
            # Generate TTS in parallel
            full_sentence_audio_task = synthesize_speech_bytes(full_sentence_text)
            
            await safe_send_json(websocket, {
                "response": f"{urdu_prompt} {english_text}",
                "step": "full_sentence_audio",
                "english_sentence": translated_en
            })
            
            full_sentence_audio = await full_sentence_audio_task
            profiler.mark("🔊 TTS full sentence completed")
            await safe_send_bytes(websocket, full_sentence_audio)

            # Optimized feedback loop
            while True:
                user_repeat_msg = await websocket.receive_text()
                user_repeat_data = json.loads(user_repeat_msg)
                user_audio_base64 = user_repeat_data.get("audio_base64")

                if not user_audio_base64:
                    await safe_send_json(websocket, {
                        "response": "No valid audio found in user response.",
                        "step": "error"
                    })
                    continue

                # Move base64 decoding to thread pool for better performance
                user_audio_bytes = await asyncio.get_event_loop().run_in_executor(
                    thread_pool,
                    base64.b64decode,
                    user_audio_base64
                )
                
                # Parallel STT and feedback evaluation
                user_transcription = await asyncio.get_event_loop().run_in_executor(
                    thread_pool,
                    stt.transcribe_audio_bytes,
                    user_audio_bytes,
                    "en-US"
                )
                profiler.mark("🎤 User repeat STT completed")

                # Run feedback evaluation in thread pool
                feedback = await asyncio.get_event_loop().run_in_executor(
                    thread_pool,
                    evaluate_response,
                    translated_en,
                    user_transcription
                )
                profiler.mark("🔍 Feedback evaluation completed")

                if feedback["is_correct"]:
                    feedback_text = feedback["feedback_text"]
                    
                    # Use cached TTS if available
                    if feedback_text in tts_cache:
                        feedback_audio = tts_cache[feedback_text]
                    else:
                        feedback_audio = await synthesize_speech_bytes(feedback_text)
                        tts_cache[feedback_text] = feedback_audio
                    
                    profiler.mark("🏆 Feedback (correct) TTS completed")

                    await safe_send_json(websocket, {
                        "response": feedback_text,
                        "step": "await_next",
                        "is_true": True
                    })
                    await safe_send_bytes(websocket, feedback_audio)
                    break

                # if not correct:
                feedback_text = feedback["feedback_text"]
                
                # Use cached TTS if available
                if feedback_text in tts_cache:
                    feedback_audio = tts_cache[feedback_text]
                else:
                    feedback_audio = await synthesize_speech_bytes(feedback_text)
                    tts_cache[feedback_text] = feedback_audio
                
                profiler.mark("🔁 Feedback (retry) TTS completed")

                await safe_send_json(websocket, {
                    "response": feedback_text,
                    "step": "feedback_step",
                    "is_true": False
                })
                await safe_send_bytes(websocket, feedback_audio)

                # Wait for "feedback_complete"
                while True:
                    next_msg = await websocket.receive_text()
                    if json.loads(next_msg).get("type") == "feedback_complete":
                        break

                # Word-by-word again
                await safe_send_json(websocket, {
                    "response": f"Let's practice word-by-word: {translated_en}",
                    "step": "word_by_word",
                    "english_sentence": translated_en,
                    "urdu_sentence": transcribed_urdu,
                    "words": words
                })

                while True:
                    next_msg = await websocket.receive_text()
                    if json.loads(next_msg).get("type") == "word_by_word_complete":
                        break

                # Full sentence again - use cached TTS if available
                full_sentence_text = f"اب مکمل جملہ دہرائیں: {translated_en}."
                
                if full_sentence_text in tts_cache:
                    full_sentence_audio = tts_cache[full_sentence_text]
                else:
                    full_sentence_audio = await synthesize_speech_bytes(full_sentence_text)
                    tts_cache[full_sentence_text] = full_sentence_audio
                
                await safe_send_json(websocket, {
                    "response": f"{urdu_prompt} {english_text}",
                    "step": "full_sentence_audio",
                    "english_sentence": translated_en
                })
                await safe_send_bytes(websocket, full_sentence_audio)

            profiler.summary()

    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        # Clean up resources
        if http_client:
            await http_client.aclose()
