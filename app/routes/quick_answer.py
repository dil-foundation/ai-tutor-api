from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
import os
from fastapi.concurrency import run_in_threadpool
from app.services.tts import synthesize_speech_exercises
from app.services.stt import transcribe_audio_bytes_eng_only
from app.services.feedback import evaluate_response_ex2_stage2
from app.supabase_client import supabase, progress_tracker
from app.auth_middleware import get_current_user, require_student, require_admin_or_teacher_or_student
import base64

router = APIRouter(tags=["quick-answer"])

async def get_question_by_id_internal(question_id: int):
    """Internal function to fetch and format a question from Supabase."""
    print(f"🔍 [DB] Looking for question with topic_number (ID): {question_id} for Stage 2, Exercise 2")
    try:
        # parent_id for Stage 2, Exercise 2 ('Question Answer Chat Practice') is 11.
        query = supabase.table("ai_tutor_content_hierarchy").select("id, topic_number, title, title_urdu, topic_data, category, difficulty").eq("level", "topic").eq("parent_id", 11).eq("topic_number", question_id).single()
        response = await run_in_threadpool(query.execute)
        
        if response.data:
            db_question = response.data
            topic_data = db_question.get("topic_data", {})
            
            formatted_question = {
                "id": db_question.get("topic_number"),
                "db_id": db_question.get("id"),
                "question": db_question.get("title"),
                "question_urdu": db_question.get("title_urdu"),
                "expected_answers": topic_data.get("expected_answers", []),
                "expected_answers_urdu": topic_data.get("expected_answers_urdu", []),
                "keywords": topic_data.get("keywords", []),
                "keywords_urdu": topic_data.get("keywords_urdu", []),
                "category": db_question.get("category"),
                "difficulty": db_question.get("difficulty"),
                "tense": topic_data.get("tense"),
                "sentence_structure": topic_data.get("sentence_structure")
            }
            print(f"✅ [DB] Found question: {formatted_question['question']}")
            return formatted_question
        else:
            print(f"❌ [DB] Question with topic_number {question_id} not found for parent_id 11")
            return None
    except Exception as e:
        print(f"❌ [DB] Error fetching question from Supabase: {str(e)}")
        return None

async def check_exercise_completion(user_id: str) -> dict:
    """Check if user has completed the full Quick Answer exercise (Stage 2, Exercise 2)"""
    print(f"🔍 [COMPLETION] Checking exercise completion for user: {user_id}")
    
    try:
        # Get total questions count from Supabase
        total_topics = 0
        try:
            query = supabase.table("ai_tutor_content_hierarchy").select("id", count="exact").eq("level", "topic").eq("parent_id", 11)
            response = await run_in_threadpool(query.execute)
            if response.count is not None:
                total_topics = response.count
                print(f"📊 [COMPLETION] Total questions available from DB: {total_topics}")
            else:
                print("⚠️ [COMPLETION] Could not get count from Supabase, falling back to default.")
                total_topics = 15
        except Exception as e:
            print(f"❌ [COMPLETION] Error getting question count from DB: {str(e)}")
            total_topics = 15 # Fallback
        
        # Get user's progress for stage 2, exercise 2
        progress_result = await progress_tracker.get_user_topic_progress(
            user_id=user_id,
            stage_id=2,
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
                "stage_id": 2,
                "exercise_id": 2,
                "exercise_name": "Quick Answer",
                "stage_name": "Stage 2 – A2 Elementary",
                "error": progress_result.get("error", "Failed to get progress")
            }
        
        user_progress = progress_result.get("data", [])
        completed_topics = len([record for record in user_progress if record.get("completed", False)])
        
        # Get current topic ID
        current_topic_result = await progress_tracker.get_current_topic_for_exercise(
            user_id=user_id,
            stage_id=2,
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
            "stage_id": 2,
            "exercise_id": 2,
            "exercise_name": "Quick Answer",
            "stage_name": "Stage 2 – A2 Elementary"
        }
        
    except Exception as e:
        print(f"❌ [COMPLETION] Error checking exercise completion: {str(e)}")
        return {
            "exercise_completed": False,
            "progress_percentage": 0.0,
            "completed_topics": 0,
            "total_topics": 0,
            "current_topic_id": 1,
            "stage_id": 2,
            "exercise_id": 2,
            "exercise_name": "Quick Answer",
            "stage_name": "Stage 2 – A2 Elementary",
            "error": str(e)
        }

