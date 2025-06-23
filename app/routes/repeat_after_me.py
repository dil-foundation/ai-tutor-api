from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import json
import os
from io import BytesIO
from app.services.tts import synthesize_speech

router = APIRouter()

PHRASES_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'repeat_after_me_phrases.json')

def get_phrase_by_id(phrase_id: int):
    with open(PHRASES_FILE, 'r', encoding='utf-8') as f:
        phrases = json.load(f)
        for phrase in phrases:
            if phrase['id'] == phrase_id:
                return phrase['phrase']
    return None

@router.post(
    "/repeat-after-me/{phrase_id}",
    summary="Convert phrase to audio for Repeat After Me Exercise",
    description="""
This endpoint is part of Stage 1 - Exercise 1 (Repeat After Me). 
It takes a phrase ID from a predefined list, converts the corresponding sentence into speech (TTS),
and returns the generated audio file as the response.
""",
    tags=["Stage 1 - Exercise 1 (Repeat After Me)"]
)
async def repeat_after_me(phrase_id: int):
    phrase = get_phrase_by_id(phrase_id)
    if not phrase:
        raise HTTPException(status_code=404, detail="Phrase not found")

    audio_content = synthesize_speech(phrase)
    audio_stream = BytesIO(audio_content)
    audio_stream.seek(0)

    return StreamingResponse(
        content=audio_stream,
        media_type="audio/wav",
        headers={"Content-Disposition": 'inline; filename="response.wav"'}
    )
