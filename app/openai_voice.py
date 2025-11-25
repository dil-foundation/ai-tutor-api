import asyncio
import json
import websockets
import base64
import wave
import zipfile
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get OpenAI API key from environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError(
        "OPENAI_API_KEY not found in environment variables. "
        "Please set it in your .env file or environment."
    )

# All available OpenAI Realtime API voices
# Supported voices: alloy, ash, ballad, coral, echo, sage, shimmer, verse, marin, cedar
OPENAI_VOICES = [
    "alloy",
    "ash",
    "ballad",
    "coral",
    "echo",
    "sage",
    "shimmer",
    "verse",
    "marin",
    "cedar"
]

REALTIME_URL = (
    "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17"
)

HEADERS = {
    "Authorization": f"Bearer {OPENAI_API_KEY}",
    "OpenAI-Beta": "realtime=v1"
}

# Test text for all voices
TEST_TEXT = (
    "Hello! This is a test of OpenAI's Realtime API voice capabilities. "
    "I am an AI English tutor designed to help students improve their English skills. "
    "How can I assist you today?"
)

# Output directory for audio files
OUTPUT_DIR = Path("openai_voice_samples")
OUTPUT_DIR.mkdir(exist_ok=True)

async def test_voice(voice: str, text: str, output_dir: Path) -> str:
    """
    Test a single OpenAI voice and save the audio file.
    Returns the path to the saved audio file.
    """
    print(f"\n🔊 Testing voice: {voice}")

    try:
        async with websockets.connect(
            REALTIME_URL,
            additional_headers=HEADERS
        ) as ws:

            print("🟢 Connected to OpenAI")

            # Update session with voice settings
            await ws.send(json.dumps({
                "type": "session.update",
                "session": {
                    "voice": voice,
                    "modalities": ["text", "audio"],
                    "output_audio_format": "pcm16"
                }
            }))

            # Wait for session to be ready (session.updated will come in the message loop)
            await asyncio.sleep(0.5)

            # Create response (text → audio stream)
            # Must use ['audio', 'text'] or ['text'] - cannot use just ['audio']
            await ws.send(json.dumps({
                "type": "response.create",
                "response": {
                    "modalities": ["audio", "text"],
                    "instructions": text
                }
            }))

            audio_bytes = bytearray()
            timeout_count = 0
            max_timeout = 30  # 30 seconds timeout

            while True:
                try:
                    message = await asyncio.wait_for(ws.recv(), timeout=2.0)
                except asyncio.TimeoutError:
                    timeout_count += 1
                    if timeout_count >= max_timeout:
                        print("⚠️ Timeout waiting for response")
                        break
                    continue

                # Binary audio frames (PCM16)
                if isinstance(message, bytes):
                    audio_bytes.extend(message)
                    continue

                # JSON control events
                data = json.loads(message)
                msg_type = data.get("type")

                if msg_type == "response.output_audio.delta":
                    # Base64-encoded PCM audio
                    delta_data = data.get("delta", {})
                    if isinstance(delta_data, dict):
                        encoded = delta_data.get("audio", "")
                    elif isinstance(delta_data, str):
                        encoded = delta_data
                    else:
                        encoded = ""
                    
                    if encoded:
                        try:
                            audio_bytes.extend(base64.b64decode(encoded))
                        except Exception as e:
                            print(f"⚠️ Error decoding audio delta: {e}")

                elif msg_type in ["response.completed", "response.done"]:
                    print("🏁 Response completed")
                    break
                
                elif msg_type == "error":
                    error_msg = data.get("error", {}).get("message", "Unknown error")
                    print(f"❌ Error from OpenAI: {error_msg}")
                    break

            if len(audio_bytes) == 0:
                print(f"⚠️ No audio data received for voice: {voice}")
                return None

            print(f"🎧 Total audio bytes: {len(audio_bytes)}")

            # Save as WAV (PCM16, 24kHz, mono)
            filename = output_dir / f"{voice}.wav"
            save_wav(str(filename), bytes(audio_bytes))
            print(f"✅ Saved audio as {filename}")
            return str(filename)

    except Exception as e:
        print(f"❌ Error testing voice {voice}: {e}")
        import traceback
        traceback.print_exc()
        return None


def save_wav(filename: str, pcm_bytes: bytes, sample_rate: int = 24000):
    """Save PCM16 audio bytes as WAV file."""
    with wave.open(filename, "wb") as f:
        f.setnchannels(1)             # mono
        f.setsampwidth(2)             # 16-bit PCM = 2 bytes
        f.setframerate(sample_rate)
        f.writeframes(pcm_bytes)


def create_zip_archive(output_dir: Path, zip_filename: str = None) -> str:
    """
    Create a ZIP archive containing all audio files.
    Returns the path to the ZIP file.
    """
    if zip_filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"openai_voices_{timestamp}.zip"
    
    zip_path = output_dir.parent / zip_filename
    
    print(f"\n📦 Creating ZIP archive: {zip_path}")
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for audio_file in output_dir.glob("*.wav"):
            zipf.write(audio_file, audio_file.name)
            print(f"   Added: {audio_file.name}")
    
    file_size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"✅ ZIP archive created: {zip_path} ({file_size_mb:.2f} MB)")
    
    return str(zip_path)


async def test_all_voices():
    """Test all OpenAI voices and save audio files."""
    print("=" * 60)
    print("🎤 OpenAI Realtime API Voice Testing")
    print("=" * 60)
    print(f"📝 Test text: {TEST_TEXT[:50]}...")
    print(f"📁 Output directory: {OUTPUT_DIR}")
    print(f"🎙️  Voices to test: {', '.join(OPENAI_VOICES)}")
    print("=" * 60)
    
    successful_voices = []
    failed_voices = []
    
    for i, voice in enumerate(OPENAI_VOICES, 1):
        print(f"\n[{i}/{len(OPENAI_VOICES)}] Processing voice: {voice}")
        
        filepath = await test_voice(voice, TEST_TEXT, OUTPUT_DIR)
        
        if filepath:
            successful_voices.append((voice, filepath))
        else:
            failed_voices.append(voice)
        
        # Small delay between requests to avoid rate limiting
        if i < len(OPENAI_VOICES):
            await asyncio.sleep(1)
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"✅ Successful: {len(successful_voices)}/{len(OPENAI_VOICES)}")
    if successful_voices:
        print("   Voices:")
        for voice, filepath in successful_voices:
            file_size_kb = Path(filepath).stat().st_size / 1024
            print(f"   - {voice}: {Path(filepath).name} ({file_size_kb:.1f} KB)")
    
    if failed_voices:
        print(f"❌ Failed: {len(failed_voices)}")
        print(f"   Voices: {', '.join(failed_voices)}")
    
    # Create ZIP archive
    if successful_voices:
        zip_path = create_zip_archive(OUTPUT_DIR)
        print(f"\n📧 Ready to send to manager:")
        print(f"   ZIP file: {zip_path}")
        print(f"   Individual files in: {OUTPUT_DIR}")
    
    print("=" * 60)
    return successful_voices, failed_voices


async def main():
    """Main function to test all voices."""
    await test_all_voices()


if __name__ == "__main__":
    asyncio.run(main())