class AudioEvaluationRequest(BaseModel):
    audio_base64: str
    question_id: int
    filename: str
    user_id: str
    time_spent_seconds: int
    urdu_used: bool

class QuestionResponse(BaseModel):
    id: int
    question: str
    question_urdu: str
    expected_answers: List[str]
    expected_answers_urdu: List[str]
    keywords: List[str]
    keywords_urdu: List[str]
    category: str
    difficulty: str
    tense: str
    sentence_structure: str

@router.get("/quick-answer-questions")
async def get_all_questions(current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)):
    """Get all quick answer questions"""
    try:
        print("🔄 [DB] Fetching all questions for Stage 2, Exercise 2 from Supabase")
        query = supabase.table("ai_tutor_content_hierarchy").select("id, topic_number, title, title_urdu, topic_data, category, difficulty").eq("level", "topic").eq("parent_id", 11).order("topic_number", desc=False)
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
                    "expected_answers": topic_data.get("expected_answers", []),
                    "expected_answers_urdu": topic_data.get("expected_answers_urdu", []),
                    "keywords": topic_data.get("keywords", []),
                    "keywords_urdu": topic_data.get("keywords_urdu", []),
                    "category": q.get("category"),
                    "difficulty": q.get("difficulty"),
                    "tense": topic_data.get("tense"),
                    "sentence_structure": topic_data.get("sentence_structure")
                })
            print(f"✅ [DB] Successfully loaded {len(questions)} questions from Supabase")
            return {"questions": questions}
        else:
            print("❌ [DB] No questions found for Stage 2, Exercise 2")
            return {"questions": []}
    except Exception as e:
        print(f"❌ [QUICK_ANSWER] Error getting questions: {e}")
        raise HTTPException(status_code=500, detail="Failed to load questions from database")

