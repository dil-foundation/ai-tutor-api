from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.translation import translate_urdu_to_english, translate_to_urdu
from app.services.tts import synthesize_speech_bytes
from app.services.feedback import evaluate_response
from app.services import stt
from app.utils.profiler import Profiler
import json
import base64

router = APIRouter()

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

@router.websocket("/ws/learn")
async def learn_conversation(websocket: WebSocket):
    await websocket.accept()
    profiler = Profiler()

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
                audio_bytes = base64.b64decode(audio_base64)
                profiler.mark("🎙️ Audio decoded from base64")
            except Exception as e:
                print("Error decoding audio:", e)
                await safe_send_json(websocket, {
                    "response": "Failed to decode audio.",
                    "step": "error"
                })
                continue

            # STT
            transcription_result = stt.transcribe_audio_bytes_eng(audio_bytes)
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
                feedback_audio = await synthesize_speech_bytes(english_feedback)
                profiler.mark("⚠️ English input handled")

                await safe_send_json(websocket, {
                    "response": english_feedback,
                    "step": "english_input_edge_case",
                    "detected_language": detected_language
                })
                await safe_send_bytes(websocket, feedback_audio)
                continue

            # Translate
            transcribed_urdu = translate_to_urdu(transcribed_text)
            profiler.mark("🔄 Translated to Urdu")

            translated_en = translate_urdu_to_english(transcribed_text.strip())
            profiler.mark("🌐 Translated to English")

            you_said_text = f"آپ نے کہا: {transcribed_urdu} اب میرے بعد دہرائیں۔"
            you_said_audio = await synthesize_speech_bytes(you_said_text)
            profiler.mark("🔊 TTS you_said completed")

            words = translated_en.split()

            await safe_send_json(websocket, {
                "response": you_said_text,
                "step": "you_said_audio",
                "english_sentence": translated_en,
                "urdu_sentence": transcribed_urdu,
                "words": words
            })
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

            # Full sentence
            urdu_prompt = "\u200Fاب مکمل جملہ دہرائیں: "
            english_text = f"\u200E{translated_en}."
            full_sentence_audio = await synthesize_speech_bytes(f"اب مکمل جملہ دہرائیں: {translated_en}.")
            profiler.mark("🔊 TTS full sentence completed")

            await safe_send_json(websocket, {
                "response": f"{urdu_prompt} {english_text}",
                "step": "full_sentence_audio",
                "english_sentence": translated_en
            })
            await safe_send_bytes(websocket, full_sentence_audio)

            # Feedback loop
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

                user_audio_bytes = base64.b64decode(user_audio_base64)
                user_transcription = stt.transcribe_audio_bytes(user_audio_bytes, language_code="en-US")
                profiler.mark("🎤 User repeat STT completed")

                feedback = evaluate_response(expected=translated_en, actual=user_transcription)
                profiler.mark("🔍 Feedback evaluation completed")

                if feedback["is_correct"]:
                    feedback_text = feedback["feedback_text"]
                    feedback_audio = await synthesize_speech_bytes(feedback_text)
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
                feedback_audio = await synthesize_speech_bytes(feedback_text)
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

                # Full sentence again
                await safe_send_json(websocket, {
                    "response": f"{urdu_prompt} {english_text}",
                    "step": "full_sentence_audio",
                    "english_sentence": translated_en
                })
                full_sentence_audio = await synthesize_speech_bytes(f"اب مکمل جملہ دہرائیں: {translated_en}.")
                await safe_send_bytes(websocket, full_sentence_audio)

            profiler.summary()

    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"Unexpected error: {e}")
