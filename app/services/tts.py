from google.cloud import texttospeech
from io import BytesIO
import httpx
from fastapi.responses import StreamingResponse
from app.config import ELEVEN_API_KEY, ELEVEN_VOICE_ID

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

def synthesize_speech(text: str):
    client = texttospeech.TextToSpeechClient()

    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.LINEAR16  # WAV format
    )

    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )

    return response.audio_content  # WAV audio bytes
