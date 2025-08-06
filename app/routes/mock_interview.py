from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
import base64
import logging
from app.services.tts import synthesize_speech_exercises
from app.services.feedback import evaluate_response_ex2_stage4
from app.supabase_client import SupabaseProgressTracker
from app.services.stt import transcribe_audio_bytes_eng_only
from app.auth_middleware import get_current_user, require_student
import os

router = APIRouter(tags=["Stage 4 - Exercise 2 (Mock Interview)"])

# Initialize progress tracker
progress_tracker = SupabaseProgressTracker()

# Load interview questions data
def load_interview_questions():
    try:
        with open("app/data/stage4_exercise2.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error loading interview questions: {e}")
        return []

class AudioEvaluationRequest(BaseModel):
    audio_base64: str
    question_id: int
    filename: str
    user_id: str
    time_spent_seconds: int
    urdu_used: bool = False

@router.get(
    "/mock-interview-questions",
    summary="Get all mock interview questions",
    description="Retrieve all available mock interview questions for Stage 4 Exercise 2",
    tags=["Stage 4 - Exercise 2 (Mock Interview)"]
)
async def get_interview_questions(current_user: Dict[str, Any] = Depends(require_student)):
    """Get all mock interview questions"""
    try:
        questions = load_interview_questions()
        return {"questions": questions}
    except Exception as e:
        logging.error(f"Error fetching interview questions: {e}")
        raise HTTPException(status_code=500, detail="Failed to load interview questions")

