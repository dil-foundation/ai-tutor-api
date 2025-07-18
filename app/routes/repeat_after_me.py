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
from app.supabase_client import progress_tracker
router = APIRouter()

PHRASES_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'repeat_after_me_phrases.json')

class AudioEvaluationRequest(BaseModel):
    audio_base64: str
    phrase_id: int
    filename: str
    user_id: str
    time_spent_seconds: int
    urdu_used: bool

def get_phrase_by_id(phrase_id: int):
    print(f"🔍 [PHRASE] Looking for phrase with ID: {phrase_id}")
    try:
        with open(PHRASES_FILE, 'r', encoding='utf-8') as f:
            phrases = json.load(f)
            print(f"📖 [PHRASE] Loaded {len(phrases)} phrases from file")
            for phrase in phrases:
                if phrase['id'] == phrase_id:
                    print(f"✅ [PHRASE] Found phrase: {phrase['phrase']}")
                    return phrase['phrase']
            print(f"❌ [PHRASE] Phrase with ID {phrase_id} not found")
            return None
    except Exception as e:
        print(f"❌ [PHRASE] Error reading phrases file: {str(e)}")
        return None


@router.get("/phrases")
async def get_all_phrases():
    """Get all available phrases for Repeat After Me exercise"""
    print("🔄 [API] GET /phrases endpoint called")
    try:
        print(f"📁 [API] Reading phrases file from: {PHRASES_FILE}")
        with open(PHRASES_FILE, 'r', encoding='utf-8') as f:
            phrases = json.load(f)
        print(f"✅ [API] Successfully loaded {len(phrases)} phrases")
        return {"phrases": phrases}
    except Exception as e:
        print(f"❌ [API] Error in get_all_phrases: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to load phrases: {str(e)}")

