from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
import base64
import logging
from fastapi.concurrency import run_in_threadpool
from app.services.tts import synthesize_speech_exercises
from app.services.feedback import evaluate_response_ex2_stage4
from app.supabase_client import supabase, progress_tracker
from app.services.stt import transcribe_audio_bytes_eng_only
from app.auth_middleware import get_current_user, require_student, require_admin_or_teacher_or_student
import os

router = APIRouter(tags=["Stage 4 - Exercise 2 (Mock Interview)"])

async def get_question_by_id_from_db(question_id: int):
    """Fetch a mock interview question from Supabase by its topic_number for Stage 4, Exercise 2."""
    print(f"🔍 [DB] Looking for question with topic_number (ID): {question_id} for Stage 4, Exercise 2")
    try:
        # parent_id for Stage 4, Exercise 2 ('Negotiation & Persuasion') is 17, but the content is interview mastery. Let's use 17.
        # The sql file says stage4_exercise2 is "Professional Interview Mastery" which matches the json file.
        # The exercise before it is "Negotiation & Persuasion", which has parent_id 17 according to the base schema.
        # Ah, the user has attached stage4_exercise2_complete_insertions.sql. It uses parent_id 17. So 17 is correct.
        query = supabase.table("ai_tutor_content_hierarchy").select("id, topic_number, title, title_urdu, topic_data, category, difficulty").eq("level", "topic").eq("parent_id", 17).eq("topic_number", question_id).single()
        response = await run_in_threadpool(query.execute)
        
        if response.data:
            db_question = response.data
            topic_data = db_question.get("topic_data", {})
            
            formatted_question = {
                "id": db_question.get("topic_number"),
                "db_id": db_question.get("id"),
                "question": db_question.get("title"),
                "question_urdu": db_question.get("title_urdu"),
                "category": db_question.get("category"),
                "difficulty": db_question.get("difficulty"),
                "speaking_duration": topic_data.get("speaking_duration"),
                "thinking_time": topic_data.get("thinking_time"),
                "expected_structure": topic_data.get("expected_structure"),
                "expected_keywords": topic_data.get("expected_keywords", []),
                "vocabulary_focus": topic_data.get("vocabulary_focus", []),
                "model_response": topic_data.get("model_response"),
                "model_response_urdu": topic_data.get("model_response_urdu"),
                "evaluation_criteria": topic_data.get("evaluation_criteria", {}),
                "learning_objectives": topic_data.get("learning_objectives", [])
            }
            print(f"✅ [DB] Found question: {formatted_question['question']}")
            return formatted_question
        else:
            print(f"❌ [DB] Question with topic_number {question_id} not found for parent_id 17")
            return None
    except Exception as e:
        print(f"❌ [DB] Error fetching question from Supabase: {str(e)}")
        return None


