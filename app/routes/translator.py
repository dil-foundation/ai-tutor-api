from fastapi import APIRouter, UploadFile, File
from fastapi.responses import JSONResponse
import io

from app.services import stt, translation, tts, whisper_scoring, feedback

router = APIRouter()

@router.post("/speak")
async def process_voice(file: UploadFile = File(...)):
    # Read file as bytes
    audio_bytes = await file.read()
    
    # Transcribe Urdu audio
    urdu_text = stt.transcribe_audio_bytes(audio_bytes)
    
    # Translate to English
    english_translation = translation.translate_urdu_to_english(urdu_text)
    
    # Score pronunciation
    pronunciation_score = whisper_scoring.score_pronunciation(audio_bytes, english_translation)
    
    # Fluency feedback
    fluency_feedback = feedback.get_fluency_feedback(english_translation)

    return JSONResponse(content={
        "urdu_text": urdu_text,
        "english_translation": english_translation,
        "pronunciation_score": pronunciation_score,
        "fluency_feedback": fluency_feedback
    })
