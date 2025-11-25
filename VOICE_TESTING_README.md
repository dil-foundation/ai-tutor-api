# OpenAI Voice Testing Script

This script tests all available OpenAI Realtime API voices and creates audio samples for your manager.

## Features

- ✅ Tests all 6 OpenAI voices: `alloy`, `echo`, `fable`, `onyx`, `nova`, `shimmer`
- ✅ Saves individual WAV files for each voice
- ✅ Creates a ZIP archive with all audio files
- ✅ Provides detailed progress and summary reports

## Usage

### Run the Script

```bash
python app/openai_voice.py
```

### What It Does

1. **Connects** to OpenAI Realtime API
2. **Tests each voice** with a sample text
3. **Saves audio files** in `openai_voice_samples/` directory:
   - `alloy.wav`
   - `echo.wav`
   - `fable.wav`
   - `onyx.wav`
   - `nova.wav`
   - `shimmer.wav`
4. **Creates a ZIP archive** (e.g., `openai_voices_20241215_143022.zip`) in the project root
5. **Displays a summary** of successful and failed tests

## Output

### Directory Structure
```
project_root/
├── openai_voice_samples/
│   ├── alloy.wav
│   ├── echo.wav
│   ├── fable.wav
│   ├── onyx.wav
│   ├── nova.wav
│   └── shimmer.wav
└── openai_voices_YYYYMMDD_HHMMSS.zip
```

### Sending to Manager

After running the script, you'll have:
- **Individual WAV files** in `openai_voice_samples/` folder
- **ZIP archive** in the project root (ready to email/share)

You can:
1. Send the ZIP file via email
2. Upload to cloud storage (Google Drive, Dropbox, etc.)
3. Share the `openai_voice_samples/` folder directly

## Configuration

The test text can be modified in the script:
```python
TEST_TEXT = (
    "Hello! This is a test of OpenAI's Realtime API voice capabilities. "
    "I am an AI English tutor designed to help students improve their English skills. "
    "How can I assist you today?"
)
```

## Requirements

- OpenAI API key configured in `.env` file
- Python packages: `websockets`, `wave` (standard library)

## Notes

- Each voice test takes approximately 5-10 seconds
- Total runtime: ~1-2 minutes for all 6 voices
- Audio files are saved as WAV format (PCM16, 24kHz, mono)
- The script includes error handling and timeout protection

