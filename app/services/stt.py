from google.cloud import speech
from pydub import AudioSegment
import base64
import io

def transcribe_audio_bytes(audio_bytes: bytes) -> str:
    client = speech.SpeechClient()

    # Convert to mono using pydub
    audio_segment = AudioSegment.from_file(io.BytesIO(audio_bytes), format="wav")
    mono_audio_segment = audio_segment.set_channels(1)

    buffer = io.BytesIO()
    mono_audio_segment.export(buffer, format="wav")
    mono_audio_bytes = buffer.getvalue()

    audio = speech.RecognitionAudio(content=mono_audio_bytes)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        language_code="ur-PK",
        sample_rate_hertz=audio_segment.frame_rate
    )

    response = client.recognize(config=config, audio=audio)
    transcript = response.results[0].alternatives[0].transcript
    return transcript
