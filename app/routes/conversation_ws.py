from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.translation import translate_urdu_to_english
from app.services.tts import synthesize_speech_bytes
from app.services.feedback import evaluate_response
from app.services import stt 
import base64
import json

router = APIRouter()

@router.websocket("/ws/learn")
async def learn_conversation(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:

            # Step 1: Receive user input (text or base64 audio string)
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                audio_base64 = message.get("audio_base64")
                filename = message.get("filename", "audio.wav")
            except Exception:
                await websocket.send_json({
                    "response": "Invalid JSON format.",
                    "step": "error"
                })
                return

            if audio_base64:
                try:
                    audio_bytes = base64.b64decode(audio_base64)

                    # Transcribe directly as English
                    transcribed_text = stt.transcribe_audio_bytes(audio_bytes, language_code="en-US")
                    print("🟡 Transcribed (English):", transcribed_text)

                    if not transcribed_text.strip():
                        print("🟡 No speech detected")
                        await websocket.send_json({
                            "response": "No speech detected. Please try again.",
                            "step": "no_speech"
                        })
                        continue

                    translated = transcribed_text.strip()

                    ai_text = f"The English sentence is \"{translated}\". Can you repeat after me?"

                    await websocket.send_json({
                        "response": ai_text,
                        "step": "repeat_prompt"
                    })

                    audio_response = await synthesize_speech_bytes(ai_text)
                    await websocket.send_bytes(audio_response)

                    user_repeat_msg = await websocket.receive_text()

                    try:
                        user_repeat_data = json.loads(user_repeat_msg)
                        user_audio_base64 = user_repeat_data.get("audio_base64")

                        if user_audio_base64:
                            user_audio_bytes = base64.b64decode(user_audio_base64)
                            user_transcription = stt.transcribe_audio_bytes(user_audio_bytes, language_code="en-US")
                            print("🔵 User Transcription:", user_transcription)

                            print("translated text: ",translated)

                            feedback = evaluate_response(expected=translated, actual=user_transcription)
                            
                            print("This is the feedback: ",feedback)
                            
                            if feedback["correct"]:
                                await websocket.send_json({
                                    "response": "Nice! Let's try another sentence.",
                                    "step": "await_next"
                                })
                            else:
                                await websocket.send_json({
                                    "response": f"Try again. Please say: '{translated}'",
                                    "step": "retry"
                                })
                        else:
                            await websocket.send_json({
                                "response": "No valid audio found in user response.",
                                "step": "error"
                            })

                    except Exception as e:
                        print("❌ Error processing user repeat audio:", str(e))
                        await websocket.send_json({
                            "response": "Failed to process your repeat audio.",
                            "step": "error"
                        })


                except Exception as e:
                    print("❌ Error in audio decoding/transcription:", str(e))
                    await websocket.send_json({
                        "response": "Failed to process the audio.",
                        "step": "error"
                    })
            else:
                await websocket.send_json({
                    "response": "No valid audio_base64 found.",
                    "step": "error"
                })

    except WebSocketDisconnect:
        print("Client disconnected")
