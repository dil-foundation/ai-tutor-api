from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
import os
import base64
from io import BytesIO
from typing import Dict, Any
from fastapi.concurrency import run_in_threadpool
from app.services.tts import synthesize_speech,synthesize_speech_exercises
from app.services.stt import transcribe_audio_bytes_eng_only
from app.services.feedback import evaluate_response_ex1_stage1
from app.supabase_client import supabase, progress_tracker
from app.auth_middleware import get_current_user, require_student,require_admin_or_teacher_or_student
router = APIRouter()

class AudioEvaluationRequest(BaseModel):
    audio_base64: str
    phrase_id: int
    filename: str
    user_id: str
    time_spent_seconds: int
    urdu_used: bool

async def get_phrase_by_id(phrase_id: int):
    """Fetch a phrase from Supabase by its topic_number for Stage 1, Exercise 1."""
    print(f"🔍 [DB] Looking for phrase with topic_number (ID): {phrase_id} for Stage 1, Exercise 1")
    try:
        # parent_id for Stage 1, Exercise 1 ('Repeat After Me Phrases') is 7.
        # This is based on the initial data insertion script.
        query = supabase.table("ai_tutor_content_hierarchy").select("id, topic_number, title, title_urdu").eq("level", "topic").eq("parent_id", 7).eq("topic_number", phrase_id).single()
        response = await run_in_threadpool(query.execute)
        
        if response.data:
            db_phrase = response.data
            # Create a dictionary that is compatible with how it was used before
            # 'id' for the frontend/client is the topic_number.
            # 'db_id' is the actual primary key in the database for progress tracking.
            formatted_phrase = {
                "id": db_phrase.get("topic_number"),
                "db_id": db_phrase.get("id"),
                "phrase": db_phrase.get("title"),
                "urdu_meaning": db_phrase.get("title_urdu")
            }
            print(f"✅ [DB] Found phrase: {formatted_phrase['phrase']}")
            return formatted_phrase
        else:
            print(f"❌ [DB] Phrase with topic_number {phrase_id} not found for parent_id 7")
            return None
    except Exception as e:
        print(f"❌ [DB] Error fetching phrase from Supabase: {str(e)}")
        return None


