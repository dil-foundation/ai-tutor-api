import tempfile
import os

# Lazy loading - don't import whisper at module level
_whisper = None
_model = None

def get_whisper_module():
    """Get the whisper module with lazy loading"""
    global _whisper
    if _whisper is None:
        try:
            import whisper
            _whisper = whisper
        except ImportError:
            _whisper = False  # Use False to indicate import failed
    return _whisper if _whisper is not False else None

def get_whisper_model():
    """Get the Whisper model with lazy loading"""
    global _model
    if _model is None:
        whisper = get_whisper_module()
        if whisper is not None:
            try:
                _model = whisper.load_model("base")
            except Exception as e:
                print(f"Failed to load Whisper model: {e}")
                _model = None
    return _model

def transcribe_with_whisper(audio_bytes: bytes) -> str:
    model = get_whisper_model()
    if model is None:
        raise ValueError("Whisper model not available")
    
    # Save audio bytes to a temporary .wav file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
        f.write(audio_bytes)
        f.flush()
        os.fsync(f.fileno())
        temp_file_path = f.name

    try:
        result = model.transcribe(temp_file_path)
        transcript = result["text"]
        return transcript.strip()
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

def score_pronunciation(audio_bytes: bytes, expected_text: str) -> float:
    # Transcribe the audio
    transcript = transcribe_with_whisper(audio_bytes)

    # Basic word-match scoring
    expected_words = set(expected_text.lower().split())
    transcript_words = set(transcript.lower().split())

    if not expected_words:
        return 0.0

    accuracy = len(transcript_words & expected_words) / len(expected_words)
    return round(accuracy * 100, 2)
