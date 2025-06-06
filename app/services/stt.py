from google.cloud import speech
from pydub import AudioSegment
import base64
import io
from fastapi import HTTPException
from .translation import detect_language
from langdetect import detect
import torch
import whisper
import tempfile
import os

# Load the Whisper model only once
model = whisper.load_model("base")

def transcribe_and_detect_language(audio_bytes: bytes) -> tuple[str, str]:
    transcribed_text = transcribe_audio_bytes_whisper(audio_bytes)
    if not transcribed_text.strip():
        return "", "Unknown"
    
    language = detect_language(transcribed_text)
    print(f"Detected Language from Text: {language}")
    return transcribed_text, language

def transcribe_audio_bytes_whisper(audio_bytes: bytes) -> str:
    """
    Saves audio bytes to a temporary file and uses Whisper to transcribe.
    Returns the transcribed text.
    """
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(audio_bytes)
            tmp.flush()
            temp_audio_path = tmp.name

        # Transcribe using Whisper
        result = model.transcribe(temp_audio_path)

        transcribed_text = result['text']
        print(f"📝 Transcribed Text: {transcribed_text.strip()}")

        return transcribed_text.strip()
    except Exception as e:
        print(f"❌ Error during transcription: {str(e)}")
        return ""
    finally:
        try:
            os.remove(temp_audio_path)  # Clean up temp file
        except:
            pass


def transcribe_audio_bytes(audio_bytes: bytes, language_code: str = "ur-PK") -> str:
    try:
        # Allow pydub to auto-detect format
        audio_segment = AudioSegment.from_file(io.BytesIO(audio_bytes))
        mono_audio_segment = audio_segment.set_channels(1)
        # Set sample width to 2 bytes (16-bit) for LINEAR16 compatibility
        mono_audio_segment = mono_audio_segment.set_sample_width(2)

        buffer = io.BytesIO()
        # Export as WAV for Google Speech API, as it's a widely supported format
        mono_audio_segment.export(buffer, format="wav")
        mono_audio_bytes = buffer.getvalue()

    except Exception as e:
        print(f"❌ Pydub Error converting audio: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Failed to process audio file: {str(e)}")

    try:
        client = speech.SpeechClient()
        audio = speech.RecognitionAudio(content=mono_audio_bytes)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16, # This matches WAV format
            language_code=language_code, # Use the provided language_code parameter
            sample_rate_hertz=mono_audio_segment.frame_rate # Use frame rate from converted audio
        )

        response = client.recognize(config=config, audio=audio)
        
        if not response.results or not response.results[0].alternatives:
            print("❌ Google Speech API: No transcription results.")
            raise HTTPException(status_code=400, detail="No transcription received from speech API.")
            
        transcript = response.results[0].alternatives[0].transcript
        print("transcript: ",transcript)
        return transcript
        
    except HTTPException as e: # Re-raise HTTPException
        raise e
    except Exception as e:
        print(f"❌ Google Speech API Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Speech-to-text service error: {str(e)}")