async def check_exercise_completion(user_id: str) -> dict:
    """Check if user has completed the full Repeat After Me exercise (Stage 1, Exercise 1)"""
    print(f"🔍 [COMPLETION] Checking exercise completion for user: {user_id}")
    
    try:
        # Get total phrases count from Supabase
        total_phrases = 0
        try:
            # parent_id for 'Repeat After Me' is 7
            query = supabase.table("ai_tutor_content_hierarchy").select("id", count="exact").eq("level", "topic").eq("parent_id", 7)
            response = await run_in_threadpool(query.execute)
            if response.count is not None:
                total_phrases = response.count
                print(f"📊 [COMPLETION] Total phrases available from DB: {total_phrases}")
            else:
                print("⚠️ [COMPLETION] Could not get count from Supabase, falling back to default.")
                total_phrases = 50
        except Exception as e:
            print(f"❌ [COMPLETION] Error getting phrase count from DB: {str(e)}")
            total_phrases = 50  # Default fallback
        
        # Get user's progress for Stage 1 Exercise 1
        progress_result = await progress_tracker.get_user_topic_progress(
            user_id=user_id,
            stage_id=1,
            exercise_id=1
        )
        
        if not progress_result["success"]:
            print(f"❌ [COMPLETION] Failed to get progress: {progress_result.get('error')}")
            return {
                "exercise_completed": False,
                "progress_percentage": 0,
                "completed_topics": 0,
                "total_topics": total_phrases,
                "current_topic_id": 1,
                "error": progress_result.get("error", "Failed to get progress")
            }
        
        # Get current topic information
        current_topic_result = await progress_tracker.get_current_topic_for_exercise(
            user_id=user_id,
            stage_id=1,
            exercise_id=1
        )
        
        if not current_topic_result["success"]:
            print(f"❌ [COMPLETION] Failed to get current topic: {current_topic_result.get('error')}")
            return {
                "exercise_completed": False,
                "progress_percentage": 0,
                "completed_topics": 0,
                "total_topics": total_phrases,
                "current_topic_id": 1,
                "error": current_topic_result.get("error", "Failed to get current topic")
            }
        
        # Extract progress data
        topic_progress = progress_result.get("data", [])
        current_topic_id = current_topic_result.get("current_topic_id", 1)
        is_exercise_completed = current_topic_result.get("is_completed", False)
        
        # Calculate completion metrics
        completed_topics = len(topic_progress) if topic_progress else 0
        progress_percentage = (completed_topics / total_phrases) * 100 if total_phrases > 0 else 0
        
        # Determine if exercise is truly completed
        # Exercise is completed ONLY when ALL topics are completed (50 out of 50)
        # This means completed_topics must equal total_phrases exactly
        exercise_completed = completed_topics >= total_phrases and completed_topics > 0
        
        print(f"📊 [COMPLETION] Completion status calculated:")
        print(f"   - Total phrases: {total_phrases}")
        print(f"   - Completed topics: {completed_topics}")
        print(f"   - Current topic ID: {current_topic_id}")
        print(f"   - Progress percentage: {progress_percentage:.1f}%")
        print(f"   - Exercise completed: {exercise_completed}")
        
        # Additional logging for completion logic
        if completed_topics >= total_phrases:
            print(f"🎉 [COMPLETION] All {total_phrases} topics completed! Exercise is finished!")
        elif completed_topics > 0:
            print(f"📈 [COMPLETION] {completed_topics}/{total_phrases} topics completed. Exercise in progress...")
        else:
            print(f"🆕 [COMPLETION] No topics completed yet. Exercise just started.")
        
        return {
            "exercise_completed": exercise_completed,
            "progress_percentage": round(progress_percentage, 1),
            "completed_topics": completed_topics,
            "total_topics": total_phrases,
            "current_topic_id": current_topic_id,
            "stage_id": 1,
            "exercise_id": 1,
            "exercise_name": "Repeat After Me",
            "stage_name": "Stage 1 – A1 Beginner",
            "completion_date": topic_progress[-1].get("created_at") if topic_progress and exercise_completed else None
        }
        
    except Exception as e:
        print(f"❌ [COMPLETION] Error checking exercise completion: {str(e)}")
        return {
            "exercise_completed": False,
            "progress_percentage": 0,
            "completed_topics": 0,
            "total_topics": 50,
            "current_topic_id": 1,
            "error": f"Failed to check completion status: {str(e)}"
        }


@router.get("/phrases")
async def get_all_phrases(current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)):
    """Get all available phrases for Repeat After Me exercise from Supabase"""
    print("🔄 [API] GET /phrases endpoint called")
    try:
        print("🔄 [DB] Fetching all phrases for Stage 1, Exercise 1 from Supabase")
        # parent_id for 'Repeat After Me' is 7
        query = supabase.table("ai_tutor_content_hierarchy").select("id, topic_number, title, title_urdu, description, category, difficulty").eq("level", "topic").eq("parent_id", 7).order("topic_number", desc=False)
        response = await run_in_threadpool(query.execute)

        if response.data:
            # Format data to be backward compatible with old JSON structure.
            # The client expects 'id' to be the topic number (1-50).
            phrases = [
                {
                    "id": p.get("topic_number"),
                    "db_id": p.get("id"),
                    "phrase": p.get("title"),
                    "urdu_meaning": p.get("title_urdu"),
                    "description": p.get("description"),
                    "category": p.get("category"),
                    "difficulty": p.get("difficulty")
                } for p in response.data
            ]
            print(f"✅ [DB] Successfully loaded {len(phrases)} phrases from Supabase")
            return {"phrases": phrases}
        else:
            print("❌ [DB] No phrases found for Stage 1, Exercise 1")
            return {"phrases": []}
    except Exception as e:
        print(f"❌ [API] Error in get_all_phrases: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to load phrases from database: {str(e)}")