@router.get(
    "/mock-interview-questions/{question_id}",
    summary="Get specific mock interview question",
    description="Retrieve a specific mock interview question by ID",
    tags=["Stage 4 - Exercise 2 (Mock Interview)"]
)
async def get_interview_question(question_id: int, current_user: Dict[str, Any] = Depends(require_student)):
    """Get a specific mock interview question by ID"""
    try:
        questions = load_interview_questions()
        question = next((q for q in questions if q["id"] == question_id), None)
        
        if not question:
            raise HTTPException(status_code=404, detail="Interview question not found")
        
        print(f"✅ [API] Retrieved question: {question['question']}")
        return question
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error fetching interview question {question_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to load interview question")

@router.post(
    "/mock-interview/{question_id}",
    summary="Generate audio for mock interview question",
    description="Generate audio pronunciation for a specific mock interview question",
    tags=["Stage 4 - Exercise 2 (Mock Interview)"]
)
async def generate_interview_audio(
    question_id: int,
    current_user: Dict[str, Any] = Depends(require_student)
):
    """Generate audio for a specific mock interview question"""
    try:
        questions = load_interview_questions()
        question = next((q for q in questions if q["id"] == question_id), None)
        
        if not question:
            raise HTTPException(status_code=404, detail="Interview question not found")
        
        # Create audio text with context
        audio_text = f"Interview Question: {question['question']}"
        
        print(f"🔄 [API] Generating audio for question: {question['question']}")
        
        # Generate audio using ElevenLabs
        audio_bytes = await synthesize_speech_exercises(audio_text)
        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
        
        print(f"✅ [API] Audio generated successfully for question {question_id}")
        
        return {
            "question_id": question_id,
            "audio_base64": audio_base64,
            "question": question['question']
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error generating audio for question {question_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate audio")

@router.post(
    "/evaluate-mock-interview",
    summary="Evaluate user's mock interview response",
    description="""
This endpoint evaluates the user's recorded audio against the mock interview question requirements.
It performs speech-to-text conversion and provides comprehensive feedback on the response quality.
Also records progress tracking data in Supabase database.
""",
    tags=["Stage 4 - Exercise 2 (Mock Interview)"]
)
async def evaluate_mock_interview(
    request: AudioEvaluationRequest,
    current_user: Dict[str, Any] = Depends(require_student)
):
    """Evaluate user's mock interview response"""
    try:
        print(f"🔄 [API] POST /evaluate-mock-interview endpoint called")
        print(f"📊 [API] Request details: question_id={request.question_id}, user_id={request.user_id}")
        
        # Validate user_id and ensure user can only access their own data
        if not request.user_id:
            raise HTTPException(status_code=400, detail="user_id is required")
        
        if request.user_id != current_user['id']:
            raise HTTPException(status_code=403, detail="You can only access your own data")
        
        # Load question data
        questions = load_interview_questions()
        question_data = next((q for q in questions if q["id"] == request.question_id), None)
        
        if not question_data:
            raise HTTPException(status_code=404, detail="Interview question not found")
        
        print(f"✅ [API] Found question: {question_data['question']}")
        
        # Decode audio
        try:
            audio_bytes = base64.b64decode(request.audio_base64)
            print(f"📊 [API] Audio decoded successfully, size: {len(audio_bytes)} bytes")
        except Exception as e:
            print(f"❌ [API] Audio decoding failed: {e}")
            raise HTTPException(status_code=400, detail="Invalid audio data")
        
        # Transcribe audio
        print("🔄 [API] Transcribing audio...")
        try:
            transcription_result = transcribe_audio_bytes_eng_only(audio_bytes)
            user_text = transcription_result.get("text", "")
            print(f"✅ [API] Transcription result: '{user_text}'")
        except Exception as e:
            print(f"❌ [API] Transcription failed: {e}")
            raise HTTPException(status_code=500, detail="Failed to transcribe audio")
        
        if not user_text.strip():
            raise HTTPException(status_code=400, detail="No speech detected in audio")
        
        # Evaluate response
        print(f"🔄 [API] Evaluating response: '{user_text}' vs expected keywords")
        evaluation = evaluate_response_ex2_stage4(
            user_response=user_text,
            question=question_data['question'],
            expected_keywords=question_data['expected_keywords'],
            vocabulary_focus=question_data['vocabulary_focus'],
            model_response=question_data['model_response']
        )
        
        print(f"✅ [API] Evaluation completed: {evaluation}")
        
        # Record progress
        print(f"🔄 [API] Recording progress for user: {request.user_id}")
        try:
            # Adjust time spent if it's 0
            adjusted_time_spent = max(1, request.time_spent_seconds)
            if request.time_spent_seconds == 0:
                print(f"⚠️ [API] Adjusted time spent from 0 to 1 seconds")
            
            # Record topic attempt
            await progress_tracker.record_topic_attempt(
                user_id=request.user_id,
                stage_id=4,
                exercise_id=2,
                topic_id=request.question_id,
                score=evaluation.get("score", 0),
                urdu_used=request.urdu_used,
                time_spent_seconds=adjusted_time_spent,
                completed=evaluation.get("completed", False)
            )
            
            print(f"✅ [API] Progress recorded successfully")
        except Exception as e:
            print(f"❌ [API] Progress recording failed: {e}")
            # Don't fail the entire request if progress recording fails
        
        # Check for content unlocks
        try:
            unlocked_content = await progress_tracker.check_content_unlocks(request.user_id)
            evaluation["unlocked_content"] = unlocked_content
        except Exception as e:
            print(f"⚠️ [API] Content unlock check failed: {e}")
            evaluation["unlocked_content"] = []
        
        return evaluation
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error evaluating mock interview: {e}")
        raise HTTPException(status_code=500, detail="Failed to evaluate response")

@router.get(
    "/mock-interview-progress/{user_id}",
    summary="Get user's mock interview progress",
    description="Retrieve the user's progress for Stage 4 Exercise 2 (Mock Interview)",
    tags=["Stage 4 - Exercise 2 (Mock Interview)"]
)
async def get_mock_interview_progress(
    user_id: str,
    current_user: Dict[str, Any] = Depends(require_student)
):
    """Get user's mock interview progress"""
    
    # Ensure user can only access their own data
    if user_id != current_user['id']:
        raise HTTPException(status_code=403, detail="You can only access your own data")
    
    try:
        print(f"🔄 [API] GET /mock-interview-progress/{user_id} endpoint called")
        
        progress = await progress_tracker.get_user_topic_progress(
            user_id=user_id,
            stage_id=4,
            exercise_id=2
        )
        
        print(f"✅ [API] Retrieved progress for user: {user_id}")
        return progress
    except Exception as e:
        logging.error(f"Error fetching mock interview progress: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch progress")

@router.get(
    "/mock-interview-current-question/{user_id}",
    summary="Get current mock interview question for user",
    description="Retrieve the current mock interview question the user should practice",
    tags=["Stage 4 - Exercise 2 (Mock Interview)"]
)
async def get_current_mock_interview_question(
    user_id: str,
    current_user: Dict[str, Any] = Depends(require_student)
):
    """Get current mock interview question for user"""
    
    # Ensure user can only access their own data
    if user_id != current_user['id']:
        raise HTTPException(status_code=403, detail="You can only access your own data")
    
    try:
        print(f"🔄 [API] GET /mock-interview-current-question/{user_id} endpoint called")
        
        current_question = await progress_tracker.get_current_topic_for_exercise(
            user_id=user_id,
            stage_id=4,
            exercise_id=2
        )
        
        print(f"✅ [API] Retrieved current question for user: {user_id}")
        return current_question
    except Exception as e:
        logging.error(f"Error fetching current mock interview question: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch current question") 