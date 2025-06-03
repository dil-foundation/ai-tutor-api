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

@router.get("/repeat-after-me/{phrase_id}")
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
