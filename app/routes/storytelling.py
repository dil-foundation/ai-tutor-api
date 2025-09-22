from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
import os
import base64
from io import BytesIO
from typing import Dict, Any
from fastapi.concurrency import run_in_threadpool
from app.services.tts import synthesize_speech, synthesize_speech_exercises
from app.services.stt import transcribe_audio_bytes_eng_only
from app.services.feedback import evaluate_response_ex1_stage3
from app.supabase_client import supabase, progress_tracker
from app.auth_middleware import get_current_user, require_student, require_admin_or_teacher_or_student

router = APIRouter()

class AudioEvaluationRequest(BaseModel):
    audio_base64: str
    prompt_id: int
    filename: str
    user_id: str
    time_spent_seconds: int
    urdu_used: bool

async def get_prompt_by_id_from_db(prompt_id: int):
    """Fetch a storytelling prompt from Supabase by its topic_number for Stage 3, Exercise 1."""
    print(f"🔍 [DB] Looking for prompt with topic_number (ID): {prompt_id} for Stage 3, Exercise 1")
    try:
        # parent_id for Stage 3, Exercise 1 ('Storytelling Narration') is 13.
        query = supabase.table("ai_tutor_content_hierarchy").select("id, topic_number, title, title_urdu, topic_data, category, difficulty").eq("level", "topic").eq("parent_id", 13).eq("topic_number", prompt_id).single()
        response = await run_in_threadpool(query.execute)
        
        if response.data:
            db_prompt = response.data
            topic_data = db_prompt.get("topic_data", {})
            
            formatted_prompt = {
                "id": db_prompt.get("topic_number"),
                "db_id": db_prompt.get("id"),
                "prompt": db_prompt.get("title"),
                "prompt_urdu": db_prompt.get("title_urdu"),
                "category": db_prompt.get("category"),
                "difficulty": db_prompt.get("difficulty"),
                "tense_focus": topic_data.get("tense_focus"),
                "expected_structure": topic_data.get("expected_structure"),
                "example_keywords": topic_data.get("example_keywords", []),
                "example_keywords_urdu": topic_data.get("example_keywords_urdu", []),
                "model_answer": topic_data.get("model_answer"),
                "model_answer_urdu": topic_data.get("model_answer_urdu"),
                "evaluation_criteria": topic_data.get("evaluation_criteria"),
                "learning_objectives": topic_data.get("learning_objectives", [])
            }
            print(f"✅ [DB] Found prompt: {formatted_prompt['prompt']}")
            return formatted_prompt
        else:
            print(f"❌ [DB] Prompt with topic_number {prompt_id} not found for parent_id 13")
            return None
    except Exception as e:
        print(f"❌ [DB] Error fetching prompt from Supabase: {str(e)}")
        return None

