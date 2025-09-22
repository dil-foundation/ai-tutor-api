from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, Any
import json
import os
import base64
from io import BytesIO
from fastapi.concurrency import run_in_threadpool
from app.services.tts import synthesize_speech, synthesize_speech_exercises
from app.services.stt import transcribe_audio_bytes_eng_only
from app.services.feedback import evaluate_response_ex3_stage5
from app.supabase_client import supabase, progress_tracker
from app.auth_middleware import get_current_user, require_student,require_admin_or_teacher_or_student

router = APIRouter()

class AudioEvaluationRequest(BaseModel):
    audio_base64: str
    prompt_id: int
    filename: str
    user_id: str
    time_spent_seconds: int
    urdu_used: bool

async def get_prompt_by_id_from_db(prompt_id: int):
    """Fetch an in-depth interview prompt from Supabase by its topic_number for Stage 5, Exercise 3."""
    print(f"🔍 [DB] Looking for prompt with topic_number (ID): {prompt_id} for Stage 5, Exercise 3")
    try:
        # parent_id for Stage 5, Exercise 3 ('Professional Interview Mastery') is 21.
        query = supabase.table("ai_tutor_content_hierarchy").select("id, topic_number, title, topic_data, category, difficulty").eq("level", "topic").eq("parent_id", 21).eq("topic_number", prompt_id).single()
        response = await run_in_threadpool(query.execute)
        
        if response.data:
            db_item = response.data
            topic_data = db_item.get("topic_data", {})
            
            formatted_item = {
                "id": db_item.get("topic_number"),
                "db_id": db_item.get("id"),
                "question": db_item.get("title"),
                "category": db_item.get("category"),
                "difficulty": db_item.get("difficulty"),
                "question_type": topic_data.get("question_type"),
                "expected_structure": topic_data.get("expected_structure"),
                "expected_keywords": topic_data.get("expected_keywords", []),
                "vocabulary_focus": topic_data.get("vocabulary_focus", []),
                "model_answer": topic_data.get("model_answer"),
                "evaluation_criteria": topic_data.get("evaluation_criteria", {})
            }
            print(f"✅ [DB] Found prompt: {formatted_item['question']}")
            return formatted_item
        else:
            print(f"❌ [DB] Prompt with topic_number {prompt_id} not found for parent_id 21")
            return None
    except Exception as e:
        print(f"❌ [DB] Error fetching prompt from Supabase: {str(e)}")
        return None


async def check_exercise_completion(user_id: str) -> dict:
    """Check if user has completed the full In-Depth Interview exercise (Stage 5, Exercise 3)"""
    print(f"🔍 [COMPLETION] Checking exercise completion for user: {user_id}")
    
    try:
        # Get total prompts count from Supabase
        total_topics = 0
        try:
            # parent_id for 'Professional Interview Mastery' is 21
            query = supabase.table("ai_tutor_content_hierarchy").select("id", count="exact").eq("level", "topic").eq("parent_id", 21)
            response = await run_in_threadpool(query.execute)
            if response.count is not None:
                total_topics = response.count
                print(f"📊 [COMPLETION] Total prompts available from DB: {total_topics}")
            else:
                print("⚠️ [COMPLETION] Could not get count from Supabase, falling back to default.")
                total_topics = 7
        except Exception as e:
            print(f"❌ [COMPLETION] Error getting prompt count from DB: {str(e)}")
            total_topics = 7
        
        # Get user's progress for stage 5, exercise 3
        progress_result = await progress_tracker.get_user_topic_progress(
            user_id=user_id,
            stage_id=5,
            exercise_id=3
        )
        
        if not progress_result["success"]:
            print(f"❌ [COMPLETION] Failed to get user progress: {progress_result.get('error')}")
            return {
                "exercise_completed": False,
                "progress_percentage": 0.0,
                "completed_topics": 0,
                "total_topics": total_topics,
                "current_topic_id": 1,
                "stage_id": 5,
                "exercise_id": 3,
                "exercise_name": "In-Depth Interview",
                "stage_name": "Stage 5 – C1 Advanced",
                "error": progress_result.get("error", "Failed to get progress")
            }
        
        user_progress = progress_result.get("data", [])
        completed_topics = len([record for record in user_progress if record.get("completed", False)])
        
        # Get current topic ID
        current_topic_result = await progress_tracker.get_current_topic_for_exercise(
            user_id=user_id,
            stage_id=5,
            exercise_id=3
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
        print(f"   - Total prompts: {total_topics}")
        print(f"   - Completed topics: {completed_topics}")
        print(f"   - Current topic ID: {current_topic_id}")
        print(f"   - Progress percentage: {progress_percentage:.1f}%")
        print(f"   - Exercise completed: {exercise_completed}")
        
        return {
            "exercise_completed": exercise_completed,
            "progress_percentage": progress_percentage,
            "completed_topics": completed_topics,
            "total_topics": total_topics,
            "current_topic_id": current_topic_id,
            "stage_id": 5,
            "exercise_id": 3,
            "exercise_name": "In-Depth Interview",
            "stage_name": "Stage 5 – C1 Advanced"
        }
        
    except Exception as e:
        print(f"❌ [COMPLETION] Error checking exercise completion: {str(e)}")
        return {
            "exercise_completed": False,
            "progress_percentage": 0.0,
            "completed_topics": 0,
            "total_topics": 0,
            "current_topic_id": 1,
            "stage_id": 5,
            "exercise_id": 3,
            "exercise_name": "In-Depth Interview",
            "stage_name": "Stage 5 – C1 Advanced",
            "error": str(e)
        }

@router.get("/in-depth-interview-prompts")
async def get_all_prompts(current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)):
    """Get all available prompts for In-Depth Interview exercise"""
    print("🔄 [API] GET /in-depth-interview-prompts endpoint called")
    print(f"👤 [API] Authenticated user: {current_user['email']}")
    try:
        print("🔄 [DB] Fetching all prompts for Stage 5, Exercise 3 from Supabase")
        # parent_id for 'Professional Interview Mastery' is 21
        query = supabase.table("ai_tutor_content_hierarchy").select("id, topic_number, title, topic_data, category, difficulty").eq("level", "topic").eq("parent_id", 21).order("topic_number", desc=False)
        response = await run_in_threadpool(query.execute)

        if response.data:
            prompts = []
            for item in response.data:
                prompts.append({
                    "id": item.get("topic_number"),
                    "db_id": item.get("id"),
                    "question": item.get("title"),
                    "category": item.get("category"),
                    "difficulty": item.get("difficulty"),
                })
            print(f"✅ [DB] Successfully loaded {len(prompts)} prompts from Supabase")
            return {"prompts": prompts}
        else:
            print("❌ [DB] No prompts found for Stage 5, Exercise 3")
            return {"prompts": []}
    except Exception as e:
        print(f"❌ [API] Error in get_all_prompts: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to load prompts from database: {str(e)}")