@router.get("/phrases/{phrase_id}")
async def get_phrase(phrase_id: int):
    """Get a specific phrase by ID"""
    print(f"🔄 [API] GET /phrases/{phrase_id} endpoint called")
    try:
        phrase = get_phrase_by_id(phrase_id)
        if not phrase:
            print(f"❌ [API] Phrase {phrase_id} not found")
            raise HTTPException(status_code=404, detail="Phrase not found")
        print(f"✅ [API] Returning phrase: {phrase}")
        return {"id": phrase_id, "phrase": phrase}
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [API] Error in get_phrase: {str(e)}")
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
    print(f"🔄 [API] POST /repeat-after-me/{phrase_id} endpoint called")
    try:
        phrase = get_phrase_by_id(phrase_id)
        if not phrase:
            print(f"❌ [API] Phrase {phrase_id} not found")
            raise HTTPException(status_code=404, detail="Phrase not found")

        print(f"🎤 [API] Converting phrase to speech: '{phrase}'")
        audio_content = await synthesize_speech_exercises(phrase)
        print(f"✅ [API] Audio content generated, size: {len(audio_content)} bytes")
        
        # Convert to base64 for React Native compatibility
        audio_base64 = base64.b64encode(audio_content).decode('utf-8')
        print(f"✅ [API] Audio converted to base64, length: {len(audio_base64)}")
        
        # Return base64 string directly
        return {"audio_base64": audio_base64}
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [API] Error in repeat_after_me: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post(
    "/evaluate-audio",
    summary="Evaluate user's audio recording against expected phrase",
    description="""
This endpoint evaluates the user's recorded audio against the expected phrase.
It performs speech-to-text conversion and provides pronunciation feedback.
Also records progress tracking data in Supabase database.
""",
    tags=["Stage 1 - Exercise 1 (Repeat After Me)"]
)
async def evaluate_audio(request: AudioEvaluationRequest):
    print(f"🔄 [API] POST /evaluate-audio endpoint called")
    print(f"📝 [API] Request details: phrase_id={request.phrase_id}, filename={request.filename}")
    print(f"📊 [API] Audio data length: {len(request.audio_base64)} characters")
    print(f"👤 [API] User ID: {request.user_id}")
    print(f"⏱️ [API] Time spent: {request.time_spent_seconds} seconds")
    print(f"🌐 [API] Urdu used: {request.urdu_used}")
    
    try:
        # Get the expected phrase
        expected_phrase = get_phrase_by_id(request.phrase_id)
        if not expected_phrase:
            print(f"❌ [API] Phrase {request.phrase_id} not found")
            raise HTTPException(status_code=404, detail="Phrase not found")

        print(f"✅ [API] Expected phrase: '{expected_phrase}'")

        # Decode base64 audio
        try:
            print("🔄 [API] Decoding base64 audio...")
            audio_bytes = base64.b64decode(request.audio_base64)
            print(f"✅ [API] Audio decoded, size: {len(audio_bytes)} bytes")
        except Exception as e:
            print(f"❌ [API] Error decoding base64 audio: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid audio data")

        # Check if audio is too short (silence detection)
        if len(audio_bytes) < 1000:  # Less than 1KB indicates very short/silent audio
            print(f"⚠️ [API] Audio too short ({len(audio_bytes)} bytes), likely silent")
            return {
                "success": False,
                "error": "no_speech_detected",
                "message": "No speech detected. Please try again.",
                "expected_phrase": expected_phrase
            }

        # Transcribe the audio
        try:
            print("🔄 [API] Transcribing audio...")
            transcription_result = transcribe_audio_bytes_eng(audio_bytes)
            user_text = transcription_result.get("text", "").strip()
            print(f"✅ [API] Transcription result: '{user_text}'")
            
            # Check if transcription is empty or too short
            if not user_text or len(user_text) < 2:
                print(f"⚠️ [API] Transcription too short or empty: '{user_text}'")
                return {
                    "success": False,
                    "error": "no_speech_detected",
                    "message": "No clear speech detected. Please speak more clearly.",
                    "expected_phrase": expected_phrase
                }

        except Exception as e:
            print(f"❌ [API] Error transcribing audio: {str(e)}")
            return {
                "success": False,
                "error": "transcription_failed",
                "message": "Failed to process audio. Please try again.",
                "expected_phrase": expected_phrase
            }

        # Evaluate the response
        try:
            print(f"🔄 [API] Evaluating response: '{user_text}' vs '{expected_phrase}'")
            evaluation = evaluate_response_ex1_stage1(expected_phrase, user_text)
            print(f"✅ [API] Evaluation completed: {evaluation}")
            
            # Extract evaluation details for progress tracking
            score = evaluation.get("score", 0)
            is_correct = evaluation.get("is_correct", False)
            completed = evaluation.get("completed", False)
            
            print(f"📊 [API] Evaluation details: score={score}, is_correct={is_correct}, completed={completed}")
            
            # Validate evaluation data
            if not isinstance(score, (int, float)) or score < 0 or score > 100:
                print(f"⚠️ [API] Invalid score value: {score}, using default")
                score = 50
                is_correct = False
                completed = False
            
            # Record progress in Supabase database
            progress_recorded = False
            unlocked_content = []
            
            if request.user_id and request.user_id.strip():
                print(f"🔄 [API] Recording progress for user: {request.user_id}")
                try:
                    # Validate time spent (should be reasonable)
                    time_spent = max(1, min(request.time_spent_seconds, 300))  # Between 1-300 seconds
                    if time_spent != request.time_spent_seconds:
                        print(f"⚠️ [API] Adjusted time spent from {request.time_spent_seconds} to {time_spent} seconds")
                    
                    # Record the topic attempt
                    progress_result = await progress_tracker.record_topic_attempt(
                        user_id=request.user_id,
                        stage_id=1,  # Stage 1
                        exercise_id=1,  # Exercise 1 (Repeat After Me)
                        topic_id=request.phrase_id,
                        score=float(score),
                        urdu_used=request.urdu_used,
                        time_spent_seconds=time_spent,
                        completed=completed
                    )
                    
                    if progress_result["success"]:
                        print(f"✅ [API] Progress recorded successfully")
                        progress_recorded = True
                        
                        # Check for unlocked content
                        unlock_result = await progress_tracker.check_and_unlock_content(request.user_id)
                        if unlock_result["success"]:
                            unlocked_content = unlock_result.get("unlocked_content", [])
                            if unlocked_content:
                                print(f"🎉 [API] Unlocked content: {unlocked_content}")
                    else:
                        print(f"❌ [API] Failed to record progress: {progress_result.get('error')}")
                        
                except Exception as e:
                    print(f"❌ [API] Error recording progress: {str(e)}")
                    print(f"❌ [API] Progress tracking error details: {type(e).__name__}: {str(e)}")
                    # Don't fail the entire request if progress tracking fails
            else:
                print(f"⚠️ [API] No valid user ID provided, skipping progress tracking")
            
            return {
                "success": True,
                "expected_phrase": expected_phrase,
                "user_text": user_text,
                "evaluation": evaluation,
                "progress_recorded": progress_recorded,
                "unlocked_content": unlocked_content
            }

        except Exception as e:
            print(f"❌ [API] Error evaluating response: {str(e)}")
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
        print(f"❌ [API] Unexpected error in evaluate_audio: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
