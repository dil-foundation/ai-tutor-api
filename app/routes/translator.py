from fastapi import APIRouter, UploadFile, File, Form, HTTPException
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
async def get_english_feedback(file: UploadFile = File(...), expected_text: str = Form(...)):
    # Step 1: Read audio bytes
    audio_bytes = await file.read()

    # Step 2: Transcribe using Whisper
    user_text = whisper_scoring.transcribe_with_whisper(audio_bytes)

    # Step 3: Pronunciation accuracy score
    score = whisper_scoring.score_pronunciation(audio_bytes, expected_text)

    # Step 4: GPT-4 feedback on fluency, grammar, etc.
    feedback_text = feedback.get_fluency_feedback(user_text, expected_text)

    # Step 5: Return response
    return JSONResponse(content={
        "user_text": user_text,
        "pronounciation_accuracy_score": score,
        "fluency_feedback": feedback_text
    })

