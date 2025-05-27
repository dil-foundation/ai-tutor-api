import whisper
import tempfile
import base64
import os

# Load the Whisper model once
model = whisper.load_model("base")

def score_pronunciation(audio_base64: str, expected_text: str) -> float:
    # Decode the base64 audio string
    audio_data = base64.b64decode(audio_base64)

    # Create a temporary .wav file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
        f.write(audio_data)
        f.flush()
        os.fsync(f.fileno())  # Ensure data is written to disk
        temp_file_path = f.name

    try:
        # Run transcription using Whisper
        result = model.transcribe(temp_file_path)
        transcript = result["text"]

        # Basic similarity scoring
        expected_words = set(expected_text.lower().split())
        transcript_words = set(transcript.lower().split())

        accuracy = len(transcript_words & expected_words) / len(expected_words) if expected_words else 0
        return round(accuracy * 100, 2)

    finally:
        # Clean up temporary file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
