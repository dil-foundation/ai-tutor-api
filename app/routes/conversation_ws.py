# from fastapi import APIRouter, WebSocket, WebSocketDisconnect
# from app.services.translation import translate_urdu_to_english
# from app.services.tts import synthesize_speech_bytes
# from app.services.tts import synthesize_speech
# from app.services.feedback import evaluate_response
# from app.services import stt 
# import base64
# import json
# from app.services.translation import translate_urdu_to_english


# router = APIRouter()

# @router.websocket("/ws/learn")
# async def learn_conversation(websocket: WebSocket):
#     await websocket.accept()
#     try:
#         while True:
#             # Step 1: Receive user input (text or base64 audio string)
#             data = await websocket.receive_text()

#             try:
#                 message = json.loads(data)
#                 audio_base64 = message.get("audio_base64")
#                 filename = message.get("filename", "audio.wav")
#             except Exception:
#                 await websocket.send_json({
#                     "response": "Invalid JSON format.",
#                     "step": "error"
#                 })
#                 return

#             if audio_base64:
#                 try:
#                     audio_bytes = base64.b64decode(audio_base64)

#                     # Transcribe directly as English
#                     # transcribed_text = stt.transcribe_audio_bytes(audio_bytes, language_code="en-US")

                    
#                     # Transcribe directly as English
#                     transcribed_text = stt.transcribe_audio_bytes(audio_bytes, language_code="ur-PK")


                    
#                     print("🟡 Transcribed (English):", transcribed_text)

#                     if not transcribed_text.strip():
#                         print("🟡 No speech detected")
#                         await websocket.send_json({
#                             "response": "No speech detected. Please try again.",
#                             "step": "no_speech"
#                         })
#                         continue

#                     translated = translate_urdu_to_english(transcribed_text.strip())

#                     ai_text = f"The English sentence is \"{translated}\". Can you repeat after me?"

#                     translated_ur = transcribed_text.strip()  # Urdu the user said
#                     translated_en = translate_urdu_to_english(translated_ur)  # English

#                     words = translated_en.split()  # ["The", "weather", "is", "nice", "today."]

#                     await websocket.send_json({
#                         "response": ai_text,
#                         "step": "repeat_prompt",
#                         "english_sentence": translated_en,
#                         "urdu_sentence": translated_ur,
#                         "words": words
#                     })

#                     audio_response = await synthesize_speech(ai_text)
#                     await websocket.send_bytes(audio_response)

#                     # Start the feedback loop - keep trying until user gets it right
#                     while True:
#                         user_repeat_msg = await websocket.receive_text()

#                         try:
#                             user_repeat_data = json.loads(user_repeat_msg)
#                             user_audio_base64 = user_repeat_data.get("audio_base64")

#                             if user_audio_base64:
#                                 user_audio_bytes = base64.b64decode(user_audio_base64)
#                                 user_transcription = stt.transcribe_audio_bytes(user_audio_bytes, language_code="en-US")
#                                 print("🔵 User Transcription:", user_transcription)

#                                 print("translated text: ", translated)

#                                 feedback = evaluate_response(expected=translated, actual=user_transcription)
                                
#                                 print("This is the feedback: ", feedback)
                                
#                                 if feedback["is_correct"]:
#                                     # User got it right - send feedback text and audio, then move to next sentence
#                                     feedback_text = feedback["feedback_text"]
#                                     await websocket.send_json({
#                                         "response": feedback_text,
#                                         "step": "await_next",
#                                         "is_true": True
#                                     })
                                    
#                                     # Send the feedback audio
#                                     feedback_audio = await synthesize_speech(feedback_text)
#                                     await websocket.send_bytes(feedback_audio)
                                    
#                                     # Break out of the feedback loop to get next sentence
#                                     break
#                                 else:
#                                     # User got it wrong - provide feedback and try again
#                                     feedback_text = feedback["feedback_text"]
#                                     await websocket.send_json({
#                                         "response": feedback_text,
#                                         "step": "feedback_step",
#                                         "is_true": False
#                                     })
                                    
