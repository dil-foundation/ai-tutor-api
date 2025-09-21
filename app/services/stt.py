from elevenlabs import ElevenLabs
from pydub import AudioSegment

# Import Google Cloud Speech conditionally to avoid credential issues during startup
try:
    from google.cloud import speech
    GOOGLE_SPEECH_AVAILABLE = True
except Exception as e:
    print(f"⚠️ Google Cloud Speech not available: {e}")
    GOOGLE_SPEECH_AVAILABLE = False
    speech = None
import base64
import io
from fastapi import HTTPException
from app.config import ELEVEN_API_KEY
from elevenlabs import ElevenLabs
import re
#api key
elevenlabs = ElevenLabs(api_key=ELEVEN_API_KEY)

def transcribe_audio_bytes_eng_only(audio_bytes: bytes) -> dict:
    """
    Transcribe audio using ElevenLabs STT with language detection
    Returns a dictionary with transcription and language info
    """
    try:
        # Allow pydub to auto-detect format
        audio_segment = AudioSegment.from_file(io.BytesIO(audio_bytes))
        mono_audio_segment = audio_segment.set_channels(1)
        # Set sample width to 2 bytes (16-bit) for better compatibility
        mono_audio_segment = mono_audio_segment.set_sample_width(2)

        buffer = io.BytesIO()
        # Export as MP3 for ElevenLabs API
        mono_audio_segment.export(buffer, format="mp3")
        mono_audio_bytes = buffer.getvalue()

    except Exception as e:
        print(f"❌ Pydub Error converting audio: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Failed to process audio file: {str(e)}")

    try:
        # Create BytesIO object for ElevenLabs
        audio_data = io.BytesIO(mono_audio_bytes)
        
        # 🎯 Transcribe with ElevenLabs
        transcription = elevenlabs.speech_to_text.convert(
            file=audio_data,
            model_id="scribe_v1", # Model to use, for now only "scribe_v1" is supported
            tag_audio_events=True, # Tag audio events like laughter, applause, etc.
            language_code="eng", # Language of the audio file. If set to None, the model will detect the language automatically.
            diarize=True, # Whether to annotate who is speaking                
        )

        # Extract language information
        # detected_language = transcription.language_code
        # language_confidence = transcription.language_probability
        transcribed_text = transcription.text
        
        # 🪄 Remove all text inside parentheses (and the parentheses)
        transcribed_text_clean = re.sub(r"\([^)]*\)", "", transcribed_text).strip()
        # Replace multiple spaces with single space
        transcribed_text_clean = re.sub(r"\s+", " ", transcribed_text_clean)

        print(f"✅ ElevenLabs Transcription Result:")
        # print(f"Detected Language: {detected_language}")
        # print(f"Language Confidence: {language_confidence:.2%}")
        print(f"Transcription: {transcribed_text}")
        print(f"Clean of Background Noise of Transcription: {transcribed_text_clean}")

        # Return structured response with language detection
        return {
            "text": transcribed_text_clean,
        }
        
    except Exception as e:
        print(f"❌ ElevenLabs STT Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Speech-to-text service error: {str(e)}")