async def check_exercise_completion(user_id: str) -> dict:
    """Check if user has completed the full Mock Interview exercise (Stage 4, Exercise 2)"""
    print(f"🔍 [COMPLETION] Checking exercise completion for user: {user_id}")
    
    try:
        # Get total questions count from Supabase
        total_topics = 0
        try:
            # parent_id for 'Professional Interview Mastery' is 17
            query = supabase.table("ai_tutor_content_hierarchy").select("id", count="exact").eq("level", "topic").eq("parent_id", 17)
            response = await run_in_threadpool(query.execute)
            if response.count is not None:
                total_topics = response.count
                print(f"📊 [COMPLETION] Total questions available from DB: {total_topics}")
            else:
                print("⚠️ [COMPLETION] Could not get count from Supabase, falling back to default.")
                total_topics = 8
        except Exception as e:
            print(f"❌ [COMPLETION] Error getting question count from DB: {str(e)}")
            total_topics = 8 # Default fallback
        
        # Get user's progress for stage 4, exercise 2
        progress_result = await progress_tracker.get_user_topic_progress(
            user_id=user_id,
            stage_id=4,
            exercise_id=2
        )
        
        if not progress_result["success"]:
            print(f"❌ [COMPLETION] Failed to get user progress: {progress_result.get('error')}")
            return {
                "exercise_completed": False,
                "progress_percentage": 0.0,
                "completed_topics": 0,
                "total_topics": total_topics,
                "current_topic_id": 1,
                "stage_id": 4,
                "exercise_id": 2,
                "exercise_name": "Mock Interview",
                "stage_name": "Stage 4 – B2 Upper Intermediate",
                "error": progress_result.get("error", "Failed to get progress")
            }
        
        user_progress = progress_result.get("data", [])
        completed_topics = len([record for record in user_progress if record.get("completed", False)])
        
        # Get current topic ID
        current_topic_result = await progress_tracker.get_current_topic_for_exercise(
            user_id=user_id,
            stage_id=4,
            exercise_id=2
        )
        
        current_topic_id = 1
        if current_topic_result["success"]:
            current_topic_id = current_topic_result.get("current_topic_id", 1)
        
        # Calculate progress percentage
        progress_percentage = (completed_topics / total_topics * 100) if total_topics > 0 else 0.0
        
        # Determine if exercise is truly completed
        # Exercise is completed ONLY when ALL topics are completed
        exercise_completed = completed_topics >= total_topics and completed_topics > 0
        
        print(f"📊 [COMPLETION] Completion status calculated:")
        print(f"   - Total questions: {total_topics}")
        print(f"   - Completed topics: {completed_topics}")
        print(f"   - Current topic ID: {current_topic_id}")
        print(f"   - Progress percentage: {progress_percentage:.1f}%")
        print(f"   - Exercise completed: {exercise_completed}")
        
        # Additional logging for completion logic
        if completed_topics >= total_topics:
            print(f"🎉 [COMPLETION] User has completed all {total_topics} questions!")
        else:
            print(f"📚 [COMPLETION] User still needs to complete {total_topics - completed_topics} more questions")
        
        return {
            "exercise_completed": exercise_completed,
            "progress_percentage": progress_percentage,
            "completed_topics": completed_topics,
            "total_topics": total_topics,
            "current_topic_id": current_topic_id,
            "stage_id": 4,
            "exercise_id": 2,
            "exercise_name": "Mock Interview",
            "stage_name": "Stage 4 – B2 Upper Intermediate"
        }
        
    except Exception as e:
        print(f"❌ [COMPLETION] Error checking exercise completion: {str(e)}")
        return {
            "exercise_completed": False,
            "progress_percentage": 0.0,
            "completed_topics": 0,
            "total_topics": 0,
            "current_topic_id": 1,
            "stage_id": 4,
            "exercise_id": 2,
            "exercise_name": "Mock Interview",
            "stage_name": "Stage 4 – B2 Upper Intermediate",
            "error": str(e)
        }


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
async def get_interview_questions(current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)):
    """Get all mock interview questions from Supabase"""
    try:
        print("🔄 [DB] Fetching all questions for Stage 4, Exercise 2 from Supabase")
        query = supabase.table("ai_tutor_content_hierarchy").select("id, topic_number, title, title_urdu, topic_data, category, difficulty").eq("level", "topic").eq("parent_id", 17).order("topic_number", desc=False)
        response = await run_in_threadpool(query.execute)
        
        if response.data:
            questions = []
            for q in response.data:
                topic_data = q.get("topic_data", {})
                questions.append({
                    "id": q.get("topic_number"),
                    "db_id": q.get("id"),
                    "question": q.get("title"),
                    "question_urdu": q.get("title_urdu"),
                    "category": q.get("category"),
                    "difficulty": q.get("difficulty"),
                    "speaking_duration": topic_data.get("speaking_duration"),
                    "thinking_time": topic_data.get("thinking_time"),
                    "expected_structure": topic_data.get("expected_structure"),
                    "expected_keywords": topic_data.get("expected_keywords", []),
                    "vocabulary_focus": topic_data.get("vocabulary_focus", []),
                    "model_response": topic_data.get("model_response"),
                    "model_response_urdu": topic_data.get("model_response_urdu"),
                    "evaluation_criteria": topic_data.get("evaluation_criteria", {}),
                    "learning_objectives": topic_data.get("learning_objectives", [])
                })
            print(f"✅ [DB] Successfully loaded {len(questions)} questions from Supabase")
            return {"questions": questions}
        else:
            print("❌ [DB] No questions found for Stage 4, Exercise 2")
            return {"questions": []}
    except Exception as e:
        logging.error(f"Error fetching interview questions: {e}")
        raise HTTPException(status_code=500, detail="Failed to load interview questions from database")

@router.get(
    "/mock-interview-questions/{question_id}",
    summary="Get specific mock interview question",
    description="Retrieve a specific mock interview question by ID",
    tags=["Stage 4 - Exercise 2 (Mock Interview)"]
)
async def get_interview_question(question_id: int, current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)):
    """Get a specific mock interview question by ID"""
    try:
        question = await get_question_by_id_from_db(question_id)
        
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
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)
):
    """Generate audio for a specific mock interview question"""
    try:
        question = await get_question_by_id_from_db(question_id)
        
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
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)
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
        question_data = await get_question_by_id_from_db(request.question_id)
        
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
                topic_id=question_data['id'], # Use the actual database ID
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
            unlocked_content_result = await progress_tracker.check_and_unlock_content(request.user_id)
            if unlocked_content_result["success"]:
                evaluation["unlocked_content"] = unlocked_content_result.get("unlocked_content", [])
            else:
                evaluation["unlocked_content"] = []
        except Exception as e:
            print(f"⚠️ [API] Content unlock check failed: {e}")
            evaluation["unlocked_content"] = []
        
        # Check for exercise completion
        try:
            exercise_completion_status = await check_exercise_completion(request.user_id)
            evaluation["exercise_completion_status"] = exercise_completion_status
        except Exception as e:
            print(f"⚠️ [API] Exercise completion check failed: {e}")
            evaluation["exercise_completion_status"] = {
                "exercise_completed": False,
                "progress_percentage": 0.0,
                "completed_topics": 0,
                "total_topics": 0,
                "current_topic_id": 1,
                "stage_id": 4,
                "exercise_id": 2,
                "exercise_name": "Mock Interview",
                "stage_name": "Stage 4 – B2 Upper Intermediate",
                "error": str(e)
            }
        
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
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)
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
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)
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