#                                     feedback_audio = await synthesize_speech(feedback_text)
#                                     await websocket.send_bytes(feedback_audio)
                                    
#                                     # Continue the loop - wait for user to try again
#                                     # The frontend will send another audio after feedback audio finishes
#                                     continue

#                             else:
#                                 await websocket.send_json({
#                                     "response": "No valid audio found in user response.",
#                                     "step": "error"
#                                 })
#                                 break

#                         except Exception as e:
#                             print("❌ Error processing user repeat audio:", str(e))
#                             await websocket.send_json({
#                                 "response": "Failed to process your repeat audio.",
#                                 "step": "error"
#                             })
#                             break

#                 except Exception as e:
#                     print("❌ Error in audio decoding/transcription:", str(e))
#                     await websocket.send_json({
#                         "response": "Failed to process the audio.",
#                         "step": "error"
#                     })
#             else:
#                 await websocket.send_json({
#                     "response": "No valid audio_base64 found.",
#                     "step": "error"
#                 })

#     except WebSocketDisconnect:
#         print("Client disconnected") 
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.translation import translate_urdu_to_english
from app.services.tts import synthesize_speech_bytes
from app.services.tts import synthesize_speech
from app.services.feedback import evaluate_response
from app.services import stt 
import base64
import json
from app.services.translation import translate_urdu_to_english


router = APIRouter()

async def safe_send_json(websocket: WebSocket, data: dict):
    """Safely send JSON data to WebSocket with error handling"""
    try:
        await websocket.send_json(data)
    except Exception as e:
        print(f"Failed to send JSON message: {e}")
        raise