@router.get("/quick-answer-questions/{question_id}")
async def get_question_by_id(question_id: int, current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)):
    """Get a specific question by ID"""
    try:
        question = await get_question_by_id_internal(question_id)
        
        if not question:
            print(f"❌ [QUICK_ANSWER] Question {question_id} not found")
            raise HTTPException(status_code=404, detail="Question not found")
        
        print(f"✅ [QUICK_ANSWER] Found question {question_id}: {question['question']}")
        return question
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [QUICK_ANSWER] Error getting question {question_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get question")

@router.post("/quick-answer/{question_id}")
async def generate_question_audio(question_id: int, current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)):
    """Generate TTS audio for a specific question"""
    try:
        question = await get_question_by_id_internal(question_id)
        
        if not question:
            print(f"❌ [QUICK_ANSWER] Question {question_id} not found for TTS")
            raise HTTPException(status_code=404, detail="Question not found")
        
        print(f"🔄 [QUICK_ANSWER] Generating TTS for question {question_id}")
        
        # Generate TTS audio for the question
        audio_content = await synthesize_speech_exercises(question["question"])
        
        if not audio_content:
            print(f"❌ [QUICK_ANSWER] Failed to generate TTS for question {question_id}")
            raise HTTPException(status_code=500, detail="Failed to generate audio")
        
        print(f"✅ [QUICK_ANSWER] Audio content generated, size: {len(audio_content)} bytes")
        
        # Convert to base64 for React Native compatibility
        audio_base64 = base64.b64encode(audio_content).decode('utf-8')
        print(f"✅ [QUICK_ANSWER] Audio converted to base64, length: {len(audio_base64)}")
        
        # Return base64 string directly
        return {"audio_base64": audio_base64}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [QUICK_ANSWER] Error generating TTS for question {question_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate audio")

@router.post("/evaluate-quick-answer")
async def evaluate_quick_answer_audio(
    request: AudioEvaluationRequest,
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)
):
    """Evaluate user's audio recording for quick answer exercise"""
    print(f"🔄 [QUICK_ANSWER] POST /evaluate-quick-answer called")
    print(f"📝 [QUICK_ANSWER] Request details: question_id={request.question_id}, filename={request.filename}")
    print(f"👤 [QUICK_ANSWER] User ID: {request.user_id}")
    
    # Validate user_id and ensure user can only access their own data
    if not request.user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    
    if request.user_id != current_user['id']:
        raise HTTPException(status_code=403, detail="You can only access your own data")
    
    try:
        # Get the question data
        question = await get_question_by_id_internal(request.question_id)
        
        if not question:
            print(f"❌ [QUICK_ANSWER] Question {request.question_id} not found")
            raise HTTPException(status_code=404, detail="Question not found")
        
        expected_answers = question['expected_answers']
        expected_answers_urdu = question['expected_answers_urdu']
        keywords = question['keywords']
        keywords_urdu = question['keywords_urdu']
        question_text = question['question']
        
        print(f"✅ [QUICK_ANSWER] Question: '{question_text}'")
        print(f"✅ [QUICK_ANSWER] Expected answers: {expected_answers}")
        print(f"✅ [QUICK_ANSWER] Keywords: {keywords}")

        # Decode base64 audio
        try:
            print("🔄 [QUICK_ANSWER] Decoding base64 audio...")
            audio_bytes = base64.b64decode(request.audio_base64)
            print(f"✅ [QUICK_ANSWER] Audio decoded, size: {len(audio_bytes)} bytes")
        except Exception as e:
            print(f"❌ [QUICK_ANSWER] Error decoding base64 audio: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid audio data")

        # Check if audio is too short (silence detection)
        if len(audio_bytes) < 1000:  # Less than 1KB indicates very short/silent audio
            print(f"⚠️ [QUICK_ANSWER] Audio too short ({len(audio_bytes)} bytes), likely silent")
            return {
                "success": False,
                "error": "no_speech_detected",
                "message": "No speech detected. Please try again.",
                "expected_answers": expected_answers
            }

        # Transcribe the audio
        try:
            print("🔄 [QUICK_ANSWER] Transcribing audio...")
            transcription_result = transcribe_audio_bytes_eng_only(audio_bytes)
            user_text = transcription_result.get("text", "").strip()
            print(f"✅ [QUICK_ANSWER] Transcription result: '{user_text}'")
            
            # Check if transcription is empty or too short
            if not user_text or len(user_text) < 2:
                print(f"⚠️ [QUICK_ANSWER] Transcription too short or empty: '{user_text}'")
                return {
                    "success": False,
                    "error": "no_speech_detected",
                    "message": "No clear speech detected. Please speak more clearly.",
                    "expected_answers": expected_answers
                }

        except Exception as e:
            print(f"❌ [QUICK_ANSWER] Error transcribing audio: {str(e)}")
            return {
                "success": False,
                "question": question["question"],
                "expected_answers": question["expected_answers"],
                "error": "no_speech_detected",
                "message": "No clear speech detected. Please speak more clearly.",
                "progress_recorded": False
            }
        
        # Evaluate response
        print(f"🔄 [QUICK_ANSWER] Evaluating response...")
        evaluation = evaluate_response_ex2_stage2(
            expected_answers=question["expected_answers"],
            user_response=user_text,
            question=question["question"],
            question_urdu=question["question_urdu"]
        )
        
        print(f"✅ [QUICK_ANSWER] Evaluation completed: {evaluation}")
        
        # Record progress
        try:
            print(f"🔄 [QUICK_ANSWER] Recording progress for user {request.user_id}")
            progress_result = await progress_tracker.record_topic_attempt(
                user_id=request.user_id,
                stage_id=2,  # Stage 2
                exercise_id=2,  # Exercise 2 (Quick Answer)
                topic_id=question['db_id'], # Use the actual database ID
                score=evaluation.get("score", 0),
                urdu_used=request.urdu_used,
                time_spent_seconds=request.time_spent_seconds,
                completed=evaluation.get("completed", False)
            )
            
            if progress_result.get("success"):
                print(f"✅ [QUICK_ANSWER] Progress recorded successfully")
                
                # Check for unlocked content
                unlock_result = await progress_tracker.check_and_unlock_content(request.user_id)
                unlocked_content = unlock_result.get("unlocked_content", []) if unlock_result.get("success") else []
                
                # Check exercise completion status
                exercise_completion_status = None
                try:
                    exercise_completion_status = await check_exercise_completion(request.user_id)
                    print(f"📊 [QUICK_ANSWER] Exercise completion status: {exercise_completion_status}")
                except Exception as completion_error:
                    print(f"⚠️ [QUICK_ANSWER] Failed to check exercise completion: {str(completion_error)}")
                    exercise_completion_status = {
                        "exercise_completed": False,
                        "progress_percentage": 0.0,
                        "completed_topics": 0,
                        "total_topics": 0,
                        "current_topic_id": 1,
                        "stage_id": 2,
                        "exercise_id": 2,
                        "exercise_name": "Quick Answer",
                        "stage_name": "Stage 2 – A2 Elementary",
                        "error": str(completion_error)
                    }
                
                return {
                    "success": True,
                    "question": question["question"],
                    "expected_answers": question["expected_answers"],
                    "user_text": user_text,
                    "evaluation": evaluation,
                    "progress_recorded": True,
                    "unlocked_content": unlocked_content,
                    "answer_accuracy": evaluation.get("answer_accuracy", 0),
                    "grammar_score": evaluation.get("grammar_score", 0),
                    "fluency_score": evaluation.get("fluency_score", 0),
                    "exercise_completion": exercise_completion_status
                }
            else:
                print(f"⚠️ [QUICK_ANSWER] Progress recording failed: {progress_result.get('error')}")
                # Check exercise completion status even when progress recording fails
                exercise_completion_status = None
                try:
                    exercise_completion_status = await check_exercise_completion(request.user_id)
                except Exception as completion_error:
                    print(f"⚠️ [QUICK_ANSWER] Failed to check exercise completion: {str(completion_error)}")
                    exercise_completion_status = {
                        "exercise_completed": False,
                        "progress_percentage": 0.0,
                        "completed_topics": 0,
                        "total_topics": 0,
                        "current_topic_id": 1,
                        "stage_id": 2,
                        "exercise_id": 2,
                        "exercise_name": "Quick Answer",
                        "stage_name": "Stage 2 – A2 Elementary",
                        "error": str(completion_error)
                    }
                
                return {
                    "success": True,
                    "question": question["question"],
                    "expected_answers": question["expected_answers"],
                    "user_text": user_text,
                    "evaluation": evaluation,
                    "progress_recorded": False,
                    "answer_accuracy": evaluation.get("answer_accuracy", 0),
                    "grammar_score": evaluation.get("grammar_score", 0),
                    "fluency_score": evaluation.get("fluency_score", 0),
                    "exercise_completion": exercise_completion_status
                }
                
        except Exception as e:
            print(f"❌ [QUICK_ANSWER] Error recording progress: {e}")
            # Check exercise completion status even when progress recording fails
            exercise_completion_status = None
            try:
                exercise_completion_status = await check_exercise_completion(request.user_id)
            except Exception as completion_error:
                print(f"⚠️ [QUICK_ANSWER] Failed to check exercise completion: {str(completion_error)}")
                exercise_completion_status = {
                    "exercise_completed": False,
                    "progress_percentage": 0.0,
                    "completed_topics": 0,
                    "total_topics": 0,
                    "current_topic_id": 1,
                    "stage_id": 2,
                    "exercise_id": 2,
                    "exercise_name": "Quick Answer",
                    "stage_name": "Stage 2 – A2 Elementary",
                    "error": str(completion_error)
                }
            
            return {
                "success": True,
                "question": question["question"],
                "expected_answers": question["expected_answers"],
                "user_text": user_text,
                "evaluation": evaluation,
                "progress_recorded": False,
                "answer_accuracy": evaluation.get("answer_accuracy", 0),
                "grammar_score": evaluation.get("grammar_score", 0),
                "fluency_score": evaluation.get("fluency_score", 0),
                "exercise_completion": exercise_completion_status
            }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [QUICK_ANSWER] Unexpected error in evaluation: {e}")
        raise HTTPException(status_code=500, detail="Failed to evaluate response") 