@router.get("/in-depth-interview-prompts/{prompt_id}")
async def get_prompt(
    prompt_id: int,
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)
):
    """Get a specific prompt by ID"""
    print(f"🔄 [API] GET /in-depth-interview-prompts/{prompt_id} endpoint called")
    print(f"👤 [API] Authenticated user: {current_user['email']}")
    try:
        prompt_data = await get_prompt_by_id_from_db(prompt_id)
        if not prompt_data:
            print(f"❌ [API] Prompt {prompt_id} not found")
            raise HTTPException(status_code=404, detail="Prompt not found")
        print(f"✅ [API] Returning prompt: {prompt_data['question']}")
        return prompt_data
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [API] Error in get_prompt: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post(
    "/in-depth-interview/{prompt_id}",
    summary="Convert prompt to audio for In-Depth Interview Exercise",
    description="""
This endpoint is part of Stage 5 - Exercise 3 (In-Depth Interview). 
It takes a prompt ID from a predefined list, converts the corresponding prompt into speech (TTS),
and returns the generated audio file as the response.
""",
    tags=["Stage 5 - Exercise 3 (In-Depth Interview)"]
)
async def in_depth_interview(
    prompt_id: int,
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)
):
    print(f"🔄 [API] POST /in-depth-interview/{prompt_id} endpoint called")
    print(f"👤 [API] Authenticated user: {current_user['email']}")
    try:
        prompt_data = await get_prompt_by_id_from_db(prompt_id)
        if not prompt_data:
            print(f"❌ [API] Prompt {prompt_id} not found")
            raise HTTPException(status_code=404, detail="Prompt not found")

        prompt_text = prompt_data['question']
        print(f"🎤 [API] Converting prompt to speech: '{prompt_text}'")
        audio_content = await synthesize_speech_exercises(prompt_text)
        print(f"✅ [API] Audio content generated, size: {len(audio_content)} bytes")
        
        # Convert to base64 for React Native compatibility
        audio_base64 = base64.b64encode(audio_content).decode('utf-8')
        print(f"✅ [API] Audio converted to base64, length: {len(audio_base64)}")
        
        # Return base64 string directly
        return {"audio_base64": audio_base64}
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [API] Error in in_depth_interview: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post(
    "/evaluate-in-depth-interview",
    summary="Evaluate user's audio recording against expected keywords and interview structure",
    description="""
This endpoint evaluates the user's recorded audio against the expected keywords and interview structure for in-depth interview prompts.
It performs speech-to-text conversion and provides comprehensive feedback on the response quality.
Also records progress tracking data in Supabase database.
""",
    tags=["Stage 5 - Exercise 3 (In-Depth Interview)"]
)
async def evaluate_in_depth_interview(
    request: AudioEvaluationRequest,
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)
):
    print(f"🔄 [API] POST /evaluate-in-depth-interview endpoint called")
    print(f"👤 [API] Authenticated user: {current_user['email']}")
    print(f"📝 [API] Request details: prompt_id={request.prompt_id}, filename={request.filename}")
    print(f"📊 [API] Audio data length: {len(request.audio_base64)} characters")
    print(f"👤 [API] User ID: {request.user_id}")
    print(f"⏱️ [API] Time spent: {request.time_spent_seconds} seconds")
    print(f"🌐 [API] Urdu used: {request.urdu_used}")
    
    # Verify user is accessing their own data
    if request.user_id != current_user['id']:
        print(f"❌ [API] Unauthorized access attempt: {current_user['email']} tried to access user {request.user_id}")
        raise HTTPException(status_code=403, detail="Unauthorized access to user data")
    
    try:
        # Get the expected prompt and keywords
        prompt_data = await get_prompt_by_id_from_db(request.prompt_id)
        if not prompt_data:
            print(f"❌ [API] Prompt {request.prompt_id} not found")
            raise HTTPException(status_code=404, detail="Prompt not found")

        expected_keywords = prompt_data['expected_keywords']
        vocabulary_focus = prompt_data['vocabulary_focus']
        question_text = prompt_data['question']
        model_answer = prompt_data['model_answer']
        expected_structure = prompt_data['expected_structure']
        print(f"✅ [API] Expected keywords: {expected_keywords}")
        print(f"✅ [API] Vocabulary focus: {vocabulary_focus}")
        print(f"✅ [API] Question: '{question_text}'")
        print(f"✅ [API] Expected structure: '{expected_structure}'")
        print(f"✅ [API] Model answer: '{model_answer}'")

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
                "question": question_text
            }

        # Transcribe the audio
        try:
            print("🔄 [API] Transcribing audio...")
            transcription_result = transcribe_audio_bytes_eng_only(audio_bytes)
            user_text = transcription_result.get("text", "").strip()
            print(f"✅ [API] Transcription result: '{user_text}'")
            
            # Check if transcription is empty or too short
            if not user_text or len(user_text) < 5:
                print(f"⚠️ [API] Transcription too short or empty: '{user_text}'")
                return {
                    "success": False,
                    "error": "no_speech_detected",
                    "message": "No clear speech detected. Please speak more clearly and provide a complete answer.",
                    "expected_keywords": expected_keywords,
                    "question": question_text
                }

        except Exception as e:
            print(f"❌ [API] Error transcribing audio: {str(e)}")
            return {
                "success": False,
                "error": "transcription_failed",
                "message": "Failed to process audio. Please try again.",
                "expected_keywords": expected_keywords,
                "question": question_text
            }

        # Evaluate the response
        try:
            print(f"🔄 [API] Evaluating response: '{user_text}' vs expected keywords: {expected_keywords}")
            evaluation = evaluate_response_ex3_stage5(user_text, question_text, expected_keywords, vocabulary_focus, model_answer, expected_structure)
            print(f"✅ [API] Evaluation completed: {evaluation}")
            
            # Extract evaluation details for progress tracking
            score = evaluation.get("score", 0)
            is_correct = evaluation.get("is_correct", False)
            completed = evaluation.get("completed", False)
            suggested_improvement = evaluation.get("suggested_improvement", "")
            keyword_matches = evaluation.get("matched_keywords_count", 0)
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
                    time_spent = max(1, min(request.time_spent_seconds, 600))  # Between 1-600 seconds for interview
                    if time_spent != request.time_spent_seconds:
                        print(f"⚠️ [API] Adjusted time spent from {request.time_spent_seconds} to {time_spent} seconds")
                    
                    # Record the topic attempt
                    progress_result = await progress_tracker.record_topic_attempt(
                        user_id=request.user_id,
                        stage_id=5,  # Stage 5
                        exercise_id=3,  # Exercise 3 (In-Depth Interview)
                        topic_id=prompt_data['id'],
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
            
            # Check exercise completion status
            exercise_completion_status = None
            try:
                exercise_completion_status = await check_exercise_completion(request.user_id)
                print(f"📊 [IN_DEPTH_INTERVIEW] Exercise completion status: {exercise_completion_status}")
            except Exception as completion_error:
                print(f"⚠️ [IN_DEPTH_INTERVIEW] Failed to check exercise completion: {str(completion_error)}")
                exercise_completion_status = {
                    "exercise_completed": False,
                    "progress_percentage": 0.0,
                    "completed_topics": 0,
                    "total_topics": 0,
                    "current_topic_id": 1,
                    "stage_id": 5,
                    "exercise_id": 3,
                    "exercise_name": "In-Depth Interview",
                    "stage_name": "Stage 5 – C1 Advanced",
                    "error": str(completion_error)
                }
            
            return {
                "success": True,
                "question": question_text,
                "expected_keywords": expected_keywords,
                "user_text": user_text,
                "evaluation": evaluation,
                "suggested_improvement": suggested_improvement,
                "progress_recorded": progress_recorded,
                "unlocked_content": unlocked_content,
                "keyword_matches": keyword_matches,
                "total_keywords": total_keywords,
                "fluency_score": fluency_score,
                "grammar_score": grammar_score,
                "exercise_completion": exercise_completion_status
            }

        except Exception as e:
            print(f"❌ [API] Error evaluating response: {str(e)}")
            return {
                "success": False,
                "error": "evaluation_failed",
                "message": "Failed to evaluate response. Please try again.",
                "expected_keywords": expected_keywords,
                "question": question_text,
                "user_text": user_text
            }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [API] Unexpected error in evaluate_in_depth_interview: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}") 