@router.get("/phrases/{phrase_id}")
async def get_phrase(phrase_id: int, current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)):
    """Get a specific phrase by ID"""
    print(f"🔄 [API] GET /phrases/{phrase_id} endpoint called")
    try:
        phrase_data = await get_phrase_by_id(phrase_id)
        if not phrase_data:
            print(f"❌ [API] Phrase {phrase_id} not found")
            raise HTTPException(status_code=404, detail="Phrase not found")
        print(f"✅ [API] Returning phrase: {phrase_data['phrase']}")
        return {
            "id": phrase_data['id'], 
            "phrase": phrase_data['phrase'],
            "urdu_meaning": phrase_data['urdu_meaning']
        }
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
async def repeat_after_me(phrase_id: int, current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)):
    print(f"🔄 [API] POST /repeat-after-me/{phrase_id} endpoint called")
    try:
        phrase_data = await get_phrase_by_id(phrase_id)
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
async def evaluate_audio(
    request: AudioEvaluationRequest,
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)
):
    print(f"🔄 [API] POST /evaluate-audio endpoint called")
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
        # Get the expected phrase
        phrase_data = await get_phrase_by_id(request.phrase_id)
        if not phrase_data:
            print(f"❌ [API] Phrase {request.phrase_id} not found")
            raise HTTPException(status_code=404, detail="Phrase not found")

        expected_phrase = phrase_data['phrase']
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
            
            # Check exercise completion status even for short audio
            exercise_completion_status = None
            if request.user_id and request.user_id.strip():
                try:
                    exercise_completion_status = await check_exercise_completion(request.user_id)
                except Exception as completion_error:
                    print(f"⚠️ [API] Failed to check exercise completion: {str(completion_error)}")
            
            return {
                "success": False,
                "error": "no_speech_detected",
                "message": "No speech detected. Please try again.",
                "expected_phrase": expected_phrase,
                "exercise_completion": exercise_completion_status
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
                
                # Check exercise completion status even for unclear speech
                exercise_completion_status = None
                if request.user_id and request.user_id.strip():
                    try:
                        exercise_completion_status = await check_exercise_completion(request.user_id)
                    except Exception as completion_error:
                        print(f"⚠️ [API] Failed to check exercise completion: {str(completion_error)}")
                
                return {
                    "success": False,
                    "error": "no_speech_detected",
                    "message": "No clear speech detected. Please speak more clearly.",
                    "expected_phrase": expected_phrase,
                    "exercise_completion": exercise_completion_status
                }

        except Exception as e:
            print(f"❌ [API] Error transcribing audio: {str(e)}")
            
            # Check exercise completion status even for transcription errors
            exercise_completion_status = None
            if request.user_id and request.user_id.strip():
                try:
                    exercise_completion_status = await check_exercise_completion(request.user_id)
                except Exception as completion_error:
                    print(f"⚠️ [API] Failed to check exercise completion: {str(completion_error)}")
            
            return {
                "success": False,
                "error": "transcription_failed",
                "message": "Failed to process audio. Please try again.",
                "expected_phrase": expected_phrase,
                "exercise_completion": exercise_completion_status
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
                        topic_id=phrase_data['id'], # Use the topic_number (e.g., 26)
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
            
            # Check if user has completed the full exercise
            exercise_completion_status = await check_exercise_completion(request.user_id)
            
            return {
                "success": True,
                "expected_phrase": expected_phrase,
                "user_text": user_text,
                "evaluation": evaluation,
                "progress_recorded": progress_recorded,
                "unlocked_content": unlocked_content,
                "exercise_completion": exercise_completion_status
            }

        except Exception as e:
            print(f"❌ [API] Error evaluating response: {str(e)}")
            
            # Even if evaluation fails, check exercise completion status
            exercise_completion_status = None
            if request.user_id and request.user_id.strip():
                try:
                    exercise_completion_status = await check_exercise_completion(request.user_id)
                except Exception as completion_error:
                    print(f"⚠️ [API] Failed to check exercise completion: {str(completion_error)}")
            
            return {
                "success": False,
                "error": "evaluation_failed",
                "message": "Failed to evaluate pronunciation. Please try again.",
                "expected_phrase": expected_phrase,
                "user_text": user_text,
                "exercise_completion": exercise_completion_status
            }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [API] Unexpected error in evaluate_audio: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
