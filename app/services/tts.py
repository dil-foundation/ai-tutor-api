from google.cloud import texttospeech
from io import BytesIO
import httpx
from fastapi.responses import StreamingResponse
from app.config import ELEVEN_API_KEY, ELEVEN_VOICE_ID

from elevenlabs.client import ElevenLabs

# Create a reusable ElevenLabs client instance
client = ElevenLabs(api_key=ELEVEN_API_KEY)

def synthesize_speech_with_elevenlabs_exercises(text: str):
    print(f"🔑 Using API Key: {ELEVEN_API_KEY[:6]}...")
    print(f"🗣️ Voice ID: {ELEVEN_VOICE_ID}")

    # Get audio bytes
    audio_bytes = client.text_to_speech.convert(
        voice_id=ELEVEN_VOICE_ID,
        model_id="eleven_multilingual_v2",
        text=text,
        voice_settings={
            "stability": 0.7,
            "similarity_boost": 0.8,
            "speed": 0.8
        }
    )

    # Wrap in BytesIO and prepare response
    audio_stream = BytesIO(audio_bytes)
    audio_stream.seek(0)

    return StreamingResponse(
        content=audio_stream,
        media_type="audio/wav",  # or "audio/mpeg" if ElevenLabs gives mp3
        headers={"Content-Disposition": 'inline; filename="output.wav"'}
    )


async def synthesize_speech_bytes(text: str) -> bytes:
    print(f"🔑 Using API Key: {ELEVEN_API_KEY[:6]}...")
    print(f"🗣️ Voice ID: {ELEVEN_VOICE_ID}")

    audio_bytes = client.text_to_speech.convert(
        voice_id=ELEVEN_VOICE_ID,
        model_id="eleven_multilingual_v2",
        text=text,
        voice_settings={
            "stability": 0.7,
            "similarity_boost": 0.8,
            "speed": 0.8
        }
    )
    return audio_bytes

async def synthesize_speech_with_elevenlabs(text: str):
    audio_bytes = await synthesize_speech_bytes(text)
    audio_stream = BytesIO(audio_bytes)
    audio_stream.seek(0)

    return StreamingResponse(
        content=audio_stream,
        media_type="audio/mpeg",
        headers={"Content-Disposition": 'inline; filename="output.mp3"'}
    )


async def synthesize_speech(text: str) -> bytes:
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

    return response.audio_content  # This is bytes