async def check_exercise_completion(user_id: str) -> dict:
    """Check if user has completed the full Storytelling exercise (Stage 3, Exercise 1)"""
    print(f"🔍 [COMPLETION] Checking exercise completion for user: {user_id}")
    
    try:
        # Get total stories count from Supabase
        total_stories = 0
        try:
            # parent_id for 'Storytelling Narration' is 13
            query = supabase.table("ai_tutor_content_hierarchy").select("id", count="exact").eq("level", "topic").eq("parent_id", 13)
            response = await run_in_threadpool(query.execute)
            if response.count is not None:
                total_stories = response.count
                print(f"📊 [COMPLETION] Total stories available from DB: {total_stories}")
            else:
                print("⚠️ [COMPLETION] Could not get count from Supabase, falling back to default.")
                total_stories = 10
        except Exception as e:
            print(f"❌ [COMPLETION] Error reading stories file: {str(e)}")
            total_stories = 10  # Default fallback based on data file
        
        # Get user's progress for Stage 3 Exercise 1
        progress_result = await progress_tracker.get_user_topic_progress(
            user_id=user_id,
            stage_id=3,
            exercise_id=1
        )
        
        if not progress_result["success"]:
            print(f"❌ [COMPLETION] Failed to get progress: {progress_result.get('error')}")
            return {
                "exercise_completed": False,
                "progress_percentage": 0,
                "completed_topics": 0,
                "total_topics": total_stories,
                "current_topic_id": 1,
                "error": progress_result.get("error", "Failed to get progress")
            }
        
        # Get current topic information
        current_topic_result = await progress_tracker.get_current_topic_for_exercise(
            user_id=user_id,
            stage_id=3,
            exercise_id=1
        )
        
        if not current_topic_result["success"]:
            print(f"❌ [COMPLETION] Failed to get current topic: {current_topic_result.get('error')}")
            return {
                "exercise_completed": False,
                "progress_percentage": 0,
                "completed_topics": 0,
                "total_topics": total_stories,
                "current_topic_id": 1,
                "error": current_topic_result.get("error", "Failed to get current topic")
            }
        
        # Extract progress data
        topic_progress = progress_result.get("data", [])
        current_topic_id = current_topic_result.get("current_topic_id", 1)
        is_exercise_completed = current_topic_result.get("is_completed", False)
        
        # Calculate completion metrics
        completed_topics = len(topic_progress) if topic_progress else 0
        progress_percentage = (completed_topics / total_stories) * 100 if total_stories > 0 else 0
        
        # Determine if exercise is truly completed
        # Exercise is completed ONLY when ALL topics are completed
        exercise_completed = completed_topics >= total_stories and completed_topics > 0
        
        print(f"📊 [COMPLETION] Completion status calculated:")
        print(f"   - Total stories: {total_stories}")
        print(f"   - Completed topics: {completed_topics}")
        print(f"   - Current topic ID: {current_topic_id}")
        print(f"   - Progress percentage: {progress_percentage:.1f}%")
        print(f"   - Exercise completed: {exercise_completed}")
        
        # Additional logging for completion logic
        if completed_topics >= total_stories:
            print(f"🎉 [COMPLETION] All {total_stories} stories completed! Exercise is finished!")
        elif completed_topics > 0:
            print(f"📈 [COMPLETION] {completed_topics}/{total_stories} stories completed. Exercise in progress...")
        else:
            print(f"🆕 [COMPLETION] No stories completed yet. Exercise just started.")
        
        return {
            "exercise_completed": exercise_completed,
            "progress_percentage": round(progress_percentage, 1),
            "completed_topics": completed_topics,
            "total_topics": total_stories,
            "current_topic_id": current_topic_id,
            "stage_id": 3,
            "exercise_id": 1,
            "exercise_name": "Storytelling Practice",
            "stage_name": "Stage 3 – B1 Intermediate",
            "completion_date": topic_progress[-1].get("created_at") if topic_progress and exercise_completed else None
        }
        
    except Exception as e:
        print(f"❌ [COMPLETION] Error checking exercise completion: {str(e)}")
        return {
            "exercise_completed": False,
            "progress_percentage": 0,
            "completed_topics": 0,
            "total_topics": 18,
            "current_topic_id": 1,
            "error": f"Failed to check completion status: {str(e)}"
        }


@router.get("/storytelling-prompts")
async def get_all_prompts(current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)):
    """Get all available prompts for Storytelling exercise from Supabase"""
    print("🔄 [API] GET /storytelling-prompts endpoint called")
    try:
        print("🔄 [DB] Fetching all prompts for Stage 3, Exercise 1 from Supabase")
        query = supabase.table("ai_tutor_content_hierarchy").select("id, topic_number, title, title_urdu, topic_data, category, difficulty").eq("level", "topic").eq("parent_id", 13).order("topic_number", desc=False)
        response = await run_in_threadpool(query.execute)

        if response.data:
            prompts = []
            for p in response.data:
                topic_data = p.get("topic_data", {})
                prompts.append({
                    "id": p.get("topic_number"),
                    "db_id": p.get("id"),
                    "prompt": p.get("title"),
                    "prompt_urdu": p.get("title_urdu"),
                    "category": p.get("category"),
                    "difficulty": p.get("difficulty"),
                    "tense_focus": topic_data.get("tense_focus"),
                    "expected_structure": topic_data.get("expected_structure"),
                    "example_keywords": topic_data.get("example_keywords", []),
                    "example_keywords_urdu": topic_data.get("example_keywords_urdu", []),
                    "model_answer": topic_data.get("model_answer"),
                    "model_answer_urdu": topic_data.get("model_answer_urdu"),
                    "evaluation_criteria": topic_data.get("evaluation_criteria"),
                    "learning_objectives": topic_data.get("learning_objectives", [])
                })
            print(f"✅ [DB] Successfully loaded {len(prompts)} prompts from Supabase")
            return {"prompts": prompts}
        else:
            print("❌ [DB] No prompts found for Stage 3, Exercise 1")
            return {"prompts": []}
    except Exception as e:
        print(f"❌ [API] Error in get_all_prompts: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to load prompts from database: {str(e)}")