def transcribe_audio_bytes_eng(audio_bytes: bytes) -> dict:
    """
    Transcribe audio using ElevenLabs STT with language detection
    Returns a dictionary with transcription and language info
    """
    try:
        # Allow pydub to auto-detect format
        audio_segment = AudioSegment.from_file(io.BytesIO(audio_bytes))
        mono_audio_segment = audio_segment.set_channels(1)
        # Set sample width to 2 bytes (16-bit) for better compatibility
        mono_audio_segment = mono_audio_segment.set_sample_width(2)

        buffer = io.BytesIO()
        # Export as MP3 for ElevenLabs API
        mono_audio_segment.export(buffer, format="mp3")
        mono_audio_bytes = buffer.getvalue()

    except Exception as e:
        print(f"❌ Pydub Error converting audio: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Failed to process audio file: {str(e)}")

    try:
        # Create BytesIO object for ElevenLabs
        audio_data = io.BytesIO(mono_audio_bytes)
        
        # 🎯 Transcribe with ElevenLabs
        transcription = elevenlabs.speech_to_text.convert(
            file=audio_data,
            model_id="scribe_v1",          
            tag_audio_events=True,         
            diarize=True                  
        )

        # Extract language information
        detected_language = transcription.language_code
        language_confidence = transcription.language_probability
        transcribed_text = transcription.text
        
        # 🪄 Remove all text inside parentheses (and the parentheses)
        transcribed_text_clean = re.sub(r"\([^)]*\)", "", transcribed_text).strip()
        # Replace multiple spaces with single space
        transcribed_text_clean = re.sub(r"\s+", " ", transcribed_text_clean)

        print(f"✅ ElevenLabs Transcription Result:")
        print(f"Detected Language: {detected_language}")
        print(f"Language Confidence: {language_confidence:.2%}")
        print(f"Transcription: {transcribed_text}")
        print(f"Clean of Background Noise of Transcription: {transcribed_text_clean}")

        # Return structured response with language detection
        return {
            "text": transcribed_text_clean,
            "language_code": detected_language,
            "language_confidence": language_confidence,
            "is_english": detected_language.lower() in ["en", "en-us", "en-gb", "english","eng","tam"]
        }
        
    except Exception as e:
        print(f"❌ ElevenLabs STT Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Speech-to-text service error: {str(e)}")

def is_english_input(transcription_result: dict) -> bool:
    """
    Check if the detected language is English
    """
    return transcription_result.get("is_english", False)


def transcribe_audio_bytes(audio_bytes: bytes, language_code: str = "ur-PK") -> str:
    if not GOOGLE_SPEECH_AVAILABLE:
        raise HTTPException(status_code=503, detail="Google Cloud Speech service is not available")
    
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

def transcribe_audio_bytes_user_repeat(audio_bytes: bytes) -> dict:
    """
    Transcribe audio using ElevenLabs STT with language detection
    Returns a dictionary with transcription and language info
    """
    try:
        # Allow pydub to auto-detect format
        audio_segment = AudioSegment.from_file(io.BytesIO(audio_bytes))
        mono_audio_segment = audio_segment.set_channels(1)
        # Set sample width to 2 bytes (16-bit) for better compatibility
        mono_audio_segment = mono_audio_segment.set_sample_width(2)

        buffer = io.BytesIO()
        # Export as MP3 for ElevenLabs API
        mono_audio_segment.export(buffer, format="mp3")
        mono_audio_bytes = buffer.getvalue()

    except Exception as e:
        print(f"❌ Pydub Error converting audio: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Failed to process audio file: {str(e)}")

    try:
        # Create BytesIO object for ElevenLabs
        audio_data = io.BytesIO(mono_audio_bytes)
        
        # 🎯 Transcribe with ElevenLabs
        transcription = elevenlabs.speech_to_text.convert(
            file=audio_data,
            model_id="scribe_v1",          
            tag_audio_events=True,         
            diarize=True                  
        )

        # Extract language information
        detected_language = transcription.language_code
        language_confidence = transcription.language_probability
        transcribed_text = transcription.text
        
        # 🪄 Remove all text inside parentheses (and the parentheses)
        transcribed_text_clean = re.sub(r"\([^)]*\)", "", transcribed_text).strip()
        # Replace multiple spaces with single space
        transcribed_text_clean = re.sub(r"\s+", " ", transcribed_text_clean)

        print(f"✅ ElevenLabs Transcription Result:")
        print(f"Detected Language: {detected_language}")
        print(f"Language Confidence: {language_confidence:.2%}")
        print(f"Transcription: {transcribed_text}")
        print(f"Clean of Background Noise of Transcription: {transcribed_text_clean}")

        # Return structured response with language detection
        return {
            "text": transcribed_text_clean,
            "language_code": detected_language,
            "language_confidence": language_confidence,
            "is_english": detected_language.lower() in ["en", "en-us", "en-gb", "english","eng","tam"]
        }
        
    except Exception as e:
        print(f"❌ ElevenLabs STT Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Speech-to-text service error: {str(e)}")
