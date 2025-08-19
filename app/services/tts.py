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

    audio_chunks = client.text_to_speech.convert(
        voice_id=ELEVEN_VOICE_ID,
        model_id="eleven_multilingual_v2",
        text=text,
        voice_settings={
            "stability": 0.7,
            "similarity_boost": 0.8,
            "speed": 0.8
        }
    )
    # If it's a normal (not async) generator:
    audio_bytes = b"".join(audio_chunks)
    return audio_bytes


async def synthesize_slow_correction_audio(text: str) -> bytes:
    """
    Generate slow audio for correction sentences to help users repeat after the AI.
    Uses slower speed and enhanced clarity settings for better pronunciation practice.
    """
    print(f"🔑 [SLOW_CORRECTION] Using API Key: {ELEVEN_API_KEY[:6]}...")
    print(f"🗣️ [SLOW_CORRECTION] Voice ID: {ELEVEN_VOICE_ID}")
    print(f"📝 [SLOW_CORRECTION] Text to synthesize slowly: '{text}'")

    audio_chunks = client.text_to_speech.convert(
        voice_id=ELEVEN_VOICE_ID,
        model_id="eleven_multilingual_v2",
        text=text,
        voice_settings={
            "stability": 0.8,        # Higher stability for clearer pronunciation
            "similarity_boost": 0.9,  # Higher similarity for consistent voice
            "speed": 0.7            # Slower speed for easier repetition
        }
    )
    
    # Convert generator to bytes
    audio_bytes = b"".join(audio_chunks)
    print(f"✅ [SLOW_CORRECTION] Slow correction audio generated, size: {len(audio_bytes)} bytes")
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


async def synthesize_speech_exercises(text: str) -> bytes:
    """
    Main TTS function that uses ElevenLabs instead of Google TTS
    This function maintains the same interface as before but uses ElevenLabs
    """
    print(f"🔄 Starting ElevenLabs TTS for text: '{text}'")
    try:
        print(f"🔑 Using ElevenLabs API Key: {ELEVEN_API_KEY[:6]}...")
        print(f"🗣️ Using ElevenLabs Voice ID: {ELEVEN_VOICE_ID}")
        print(f"📝 Text to synthesize: '{text}'")

        # Use ElevenLabs instead of Google TTS
        audio_generator = client.text_to_speech.convert(
            voice_id=ELEVEN_VOICE_ID,
            model_id="eleven_multilingual_v2",
            text=text,
            voice_settings={
                "stability": 0.7,
                "similarity_boost": 0.8,
                "speed": 0.8
            }
        )
        
        # Convert generator to bytes
        audio_bytes = b''.join(audio_generator)
        print(f"✅ ElevenLabs TTS successful, audio size: {len(audio_bytes)} bytes")

        return audio_bytes  # Return bytes for compatibility
    except Exception as e:
        print(f"❌ ElevenLabs TTS error: {str(e)}")
        raise e
