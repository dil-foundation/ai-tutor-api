from fastapi import APIRouter, UploadFile, File, Body, Form, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
import io
import base64

from app.services import stt, translation, tts, whisper_scoring, feedback

router = APIRouter()

@router.post("/speak/metadata")
async def speak_urdu_to_english_metadata(file: UploadFile = File(...)):
    # Step 1: Read Urdu audio bytes
    audio_bytes = await file.read()
    
    # Step 2: Convert Urdu audio to text
    urdu_text = stt.transcribe_audio_bytes(audio_bytes)
    print("🔍 Urdu Text:", urdu_text)
    if not urdu_text.strip():
        raise HTTPException(status_code=400, detail="Failed to transcribe Urdu audio.")

    # Step 3: Translate Urdu to English
    english_translation = translation.translate_urdu_to_english(urdu_text)
    print("🔍 English Translation:", english_translation)
    if not english_translation.strip():
        raise HTTPException(status_code=400, detail="Failed to translate Urdu text.")

    # Step 4: Return metadata as JSON
    return {
        "urdu_text": urdu_text,
        "english_translation": english_translation
    }

@router.post("/speak/audio")
async def speak_urdu_to_english_audio(file: UploadFile = File(...)):
    # Step 1: Read Urdu audio bytes
    audio_bytes = await file.read()

    # Step 2: Convert to Urdu text
    urdu_text = stt.transcribe_audio_bytes(audio_bytes)
    print("🔍 Urdu Text:", urdu_text)
    if not urdu_text.strip():
        raise HTTPException(status_code=400, detail="Failed to transcribe audio.")

    # Step 3: Translate Urdu to English
    english_translation = translation.translate_urdu_to_english(urdu_text)
    print("🔍 English Translation:", english_translation)
    if not english_translation.strip():
        raise HTTPException(status_code=400, detail="Failed to translate Urdu.")

    # Step 4: Generate English audio
    english_audio_bytes = tts.synthesize_speech(english_translation)
    print("Length of the english audio bytes: ",len(english_audio_bytes))
    if not english_audio_bytes:
        raise HTTPException(status_code=500, detail="Generated audio is empty")

    # Step 5: Return audio as stream (WAV format)
    audio_stream = io.BytesIO(english_audio_bytes)
    audio_stream.seek(0)  # Rewind to start

    return StreamingResponse(
        content=audio_stream,
        media_type="audio/wav",
        headers={"Content-Disposition": 'inline; filename="response.wav"'}
    )

@router.post("/feedback")
async def get_english_feedback(
    payload: dict = Body(...)
):
    print("✅ /api/translate/feedback endpoint CALLED (expecting Base64 JSON for audio)")
    try:
        expected_text = payload.get("expected_text")
        audio_base64 = payload.get("audio_base64")
        filename = payload.get("filename", "practiced_audio.wav")

        if not expected_text:
            raise HTTPException(status_code=400, detail="Missing 'expected_text' in payload.")
        if not audio_base64:
            raise HTTPException(status_code=400, detail="Missing 'audio_base64' in payload.")

        print(f"Received for feedback: expected_text='{expected_text}', audio_filename='{filename}', audio_base64 length={len(audio_base64)}")

        # Decode the Base64 string to bytes
        audio_bytes = base64.b64decode(audio_base64)
        print(f"Decoded audio bytes length for feedback: {len(audio_bytes)}")

        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Decoded audio for feedback is empty.")

        # Step 2: Transcribe using Whisper
        # Assuming whisper_scoring.transcribe_with_whisper expects audio_bytes
        user_text = whisper_scoring.transcribe_with_whisper(audio_bytes)
        print(f"Whisper transcription for feedback: {user_text}")

        # Step 3: Pronunciation accuracy score
        # Assuming whisper_scoring.score_pronunciation expects audio_bytes and expected_text
        score = whisper_scoring.score_pronunciation(audio_bytes, expected_text)
        print(f"Pronunciation score: {score}")

        # Step 4: GPT-4 feedback on fluency, grammar, etc.
        # Assuming feedback.get_fluency_feedback expects user_text (transcribed) and expected_text
        feedback_text = feedback.get_fluency_feedback(user_text, expected_text)
        print(f"Fluency feedback: {feedback_text}")

        # Step 5: Return response
        # Ensure the score key matches your client's 'FeedbackData' interface ('pronunciation_score')
        return JSONResponse(content={
            "user_text": user_text,
            "pronunciation_score": score, # Matching common client interface key
            "fluency_feedback": feedback_text
        })

    except HTTPException as e:
        # Re-raise HTTPExceptions directly
        raise e
    except Exception as e:
        print(f"❌ ERROR in /api/translate/feedback (Base64 audio): {str(e)}")
        # Consider logging the full traceback for non-HTTP exceptions
        # import traceback
        # print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal server error during feedback processing: {str(e)}")



@router.post("/transcribe-audio-direct")
async def transcribe_audio_direct(
    payload: dict = Body(...),  # Expect a JSON body containing the base64 string
    # language_code: str = Query("en-US") # language_code can be part of the payload if preferred
):
    print("✅ /api/translate/transcribe-audio-direct endpoint CALLED (expecting Base64 JSON)")
    try:
        audio_base64 = payload.get("audio_base64")
        filename = payload.get("filename", "audio.wav")


        if not audio_base64:
            raise HTTPException(status_code=400, detail="Missing 'audio_base64' in payload.")

        print(f"Received audio_base64 for: {filename}, length: {len(audio_base64)}")

        # Decode the Base64 string to bytes
        audio_bytes = base64.b64decode(audio_base64)
        print(f"Decoded audio bytes length: {len(audio_bytes)}")

        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Decoded audio is empty.")

        transcribed_text = stt.transcribe_audio_bytes(audio_bytes, language_code="en-US") # Ensure correct language_code for English

        if not transcribed_text.strip():
            raise HTTPException(status_code=400, detail="Audio transcribed to empty text.")

        return JSONResponse(content={"transcribed_text": transcribed_text})

    except HTTPException as e:
        # Re-raise HTTPExceptions directly
        raise e
    except Exception as e:
        print(f"❌ ERROR in /api/translate/transcribe-audio-direct (Base64): {str(e)}")
        # Consider logging the full traceback for non-HTTP exceptions
        # import traceback
        # print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal server error during transcription: {str(e)}")