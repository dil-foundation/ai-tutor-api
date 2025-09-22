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
from app.services.feedback import evaluate_response_ex3_stage1
from app.supabase_client import supabase, progress_tracker
from app.auth_middleware import get_current_user, require_student,require_admin_or_teacher_or_student
router = APIRouter()


class AudioEvaluationRequest(BaseModel):
    audio_base64: str
    dialogue_id: int
    filename: str
    user_id: str
    time_spent_seconds: int
    urdu_used: bool

async def get_dialogue_by_id(dialogue_id: int):
    """Fetch a dialogue from Supabase by its topic_number for Stage 1, Exercise 3."""
    print(f"🔍 [DB] Looking for dialogue with topic_number (ID): {dialogue_id} for Stage 1, Exercise 3")
    try:
        # parent_id for Stage 1, Exercise 3 ('Functional Dialogue') is 9.
        query = supabase.table("ai_tutor_content_hierarchy").select("id, topic_number, title, title_urdu, topic_data, category, difficulty").eq("level", "topic").eq("parent_id", 9).eq("topic_number", dialogue_id).single()
        response = await run_in_threadpool(query.execute)
        
        if response.data:
            db_dialogue = response.data
            topic_data = db_dialogue.get("topic_data", {})
            
            formatted_dialogue = {
                "id": db_dialogue.get("topic_number"),
                "db_id": db_dialogue.get("id"),
                "ai_prompt": db_dialogue.get("title"),
                "ai_prompt_urdu": db_dialogue.get("title_urdu"),
                "expected_keywords": topic_data.get("expected_keywords"),
                "expected_keywords_urdu": topic_data.get("expected_keywords_urdu"),
                "category": db_dialogue.get("category"),
                "difficulty": db_dialogue.get("difficulty"),
                "context": topic_data.get("context")
            }
            print(f"✅ [DB] Found dialogue: {formatted_dialogue['ai_prompt']}")
            return formatted_dialogue
        else:
            print(f"❌ [DB] Dialogue with topic_number {dialogue_id} not found for parent_id 9")
            return None
    except Exception as e:
        print(f"❌ [DB] Error fetching dialogue from Supabase: {str(e)}")
        return None


async def check_exercise_completion(user_id: str) -> dict:
    """Check if user has completed the full Listen and Reply exercise (Stage 1, Exercise 3)"""
    print(f"🔍 [COMPLETION] Checking exercise completion for user: {user_id}")
    
    try:
        # Get total dialogues count from Supabase
        total_dialogues = 0
        try:
            # parent_id for 'Functional Dialogue' is 9
            query = supabase.table("ai_tutor_content_hierarchy").select("id", count="exact").eq("level", "topic").eq("parent_id", 9)
            response = await run_in_threadpool(query.execute)
            if response.count is not None:
                total_dialogues = response.count
                print(f"📊 [COMPLETION] Total dialogues available from DB: {total_dialogues}")
            else:
                print("⚠️ [COMPLETION] Could not get count from Supabase, falling back to default.")
                total_dialogues = 20
        except Exception as e:
            print(f"❌ [COMPLETION] Error getting dialogue count from DB: {str(e)}")
            total_dialogues = 20  # Default fallback based on data file
        
        # Get user's progress for Stage 1 Exercise 3
        progress_result = await progress_tracker.get_user_topic_progress(
            user_id=user_id,
            stage_id=1,
            exercise_id=3
        )
        
        if not progress_result["success"]:
            print(f"❌ [COMPLETION] Failed to get progress: {progress_result.get('error')}")
            return {
                "exercise_completed": False,
                "progress_percentage": 0,
                "completed_topics": 0,
                "total_topics": total_dialogues,
                "current_topic_id": 1,
                "error": progress_result.get("error", "Failed to get progress")
            }
        
        # Get current topic information
        current_topic_result = await progress_tracker.get_current_topic_for_exercise(
            user_id=user_id,
            stage_id=1,
            exercise_id=3
        )
        
        if not current_topic_result["success"]:
            print(f"❌ [COMPLETION] Failed to get current topic: {current_topic_result.get('error')}")
            return {
                "exercise_completed": False,
                "progress_percentage": 0,
                "completed_topics": 0,
                "total_topics": total_dialogues,
                "current_topic_id": 1,
                "error": current_topic_result.get("error", "Failed to get current topic")
            }
        
        # Extract progress data
        topic_progress = progress_result.get("data", [])
        current_topic_id = current_topic_result.get("current_topic_id", 1)
        is_exercise_completed = current_topic_result.get("is_completed", False)
        
        # Calculate completion metrics
        completed_topics = len(topic_progress) if topic_progress else 0
        progress_percentage = (completed_topics / total_dialogues) * 100 if total_dialogues > 0 else 0
        
        # Determine if exercise is truly completed
        # Exercise is completed ONLY when ALL topics are completed
        exercise_completed = completed_topics >= total_dialogues and completed_topics > 0
        
        print(f"📊 [COMPLETION] Completion status calculated:")
        print(f"   - Total dialogues: {total_dialogues}")
        print(f"   - Completed topics: {completed_topics}")
        print(f"   - Current topic ID: {current_topic_id}")
        print(f"   - Progress percentage: {progress_percentage:.1f}%")
        print(f"   - Exercise completed: {exercise_completed}")
        
        # Additional logging for completion logic
        if completed_topics >= total_dialogues:
            print(f"🎉 [COMPLETION] All {total_dialogues} dialogues completed! Exercise is finished!")
        elif completed_topics > 0:
            print(f"📈 [COMPLETION] {completed_topics}/{total_dialogues} dialogues completed. Exercise in progress...")
        else:
            print(f"🆕 [COMPLETION] No dialogues completed yet. Exercise just started.")
        
        return {
            "exercise_completed": exercise_completed,
            "progress_percentage": round(progress_percentage, 1),
            "completed_topics": completed_topics,
            "total_topics": total_dialogues,
            "current_topic_id": current_topic_id,
            "stage_id": 1,
            "exercise_id": 3,
            "exercise_name": "Listen and Reply",
            "stage_name": "Stage 1 – A1 Beginner",
            "completion_date": topic_progress[-1].get("created_at") if topic_progress and exercise_completed else None
        }
        
    except Exception as e:
        print(f"❌ [COMPLETION] Error checking exercise completion: {str(e)}")
        return {
            "exercise_completed": False,
            "progress_percentage": 0,
            "completed_topics": 0,
            "total_topics": 12,
            "current_topic_id": 1,
            "error": f"Failed to check completion status: {str(e)}"
        }


