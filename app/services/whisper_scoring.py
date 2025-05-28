import whisper
import tempfile
import os

# Load Whisper model only once
model = whisper.load_model("base")

def score_pronunciation(audio_bytes: bytes, expected_text: str) -> float:
    # Create a temporary .wav file to save the audio bytes
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
        f.write(audio_bytes)
        f.flush()
        os.fsync(f.fileno())  # Make sure it's written to disk
        temp_file_path = f.name

    try:
        # Transcribe the audio using Whisper
        result = model.transcribe(temp_file_path)
        transcript = result["text"]

        # Compare transcribed text with expected text (basic word match scoring)
        expected_words = set(expected_text.lower().split())
        transcript_words = set(transcript.lower().split())

        accuracy = len(transcript_words & expected_words) / len(expected_words) if expected_words else 0
        return round(accuracy * 100, 2)

    finally:
        # Clean up temporary file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
