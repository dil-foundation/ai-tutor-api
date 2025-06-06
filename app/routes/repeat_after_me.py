from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import json
import os
from io import BytesIO
from app.services.tts import synthesize_speech_with_openai
from app.services.tts import synthesize_speech_with_elevenlabs
from app.services.feedback import get_fluency_feedback
from app.services.stt_english import transcribe_english_audio

from fastapi import UploadFile, File


router = APIRouter()

PHRASES_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'repeat_after_me_phrases.json')

def get_phrase_by_id(phrase_id: int):
    with open(PHRASES_FILE, 'r', encoding='utf-8') as f:
        phrases = json.load(f)
        for phrase in phrases:
            if phrase['id'] == phrase_id:
                return phrase['phrase']
    return None

# @router.get(
#     "/repeat-after-me/{phrase_id}",
#     summary="Get Audio for Repeat Phrase",
#     description="Returns a WAV audio stream for the phrase associated with the given phrase ID. Used in 'Repeat After Me' training."
# )
@router.get(
    "/repeat-after-me/{phrase_id}",
    summary="Stage 1 - Exercise 1: Play Phrase Audio",
    description="Repeat After Me - Phrase Training: Returns the audio of the sentence based on the given phrase ID."
)
async def repeat_after_me(phrase_id: int):
    phrase = get_phrase_by_id(phrase_id)
    if not phrase:
        raise HTTPException(status_code=404, detail="Phrase not found")

    return await synthesize_speech_with_elevenlabs(phrase)


@router.post(
    "/repeat-after-me/evaluate/{phrase_id}",
    summary="Stage 1 - Exercise 1: Evaluate Pronunciation",
    description="Repeat After Me - Phrase Training: Evaluates the user's pronunciation by comparing their spoken audio with the expected phrase. Requires audio input and phrase ID."
)
async def evaluate_repeat_after_me(
    phrase_id: int,
    file: UploadFile = File(...),
):
    # Get expected phrase
    with open(PHRASES_FILE, 'r', encoding='utf-8') as f:
        phrases = json.load(f)
        phrase_data = next((item for item in phrases if item['id'] == phrase_id), None)

    if not phrase_data:
        raise HTTPException(status_code=404, detail="Phrase not found")

    expected_phrase = phrase_data['phrase']

    # Transcribe user audio
    audio_bytes = await file.read()
    user_transcript = transcribe_english_audio(audio_bytes)

    # Get fluency feedback
    feedback = get_fluency_feedback(user_transcript, expected_phrase)

    return {
        "transcript": user_transcript,
        "expected_phrase": expected_phrase,
        "feedback": feedback
    }