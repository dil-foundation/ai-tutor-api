from fastapi import APIRouter
from app.schemas.user_input import VoiceInput
from app.services import stt, translation, tts, whisper_scoring, feedback
from fastapi.responses import JSONResponse

router = APIRouter()

@router.post("/speak")
def process_voice(input: VoiceInput):
    urdu_text = stt.transcribe_audio(input.audio_base64)
    english_translation = translation.translate_urdu_to_english(urdu_text)
    pronunciation_score = whisper_scoring.score_pronunciation(input.audio_base64, english_translation)
    fluency_feedback = feedback.get_fluency_feedback(english_translation)

    return JSONResponse(content={
        "urdu_text": urdu_text,
        "english_translation": english_translation,
        "pronunciation_score": pronunciation_score,
        "fluency_feedback": fluency_feedback
    })
