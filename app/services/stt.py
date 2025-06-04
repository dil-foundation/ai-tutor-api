from google.cloud import speech
from pydub import AudioSegment
import base64
import io
from fastapi import HTTPException

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
        return transcript
        
    except HTTPException as e: # Re-raise HTTPException
        raise e
    except Exception as e:
        print(f"❌ Google Speech API Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Speech-to-text service error: {str(e)}")