async def safe_send_bytes(websocket: WebSocket, data: bytes):
    """Safely send binary data to WebSocket with error handling"""
    try:
        await websocket.send_bytes(data)
    except Exception as e:
        print(f"Failed to send binary data: {e}")
        raise

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
                # Don't return, just continue to next iteration
                await safe_send_json(websocket, {
                    "response": "Invalid JSON format.",
                    "step": "error"
                })
                continue

            if audio_base64:
                try:
                    audio_bytes = base64.b64decode(audio_base64)

                    # Transcribe directly as English
                    # transcribed_text = stt.transcribe_audio_bytes(audio_bytes, language_code="en-US")

                    
                    # Transcribe directly as English
                    transcribed_text = stt.transcribe_audio_bytes(audio_bytes, language_code="ur-PK")


                    
                    print("🟡 Transcribed (English):", transcribed_text)

                    if not transcribed_text.strip():
                        print("🟡 No speech detected")
                        await safe_send_json(websocket, {
                            "response": "No speech detected. Please try again.",
                            "step": "no_speech"
                        })
                        continue

                    translated = translate_urdu_to_english(transcribed_text.strip())

                    translated_ur = transcribed_text.strip()  # Urdu the user said
                    translated_en = translate_urdu_to_english(translated_ur)  # English

                    you_said_text = f"آپ نے کہا: {translated_ur} اب میرے بعد دہرائیں۔"
                    
                    you_said_audio = await synthesize_speech_bytes(you_said_text)

                    ai_text = f"The English sentence is \"{translated}\". Can you repeat after me?"
                    
                    words = translated_en.split()  # ["The", "weather", "is", "nice", "today."]
                   
                    # First send the "you said" audio
                    await safe_send_json(websocket, {
                        "response": you_said_text,
                        "step": "you_said_audio",
                        "english_sentence": translated_en,
                        "urdu_sentence": translated_ur,
                        "words": words
                    })

                    # Send the "you said" audio
                    await safe_send_bytes(websocket, you_said_audio)

                    # Wait for frontend to finish playing "you said" audio
                    while True:
                        next_msg = await websocket.receive_text()
                        try:
                            next_data = json.loads(next_msg)
                            if next_data.get("type") == "you_said_complete":
                                break
                        except Exception:
                            continue

                    # Now send the repeat_prompt step
                    await safe_send_json(websocket, {
                        "response": ai_text,
                        "step": "repeat_prompt",
                        "english_sentence": translated_en,
                        "urdu_sentence": translated_ur,
                        "words": words
                    })

                    # # Wait a bit for word-by-word to complete, then send full sentence audio
                    # import asyncio
                    # await asyncio.sleep(25)  # Wait 5 seconds for word-by-word to complete

                    # Wait for frontend signal to continue
                    while True:
                        next_msg = await websocket.receive_text()
                        try:
                            next_data = json.loads(next_msg)
                            if next_data.get("type") == "word_by_word_complete":
                                break
                        except Exception:
                            continue
                    # Now send full sentence audio...
                    
                    # Send full sentence audios
                    await safe_send_json(websocket, {
                        # "response": f"Now repeat the full sentence: {translated_en}",
                        "response": f"اب مکمل جملہ دہرائیں: {translated_en}.",
                        "step": "full_sentence_audio",
                        "english_sentence": translated_en,
                    })
                    
                    # full_sentence_audio = await synthesize_speech_bytes(f"Now repeat the full sentence: {translated_en}")
                    
                    full_sentence_audio = await synthesize_speech_bytes(f"اب مکمل جملہ دہرائیں: {translated_en}.")
                    await safe_send_bytes(websocket, full_sentence_audio)

                    # Start the feedback loop - keep trying until user gets it right
                    while True:
                        user_repeat_msg = await websocket.receive_text()

                        try:
                            user_repeat_data = json.loads(user_repeat_msg)
                            user_audio_base64 = user_repeat_data.get("audio_base64")

                            if user_audio_base64:
                                user_audio_bytes = base64.b64decode(user_audio_base64)
                                user_transcription = stt.transcribe_audio_bytes(user_audio_bytes, language_code="en-US")
                                print("🔵 User Transcription:", user_transcription)

                                print("translated text: ", translated)

                                feedback = evaluate_response(expected=translated, actual=user_transcription)
                                
                                print("This is the feedback: ", feedback)
                                
                                if feedback["is_correct"]:
                                    # User got it right - send feedback text and audio, then move to next sentence
                                    feedback_text = feedback["feedback_text"]
                                    await safe_send_json(websocket, {
                                        "response": feedback_text,
                                        "step": "await_next",
                                        "is_true": True
                                    })
                                    
                                    # Send the feedback audio
                                    feedback_audio = await synthesize_speech_bytes(feedback_text)
                                    await safe_send_bytes(websocket, feedback_audio)
                                    
                                    # Break out of the feedback loop to get next sentence
                                    break
                                else:
                                    # User got it wrong - provide feedback and try again
                                    feedback_text = feedback["feedback_text"]
                                    await safe_send_json(websocket, {
                                        "response": feedback_text,
                                        "step": "feedback_step",
                                        "is_true": False
                                    })
                                    
                                    feedback_audio = await synthesize_speech_bytes(feedback_text)
                                    await safe_send_bytes(websocket, feedback_audio)
                                    
                                    # Continue the loop - wait for user to try again
                                    # The frontend will send another audio after feedback audio finishes
                                    continue

                            else:
                                await safe_send_json(websocket, {
                                    "response": "No valid audio found in user response.",
                                    "step": "error"
                                })
                                # Don't break, continue to next iteration
                                continue

                        except Exception as e:
                            print("❌ Error processing user repeat audio:", str(e))
                            await safe_send_json(websocket, {
                                "response": "Failed to process your repeat audio.",
                                "step": "error"
                            })
                            # Don't break, continue to next iteration
                            continue

                except Exception as e:
                    print("❌ Error in audio decoding/transcription:", str(e))
                    await safe_send_json(websocket, {
                        "response": "Failed to process the audio.",
                        "step": "error"
                    })
                    # Don't break, continue to next iteration
                    continue
            else:
                await safe_send_json(websocket, {
                    "response": "No valid audio_base64 found.",
                    "step": "error"
                })
                # Don't break, continue to next iteration
                continue

    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"Unexpected error in WebSocket handler: {e}")
        # Don't try to send anything here as the connection might be closed 