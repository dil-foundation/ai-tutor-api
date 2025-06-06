import openai
from io import BytesIO
import httpx
from fastapi.responses import StreamingResponse
import os
from app.config import ELEVEN_API_KEY, ELEVEN_VOICE_ID


openai.api_key = os.getenv("OPENAI_API_KEY")

async def synthesize_speech_with_elevenlabs(text: str):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVEN_VOICE_ID}"

    headers = {
        "xi-api-key": ELEVEN_API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "text": text,
        "voice_settings": {
            "stability": 0.7,
            "similarity_boost": 0.8
        }
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        audio_bytes = response.content

    audio_stream = BytesIO(audio_bytes)
    audio_stream.seek(0)

    return StreamingResponse(
        content=audio_stream,
        media_type="audio/mpeg",  # ElevenLabs returns MP3 by default
        headers={"Content-Disposition": 'inline; filename="output.mp3"'}
    )


def synthesize_speech_with_openai(text: str):
    response = openai.audio.speech.create(
        model="tts-1-hd",
        voice="nova",      
        input=text
    )

    # The response is a binary audio stream (MP3)
    audio_stream = BytesIO(response.read())
    audio_stream.seek(0)

    return StreamingResponse(
        content=audio_stream,
        media_type="audio/wav",
        headers={"Content-Disposition": 'inline; filename="output.wav"'}
    )