@router.get("/dialogues")
async def get_all_dialogues(current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)):
    """Get all available dialogues for Listen and Reply exercise from Supabase"""
    print("🔄 [API] GET /dialogues endpoint called")
    try:
        print("🔄 [DB] Fetching all dialogues for Stage 1, Exercise 3 from Supabase")
        # parent_id for 'Functional Dialogue' is 9
        query = supabase.table("ai_tutor_content_hierarchy").select("id, topic_number, title, title_urdu, topic_data, category, difficulty").eq("level", "topic").eq("parent_id", 9).order("topic_number", desc=False)
        response = await run_in_threadpool(query.execute)

        if response.data:
            # Format data to be backward compatible with the old JSON structure.
            dialogues = []
            for d in response.data:
                topic_data = d.get("topic_data", {})
                dialogues.append({
                    "id": d.get("topic_number"),
                    "db_id": d.get("id"),
                    "ai_prompt": d.get("title"),
                    "ai_prompt_urdu": d.get("title_urdu"),
                    "expected_keywords": topic_data.get("expected_keywords"),
                    "expected_keywords_urdu": topic_data.get("expected_keywords_urdu"),
                    "category": d.get("category"),
                    "difficulty": d.get("difficulty"),
                    "context": topic_data.get("context")
                })
            print(f"✅ [DB] Successfully loaded {len(dialogues)} dialogues from Supabase")
            return {"dialogues": dialogues}
        else:
            print("❌ [DB] No dialogues found for Stage 1, Exercise 3")
            return {"dialogues": []}
    except Exception as e:
        print(f"❌ [API] Error in get_all_dialogues: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to load dialogues from database: {str(e)}")

