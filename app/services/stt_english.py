# app/services/stt_english.py

from google.cloud import speech
try:
    from pydub import AudioSegment
except ImportError:
    # Python 3.13 compatibility issue - audioop module removed
    AudioSegment = None
import io

def transcribe_english_audio(audio_bytes: bytes) -> str:
    """
    Transcribes English audio bytes using Google Cloud STT.
    Supports MP3, M4A, WAV, etc.
    """

    # Let pydub auto-detect the format
    try:
        if AudioSegment is None:
            raise ValueError("Audio processing not available due to Python 3.13 compatibility issues")
        audio_segment = AudioSegment.from_file(io.BytesIO(audio_bytes))
    except Exception as e:
        raise ValueError(f"Unsupported audio format or corrupted file: {e}")

    # Convert to mono channel for Google STT
    mono_audio = audio_segment.set_channels(1)

    # Export to LINEAR16 WAV (required format for Google STT)
    wav_io = io.BytesIO()
    mono_audio.export(wav_io, format="wav")
    wav_io.seek(0)
    mono_audio_bytes = wav_io.read()

    # Setup Google STT client
    client = speech.SpeechClient()
    audio = speech.RecognitionAudio(content=mono_audio_bytes)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        language_code="en-US",
        sample_rate_hertz=audio_segment.frame_rate
    )

    response = client.recognize(config=config, audio=audio)

    if not response.results:
        return ""

    transcript = response.results[0].alternatives[0].transcript
    return transcript