@router.get("/storytelling-prompts/{prompt_id}")
async def get_prompt(prompt_id: int, current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)):
    """Get a specific prompt by ID"""
    print(f"🔄 [API] GET /storytelling-prompts/{prompt_id} endpoint called")
    try:
        prompt_data = await get_prompt_by_id_from_db(prompt_id)
        if not prompt_data:
            print(f"❌ [API] Prompt {prompt_id} not found")
            raise HTTPException(status_code=404, detail="Prompt not found")
        print(f"✅ [API] Returning prompt: {prompt_data['prompt']}")
        return {
            "id": prompt_data['id'],
            "prompt": prompt_data['prompt'],
            "prompt_urdu": prompt_data['prompt_urdu'],
            "category": prompt_data['category'],
            "difficulty": prompt_data['difficulty'],
            "tense_focus": prompt_data['tense_focus'],
            "expected_structure": prompt_data['expected_structure'],
            "example_keywords": prompt_data['example_keywords'],
            "example_keywords_urdu": prompt_data['example_keywords_urdu'],
            "model_answer": prompt_data['model_answer'],
            "model_answer_urdu": prompt_data['model_answer_urdu'],
            "evaluation_criteria": prompt_data['evaluation_criteria'],
            "learning_objectives": prompt_data['learning_objectives']
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [API] Error in get_prompt: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post(
    "/storytelling/{prompt_id}",
    summary="Convert prompt to audio for Storytelling Exercise",
    description="""
This endpoint is part of Stage 3 - Exercise 1 (Storytelling). 
It takes a prompt ID from a predefined list, converts the corresponding prompt into speech (TTS),
and returns the generated audio file as the response.
""",
    tags=["Stage 3 - Exercise 1 (Storytelling)"]
)
async def storytelling(prompt_id: int, current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)):
    print(f"🔄 [API] POST /storytelling/{prompt_id} endpoint called")
    try:
        prompt_data = await get_prompt_by_id_from_db(prompt_id)
        if not prompt_data:
            print(f"❌ [API] Prompt {prompt_id} not found")
            raise HTTPException(status_code=404, detail="Prompt not found")

        prompt_text = prompt_data['prompt']
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
        print(f"❌ [API] Error in storytelling: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post(
    "/evaluate-storytelling",
    summary="Evaluate user's audio recording against expected keywords and narrative structure",
    description="""
This endpoint evaluates the user's recorded audio against the expected keywords and narrative structure for storytelling prompts.
It performs speech-to-text conversion and provides comprehensive feedback on the response quality.
Also records progress tracking data in Supabase database.
""",
    tags=["Stage 3 - Exercise 1 (Storytelling)"]
)
async def evaluate_storytelling(
    request: AudioEvaluationRequest,
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)
):
    print(f"🔄 [API] POST /evaluate-storytelling endpoint called")
    print(f"📝 [API] Request details: prompt_id={request.prompt_id}, filename={request.filename}")
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
        # Get the expected prompt and keywords
        prompt_data = await get_prompt_by_id_from_db(request.prompt_id)
        if not prompt_data:
            print(f"❌ [API] Prompt {request.prompt_id} not found")
            raise HTTPException(status_code=404, detail="Prompt not found")

        expected_keywords = prompt_data['example_keywords']
        prompt_text = prompt_data['prompt']
        prompt_urdu = prompt_data['prompt_urdu']
        model_answer = prompt_data['model_answer']
        print(f"✅ [API] Expected keywords: {expected_keywords}")
        print(f"✅ [API] Prompt: '{prompt_text}'")
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
                "prompt": prompt_text
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
                    "message": "No clear speech detected. Please speak more clearly and tell a complete story.",
                    "expected_keywords": expected_keywords,
                    "prompt": prompt_text
                }

        except Exception as e:
            print(f"❌ [API] Error transcribing audio: {str(e)}")
            return {
                "success": False,
                "error": "transcription_failed",
                "message": "Failed to process audio. Please try again.",
                "expected_keywords": expected_keywords,
                "prompt": prompt_text
            }

        # Evaluate the response
        try:
            print(f"🔄 [API] Evaluating response: '{user_text}' vs expected keywords: {expected_keywords}")
            evaluation = evaluate_response_ex1_stage3(expected_keywords, user_text, prompt_text, prompt_urdu, model_answer)
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
                    time_spent = max(1, min(request.time_spent_seconds, 600))  # Between 1-600 seconds for storytelling
                    if time_spent != request.time_spent_seconds:
                        print(f"⚠️ [API] Adjusted time spent from {request.time_spent_seconds} to {time_spent} seconds")
                    
                    # Record the topic attempt
                    progress_result = await progress_tracker.record_topic_attempt(
                        user_id=request.user_id,
                        stage_id=3,  # Stage 3
                        exercise_id=1,  # Exercise 1 (Storytelling)
                        topic_id=prompt_data['db_id'], # Use the actual database ID
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
            
            # Check if the exercise is completed
            exercise_completion_status = await check_exercise_completion(request.user_id)
            print(f"📊 [API] Exercise completion status: {exercise_completion_status}")

            return {
                "success": True,
                "prompt": prompt_text,
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
                "exercise_completion_status": exercise_completion_status
            }

        except Exception as e:
            print(f"❌ [API] Error evaluating response: {str(e)}")
            return {
                "success": False,
                "error": "evaluation_failed",
                "message": "Failed to evaluate response. Please try again.",
                "expected_keywords": expected_keywords,
                "prompt": prompt_text,
                "user_text": user_text
            }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [API] Unexpected error in evaluate_storytelling: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}") 