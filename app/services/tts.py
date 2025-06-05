import openai
from io import BytesIO
from fastapi.responses import StreamingResponse
import os

openai.api_key = os.getenv("OPENAI_API_KEY")

def synthesize_speech_with_openai(text: str):
    response = openai.audio.speech.create(
        model="tts-1-hd",
        voice="nova",      
        input=text
    )

    # The response is a binary audio stream (MP3)
    audio_stream = BytesIO(response.read())
    audio_stream.seek(0)

    return StreamingResponse(
        content=audio_stream,
        media_type="audio/wav",
        headers={"Content-Disposition": 'inline; filename="output.wav"'}
    )
