from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
import os
import base64
from io import BytesIO
from typing import Dict, Any
from app.services.tts import synthesize_speech, synthesize_speech_exercises
from app.services.stt import transcribe_audio_bytes_eng_only
from app.services.feedback import evaluate_response_ex1_stage2
from app.supabase_client import progress_tracker
from app.auth_middleware import get_current_user, require_student,require_admin_or_teacher_or_student
router = APIRouter()

DAILY_ROUTINE_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'daily_routine_narration.json')

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
        with open(DAILY_ROUTINE_FILE, 'r', encoding='utf-8') as f:
            phrases = json.load(f)
            print(f"📖 [PHRASE] Loaded {len(phrases)} phrases from file")
            for phrase in phrases:
                if phrase['id'] == phrase_id:
                    print(f"✅ [PHRASE] Found phrase: {phrase['phrase']}")
                    return phrase  # Return the full phrase object
            print(f"❌ [PHRASE] Phrase with ID {phrase_id} not found")
            return None
    except Exception as e:
        print(f"❌ [PHRASE] Error reading phrase file: {str(e)}")
        return None


@router.get("/daily-routine-phrases")
async def get_all_phrases(current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)):
    """Get all available phrases for Daily Routine exercise"""
    print("🔄 [API] GET /daily-routine-phrases endpoint called")
    try:
        print(f"📁 [API] Reading phrase file from: {DAILY_ROUTINE_FILE}")
        with open(DAILY_ROUTINE_FILE, 'r', encoding='utf-8') as f:
            phrases = json.load(f)
        print(f"✅ [API] Successfully loaded {len(phrases)} phrases")
        return {"phrases": phrases}
    except Exception as e:
        print(f"❌ [API] Error in get_all_phrases: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to load phrases: {str(e)}")