@router.get("/dialogues/{dialogue_id}")
async def get_dialogue(dialogue_id: int, current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)):
    """Get a specific dialogue by ID"""
    print(f"🔄 [API] GET /dialogues/{dialogue_id} endpoint called")
    try:
        dialogue_data = await get_dialogue_by_id(dialogue_id)
        if not dialogue_data:
            print(f"❌ [API] Dialogue {dialogue_id} not found")
            raise HTTPException(status_code=404, detail="Dialogue not found")
        print(f"✅ [API] Returning dialogue: {dialogue_data['ai_prompt']}")
        return {
            "id": dialogue_data['id'], 
            "ai_prompt": dialogue_data['ai_prompt'],
            "ai_prompt_urdu": dialogue_data['ai_prompt_urdu'],
            "expected_keywords": dialogue_data['expected_keywords'],
            "expected_keywords_urdu": dialogue_data['expected_keywords_urdu'],
            "category": dialogue_data['category'],
            "difficulty": dialogue_data['difficulty'],
            "context": dialogue_data['context']
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [API] Error in get_dialogue: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post(
    "/listen-and-reply/{dialogue_id}",
    summary="Convert dialogue prompt to audio for Listen and Reply Exercise",
    description="""
This endpoint is part of Stage 1 - Exercise 3 (Listen and Reply). 
It takes a dialogue ID from a predefined list, converts the corresponding AI prompt into speech (TTS),
and returns the generated audio file as the response.
""",
    tags=["Stage 1 - Exercise 3 (Listen and Reply)"]
)
async def listen_and_reply(dialogue_id: int, current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)):
    print(f"🔄 [API] POST /listen-and-reply/{dialogue_id} endpoint called")
    try:
        dialogue_data = await get_dialogue_by_id(dialogue_id)
        if not dialogue_data:
            print(f"❌ [API] Dialogue {dialogue_id} not found")
            raise HTTPException(status_code=404, detail="Dialogue not found")

        prompt_text = dialogue_data['ai_prompt']
        print(f"🎤 [API] Converting dialogue to speech: '{prompt_text}'")
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
        print(f"❌ [API] Error in listen_and_reply: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post(
    "/evaluate-listen-reply",
    summary="Evaluate user's audio recording against expected keywords",
    description="""
This endpoint evaluates the user's recorded audio against the expected keywords for listen and reply dialogues.
It performs speech-to-text conversion and provides feedback on the response quality.
Also records progress tracking data in Supabase database.
""",
    tags=["Stage 1 - Exercise 3 (Listen and Reply)"]
)
async def evaluate_listen_reply(
    request: AudioEvaluationRequest,
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)
):
    print(f"🔄 [API] POST /evaluate-listen-reply endpoint called")
    print(f"📝 [API] Request details: dialogue_id={request.dialogue_id}, filename={request.filename}")
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
        # Get the expected dialogue data
        dialogue_data = await get_dialogue_by_id(request.dialogue_id)
        if not dialogue_data:
            print(f"❌ [API] Dialogue {request.dialogue_id} not found")
            raise HTTPException(status_code=404, detail="Dialogue not found")

        expected_keywords = dialogue_data['expected_keywords']
        expected_keywords_urdu = dialogue_data['expected_keywords_urdu']
        ai_prompt = dialogue_data['ai_prompt']
        print(f"✅ [API] Expected keywords: {expected_keywords}")
        print(f"✅ [API] AI Prompt: '{ai_prompt}'")

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
                "expected_keywords": expected_keywords
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
                    "expected_keywords": expected_keywords
                }

        except Exception as e:
            print(f"❌ [API] Error transcribing audio: {str(e)}")
            return {
                "success": False,
                "error": "transcription_failed",
                "message": "Failed to process audio. Please try again.",
                "expected_keywords": expected_keywords
            }

        # Evaluate the response
        try:
            print(f"🔄 [API] Evaluating response: '{user_text}' vs expected keywords")
            evaluation = evaluate_response_ex3_stage1(expected_keywords, user_text, ai_prompt)
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
                        exercise_id=3,  # Exercise 3 (Listen and Reply)
                        topic_id=dialogue_data['id'], # Use the actual database ID
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
            print(f"✅ [API] Exercise completion status: {exercise_completion_status}")

            return {
                "success": True,
                "ai_prompt": ai_prompt,
                "expected_keywords": expected_keywords,
                "expected_keywords_urdu": expected_keywords_urdu,
                "user_text": user_text,
                "evaluation": evaluation,
                "progress_recorded": progress_recorded,
                "unlocked_content": unlocked_content,
                "exercise_completion_status": exercise_completion_status
            }

        except Exception as e:
            print(f"❌ [API] Error evaluating response: {str(e)}")
            return {
                "success": False,
                "error": "evaluation_failed",
                "message": "Failed to evaluate response. Please try again.",
                "expected_keywords": expected_keywords,
                "user_text": user_text
            }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [API] Unexpected error in evaluate_listen_reply: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}") 