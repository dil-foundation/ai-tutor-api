import asyncio
import json
import base64
import os
import io
from pydub import AudioSegment

import websockets
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.audio_utils import validate_and_convert_audio

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

router = APIRouter()

YOUR_PROMPT = (
    "You are a kind, encouraging, and patient English tutor for Urdu-speaking learners. "
    "Listen to the user's spoken sentence (which is in Urdu), translate it into clear, simple English, "
    "and teach them to say the English sentence step by step. "
    "Speak slowly and clearly in simple English, like teaching a child. "
    "If their pronunciation or grammar is incorrect, gently correct them and ask them to repeat. "
    "Praise them when correct, and guide them word by word if they struggle. "
    "Avoid difficult words unless teaching explicitly. "
    "If appropriate, tell them the English meaning in Urdu at the end."
)


async def talk_to_openai(audio_bytes: bytes) -> bytes:
    """
    Connects to OpenAI's Realtime API, sends audio, and returns the response audio.
    """
    response_audio_chunks = []
    uri = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2025-06-03"

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "OpenAI-Beta": "realtime=v1"
    }

    async with websockets.connect(uri, additional_headers=headers) as ws:
        # Configure the session for audio-to-audio
        await ws.send(json.dumps({
            "type": "session.update",
            "session": {
                "modalities": ["audio", "text"],
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "instructions": YOUR_PROMPT
            }
        }))

        # Send the user's audio data in a single chunk
        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
        await ws.send(json.dumps({
            "type": "input_audio_buffer.append",
            "audio": audio_base64
        }))
        
        # Tell the server that the user's audio is complete
        await ws.send(json.dumps({"type": "input_audio_buffer.commit"}))
        
        # Request a response from the model
        await ws.send(json.dumps({"type": "response.create"}))

        # Receive the streamed audio response from OpenAI
        async for message in ws:
            data = json.loads(message)
            if data.get("type") == "response.audio.delta":
                response_audio_chunks.append(base64.b64decode(data["delta"]))
            elif data.get("type") == "response.done":
                break  # The model has finished sending its response
            elif data.get("type") == "error":
                error_details = data.get('error', {})
                print(f"OpenAI Error: {error_details.get('message')} (Code: {error_details.get('code')})")
                break

    # Combine the raw PCM audio chunks
    raw_pcm_data = b"".join(response_audio_chunks)

    if not raw_pcm_data:
        return b""

    # Create a pydub AudioSegment from the raw PCM data
    # OpenAI Realtime API for pcm16 defaults to a 24kHz sample rate
    audio_segment = AudioSegment(
        data=raw_pcm_data,
        sample_width=2,  # 16-bit PCM = 2 bytes
        frame_rate=24000, # OpenAI's default for pcm16 output
        channels=1
    )

    # Export the audio segment to an in-memory WAV file with proper format
    wav_buffer = io.BytesIO()
    
    # Use WAV format which is more reliable for mobile playback
    audio_segment.export(
        wav_buffer, 
        format="wav"
    )
    
    audio_data = wav_buffer.getvalue()
    print(f"Generated audio data size: {len(audio_data)} bytes")
    
    # Check if the audio data has proper WAV headers
    if len(audio_data) > 12:
        print(f"First 12 bytes: {audio_data[:12].hex()}")
        # Check for WAV header (RIFF)
        if audio_data[0:4] == b'RIFF' and audio_data[8:12] == b'WAVE':
            print("✅ WAV header detected - file appears to be valid WAV")
        else:
            print("❌ WAV header not found - file may be corrupted")
    
    return audio_data


@router.websocket("/ws/learn_gpt")
async def learn_gpt_conversation(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                audio_base64 = message.get("audio_base64")
                if not audio_base64:
                    await websocket.send_json({
                        "response": "No audio_base64 found.",
                        "step": "error"
                    })
                    continue
            except Exception:
                await websocket.send_json({
                    "response": "Invalid JSON format.",
                    "step": "error"
                })
                continue

            try:
                audio_bytes = base64.b64decode(audio_base64)
                # Validate and convert the audio
                converted_audio_bytes = validate_and_convert_audio(audio_bytes)
            except Exception as e:
                print(f"Failed to process audio: {e}")
                await websocket.send_json({
                    "response": "Failed to process audio.",
                    "step": "error"
                })
                continue

            # 🔷 Call OpenAI
            try:
                response_audio = await talk_to_openai(converted_audio_bytes)
                print("✅ Received response from OpenAI")
            except Exception as e:
                print(f"Error calling OpenAI: {e}")
                await websocket.send_json({
                    "response": "Failed to get response from AI.",
                    "step": "error"
                })
                continue

            # Send back the audio response
            await websocket.send_bytes(response_audio)

    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"Unexpected error: {e}")