@router.get("/daily-routine-phrases/{phrase_id}")
async def get_phrase(phrase_id: int, current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)):
    """Get a specific phrase by ID"""
    print(f"🔄 [API] GET /daily-routine-phrases/{phrase_id} endpoint called")
    try:
        phrase_data = get_phrase_by_id(phrase_id)
        if not phrase_data:
            print(f"❌ [API] Phrase {phrase_id} not found")
            raise HTTPException(status_code=404, detail="Phrase not found")
        print(f"✅ [API] Returning phrase: {phrase_data['phrase']}")
        return {
            "id": phrase_data['id'], 
            "phrase": phrase_data['phrase'],
            "phrase_urdu": phrase_data['phrase_urdu'],
            "example": phrase_data['example'],
            "example_urdu": phrase_data['example_urdu'],
            "keywords": phrase_data['keywords'],
            "keywords_urdu": phrase_data['keywords_urdu'],
            "category": phrase_data['category'],
            "difficulty": phrase_data['difficulty'],
            "tense_focus": phrase_data['tense_focus'],
            "sentence_structure": phrase_data['sentence_structure']
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [API] Error in get_phrase: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post(
    "/daily-routine/{phrase_id}",
    summary="Convert phrase to audio for Daily Routine Exercise",
    description="""
This endpoint is part of Stage 2 - Exercise 1 (Daily Routine). 
It takes a phrase ID from a predefined list, converts the corresponding phrase into speech (TTS),
and returns the generated audio file as the response.
""",
    tags=["Stage 2 - Exercise 1 (Daily Routine)"]
)
async def daily_routine(phrase_id: int, current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)):
    print(f"🔄 [API] POST /daily-routine/{phrase_id} endpoint called")
    try:
        phrase_data = get_phrase_by_id(phrase_id)
        if not phrase_data:
            print(f"❌ [API] Phrase {phrase_id} not found")
            raise HTTPException(status_code=404, detail="Phrase not found")

        phrase_text = phrase_data['phrase']
        print(f"🎤 [API] Converting phrase to speech: '{phrase_text}'")
        audio_content = await synthesize_speech_exercises(phrase_text)
        print(f"✅ [API] Audio content generated, size: {len(audio_content)} bytes")
        
        # Convert to base64 for React Native compatibility
        audio_base64 = base64.b64encode(audio_content).decode('utf-8')
        print(f"✅ [API] Audio converted to base64, length: {len(audio_base64)}")
        
        # Return base64 string directly
        return {"audio_base64": audio_base64}
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [API] Error in daily_routine: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post(
    "/evaluate-daily-routine",
    summary="Evaluate user's audio recording against expected keywords",
    description="""
This endpoint evaluates the user's recorded audio against the expected keywords for daily routine phrases.
It performs speech-to-text conversion and provides feedback on the response quality.
Also records progress tracking data in Supabase database.
""",
    tags=["Stage 2 - Exercise 1 (Daily Routine)"]
)
async def evaluate_daily_routine(
    request: AudioEvaluationRequest,
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)
):
    print(f"🔄 [API] POST /evaluate-daily-routine endpoint called")
    print(f"📝 [API] Request details: phrase_id={request.phrase_id}, filename={request.filename}")
    print(f"📊 [API] Audio data length: {len(request.audio_base64)} characters")
    print(f"👤 [API] User ID: {request.user_id}")
    print(f"⏱️ [API] Time spent: {request.time_spent_seconds} seconds")
    print(f"🌐 [API] Urdu used: {request.urdu_used}")
    
    # Validate user_id and ensure user can only access their own data
    if not request.user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    
    if request.user_id != current_user['id']:
        raise HTTPException(status_code=403, detail="You can only access your own data")
    
    try:
        # Get the expected phrase and keywords
        phrase_data = get_phrase_by_id(request.phrase_id)
        if not phrase_data:
            print(f"❌ [API] Phrase {request.phrase_id} not found")
            raise HTTPException(status_code=404, detail="Phrase not found")

        expected_keywords = phrase_data['keywords']
        phrase_text = phrase_data['phrase']
        example_text = phrase_data['example']
        print(f"✅ [API] Expected keywords: {expected_keywords}")
        print(f"✅ [API] Phrase: '{phrase_text}'")
        print(f"✅ [API] Example: '{example_text}'")

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
                "expected_keywords": expected_keywords,
                "phrase": phrase_text
            }

        # Transcribe the audio
        try:
            print("🔄 [API] Transcribing audio...")
            transcription_result = transcribe_audio_bytes_eng_only(audio_bytes)
            user_text = transcription_result.get("text", "").strip()
            print(f"✅ [API] Transcription result: '{user_text}'")
            
            # Check if transcription is empty or too short
            if not user_text or len(user_text) < 2:
                print(f"⚠️ [API] Transcription too short or empty: '{user_text}'")
                return {
                    "success": False,
                    "error": "no_speech_detected",
                    "message": "No clear speech detected. Please speak more clearly.",
                    "expected_keywords": expected_keywords,
                    "phrase": phrase_text
                }

        except Exception as e:
            print(f"❌ [API] Error transcribing audio: {str(e)}")
            return {
                "success": False,
                "error": "transcription_failed",
                "message": "Failed to process audio. Please try again.",
                "expected_keywords": expected_keywords,
                "phrase": phrase_text
            }

        # Evaluate the response
        try:
            print(f"🔄 [API] Evaluating response: '{user_text}' vs expected keywords: {expected_keywords}")
            evaluation = evaluate_response_ex1_stage2(expected_keywords, user_text, phrase_text, example_text)
            print(f"✅ [API] Evaluation completed: {evaluation}")
            
            # Extract evaluation details for progress tracking
            score = evaluation.get("score", 0)
            is_correct = evaluation.get("is_correct", False)
            completed = evaluation.get("completed", False)
            suggested_improvement = evaluation.get("suggested_improvement", "")
            keyword_matches = evaluation.get("keyword_matches", 0)
            total_keywords = evaluation.get("total_keywords", len(expected_keywords))
            fluency_score = evaluation.get("fluency_score", 0)
            grammar_score = evaluation.get("grammar_score", 0)
            
            print(f"📊 [API] Evaluation details: score={score}, is_correct={is_correct}, completed={completed}")
            print(f"📊 [API] Keyword matches: {keyword_matches}/{total_keywords}")
            print(f"📊 [API] Fluency score: {fluency_score}, Grammar score: {grammar_score}")
            
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
                        stage_id=2,  # Stage 2
                        exercise_id=1,  # Exercise 1 (Daily Routine)
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
                "phrase": phrase_text,
                "expected_keywords": expected_keywords,
                "user_text": user_text,
                "evaluation": evaluation,
                "suggested_improvement": suggested_improvement,
                "progress_recorded": progress_recorded,
                "unlocked_content": unlocked_content,
                "keyword_matches": keyword_matches,
                "total_keywords": total_keywords,
                "fluency_score": fluency_score,
                "grammar_score": grammar_score
            }

        except Exception as e:
            print(f"❌ [API] Error evaluating response: {str(e)}")
            return {
                "success": False,
                "error": "evaluation_failed",
                "message": "Failed to evaluate response. Please try again.",
                "expected_keywords": expected_keywords,
                "phrase": phrase_text,
                "user_text": user_text
            }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [API] Unexpected error in evaluate_daily_routine: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}") 