from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
import os
import base64
from io import BytesIO
from app.services.tts import synthesize_speech,synthesize_speech_exercises
from app.services.stt import transcribe_audio_bytes_eng
from app.services.feedback import evaluate_response_ex1_stage1
router = APIRouter()

PHRASES_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'repeat_after_me_phrases.json')

class AudioEvaluationRequest(BaseModel):
    audio_base64: str
    phrase_id: int
    filename: str

def get_phrase_by_id(phrase_id: int):
    print(f"🔍 Looking for phrase with ID: {phrase_id}")
    try:
        with open(PHRASES_FILE, 'r', encoding='utf-8') as f:
            phrases = json.load(f)
            print(f"📖 Loaded {len(phrases)} phrases from file")
            for phrase in phrases:
                if phrase['id'] == phrase_id:
                    print(f"✅ Found phrase: {phrase['phrase']}")
                    return phrase['phrase']
            print(f"❌ Phrase with ID {phrase_id} not found")
            return None
    except Exception as e:
        print(f"❌ Error reading phrases file: {str(e)}")
        return None


@router.get("/phrases")
async def get_all_phrases():
    """Get all available phrases for Repeat After Me exercise"""
    print("🔄 GET /phrases endpoint called")
    try:
        print(f"📁 Reading phrases file from: {PHRASES_FILE}")
        with open(PHRASES_FILE, 'r', encoding='utf-8') as f:
            phrases = json.load(f)
        print(f"✅ Successfully loaded {len(phrases)} phrases")
        return {"phrases": phrases}
    except Exception as e:
        print(f"❌ Error in get_all_phrases: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to load phrases: {str(e)}")

@router.get("/phrases/{phrase_id}")
async def get_phrase(phrase_id: int):
    """Get a specific phrase by ID"""
    print(f"🔄 GET /phrases/{phrase_id} endpoint called")
    try:
        phrase = get_phrase_by_id(phrase_id)
        if not phrase:
            print(f"❌ Phrase {phrase_id} not found")
            raise HTTPException(status_code=404, detail="Phrase not found")
        print(f"✅ Returning phrase: {phrase}")
        return {"id": phrase_id, "phrase": phrase}
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in get_phrase: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post(
    "/repeat-after-me/{phrase_id}",
    summary="Convert phrase to audio for Repeat After Me Exercise",
    description="""
This endpoint is part of Stage 1 - Exercise 1 (Repeat After Me). 
It takes a phrase ID from a predefined list, converts the corresponding sentence into speech (TTS),
and returns the generated audio file as the response.
""",
    tags=["Stage 1 - Exercise 1 (Repeat After Me)"]
)
async def repeat_after_me(phrase_id: int):
    print(f"🔄 POST /repeat-after-me/{phrase_id} endpoint called")
    try:
        phrase = get_phrase_by_id(phrase_id)
        if not phrase:
            print(f"❌ Phrase {phrase_id} not found")
            raise HTTPException(status_code=404, detail="Phrase not found")

        print(f"🎤 Converting phrase to speech: '{phrase}'")
        audio_content = await synthesize_speech_exercises(phrase)
        print(f"✅ Audio content generated, size: {len(audio_content)} bytes")
        
        # Convert to base64 for React Native compatibility
        audio_base64 = base64.b64encode(audio_content).decode('utf-8')
        print(f"✅ Audio converted to base64, length: {len(audio_base64)}")
        
        # Return base64 string directly
        return {"audio_base64": audio_base64}
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in repeat_after_me: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post(
    "/evaluate-audio",
    summary="Evaluate user's audio recording against expected phrase",
    description="""
This endpoint evaluates the user's recorded audio against the expected phrase.
It performs speech-to-text conversion and provides pronunciation feedback.
""",
    tags=["Stage 1 - Exercise 1 (Repeat After Me)"]
)
async def evaluate_audio(request: AudioEvaluationRequest):
    print(f"🔄 POST /evaluate-audio endpoint called")
    print(f"📝 Request details: phrase_id={request.phrase_id}, filename={request.filename}")
    print(f"📊 Audio data length: {len(request.audio_base64)} characters")
    
    try:
        # Get the expected phrase
        expected_phrase = get_phrase_by_id(request.phrase_id)
        if not expected_phrase:
            print(f"❌ Phrase {request.phrase_id} not found")
            raise HTTPException(status_code=404, detail="Phrase not found")

        print(f"✅ Expected phrase: '{expected_phrase}'")

        # Decode base64 audio
        try:
            print("🔄 Decoding base64 audio...")
            audio_bytes = base64.b64decode(request.audio_base64)
            print(f"✅ Audio decoded, size: {len(audio_bytes)} bytes")
        except Exception as e:
            print(f"❌ Error decoding base64 audio: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid audio data")

        # Check if audio is too short (silence detection)
        if len(audio_bytes) < 1000:  # Less than 1KB indicates very short/silent audio
            print(f"⚠️ Audio too short ({len(audio_bytes)} bytes), likely silent")
            return {
                "success": False,
                "error": "no_speech_detected",
                "message": "No speech detected. Please try again.",
                "expected_phrase": expected_phrase
            }

        # Transcribe the audio
        try:
            print("🔄 Transcribing audio...")
            transcription_result = transcribe_audio_bytes_eng(audio_bytes)
            user_text = transcription_result.get("text", "").strip()
            print(f"✅ Transcription result: '{user_text}'")
            
            # Check if transcription is empty or too short
            if not user_text or len(user_text) < 2:
                print(f"⚠️ Transcription too short or empty: '{user_text}'")
                return {
                    "success": False,
                    "error": "no_speech_detected",
                    "message": "No clear speech detected. Please speak more clearly.",
                    "expected_phrase": expected_phrase
                }

        except Exception as e:
            print(f"❌ Error transcribing audio: {str(e)}")
            return {
                "success": False,
                "error": "transcription_failed",
                "message": "Failed to process audio. Please try again.",
                "expected_phrase": expected_phrase
            }

        # Evaluate the response
        try:
            print(f"🔄 Evaluating response: '{user_text}' vs '{expected_phrase}'")
            evaluation = evaluate_response_ex1_stage1(expected_phrase, user_text)
            print(f"✅ Evaluation completed: {evaluation}")
            
            return {
                "success": True,
                "expected_phrase": expected_phrase,
                "user_text": user_text,
                "evaluation": evaluation
            }

        except Exception as e:
            print(f"❌ Error evaluating response: {str(e)}")
            return {
                "success": False,
                "error": "evaluation_failed",
                "message": "Failed to evaluate pronunciation. Please try again.",
                "expected_phrase": expected_phrase,
                "user_text": user_text
            }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Unexpected error in evaluate_audio: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
