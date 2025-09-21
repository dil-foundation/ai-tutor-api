try:
    from pydub import AudioSegment
except ImportError:
    # Python 3.13 compatibility issue - audioop module removed
    AudioSegment = None
import io

def validate_and_convert_audio(audio_bytes: bytes) -> bytes:
    """
    Validates, converts, and returns audio bytes in the format required by OpenAI.
    (16kHz, single-channel, 16-bit PCM WAV)
    
    Returns:
        bytes: The converted audio bytes.
    
    Raises:
        ValueError: If the audio format is invalid or cannot be processed.
    """
    try:
        if AudioSegment is None:
            raise ValueError("Audio processing not available due to Python 3.13 compatibility issues")
        audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
        
        # Convert to 16kHz sample rate
        audio = audio.set_frame_rate(16000)
        
        # Convert to single channel (mono)
        audio = audio.set_channels(1)

        # Convert to 16-bit PCM
        audio = audio.set_sample_width(2)

        # Export to an in-memory WAV file
        buf = io.BytesIO()
        audio.export(buf, format="wav")
        
        print("✅ Audio successfully validated and converted to 16kHz mono WAV.")
        
        return buf.getvalue()

    except Exception as e:
        print(f"❌ Failed to validate or convert audio: {e}")
        raise ValueError("Invalid audio format")
