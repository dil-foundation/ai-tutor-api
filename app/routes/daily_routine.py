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
from app.services.feedback import evaluate_response_ex1_stage2
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
    """Fetch a daily routine topic from Supabase by its topic_number for Stage 2, Exercise 1."""
    print(f"🔍 [DB] Looking for phrase with topic_number (ID): {phrase_id} for Stage 2, Exercise 1")
    try:
        # parent_id for Stage 2, Exercise 1 ('Daily Routine Narration') is 10.
        query = supabase.table("ai_tutor_content_hierarchy").select("id, topic_number, title, topic_data, category, difficulty").eq("level", "topic").eq("parent_id", 10).eq("topic_number", phrase_id).single()
        response = await run_in_threadpool(query.execute)
        
        if response.data:
            db_phrase = response.data
            topic_data = db_phrase.get("topic_data", {})
            
            formatted_phrase = {
                "id": db_phrase.get("topic_number"),
                "db_id": db_phrase.get("id"),
                "title": db_phrase.get("title"),
                "phrase": topic_data.get("phrase"),
                "phrase_urdu": topic_data.get("phrase_urdu"),
                "example": topic_data.get("example"),
                "example_urdu": topic_data.get("example_urdu"),
                "keywords": topic_data.get("keywords"),
                "keywords_urdu": topic_data.get("keywords_urdu"),
                "category": db_phrase.get("category"),
                "difficulty": db_phrase.get("difficulty"),
                "tense_focus": topic_data.get("tense_focus"),
                "sentence_structure": topic_data.get("sentence_structure")
            }
            print(f"✅ [DB] Found phrase: {formatted_phrase['phrase']}")
            return formatted_phrase
        else:
            print(f"❌ [DB] Phrase with topic_number {phrase_id} not found for parent_id 10")
            return None
    except Exception as e:
        print(f"❌ [DB] Error fetching phrase from Supabase: {str(e)}")
        return None


async def check_exercise_completion(user_id: str) -> dict:
    """Check if user has completed the full Daily Routine exercise (Stage 2, Exercise 1)"""
    print(f"🔍 [COMPLETION] Checking exercise completion for user: {user_id}")
    
    try:
        # Get total routines count from Supabase
        total_routines = 0
        try:
            # parent_id for 'Daily Routine Narration' is 10
            query = supabase.table("ai_tutor_content_hierarchy").select("id", count="exact").eq("level", "topic").eq("parent_id", 10)
            response = await run_in_threadpool(query.execute)
            if response.count is not None:
                total_routines = response.count
                print(f"📊 [COMPLETION] Total routines available from DB: {total_routines}")
            else:
                print("⚠️ [COMPLETION] Could not get count from Supabase, falling back to default.")
                total_routines = 20
        except Exception as e:
            print(f"❌ [COMPLETION] Error getting routine count from DB: {str(e)}")
            total_routines = 20  # Default fallback based on data file
        
        # Get user's progress for Stage 2 Exercise 1
        progress_result = await progress_tracker.get_user_topic_progress(
            user_id=user_id,
            stage_id=2,
            exercise_id=1
        )
        
        if not progress_result["success"]:
            print(f"❌ [COMPLETION] Failed to get progress: {progress_result.get('error')}")
            return {
                "exercise_completed": False,
                "progress_percentage": 0,
                "completed_topics": 0,
                "total_topics": total_routines,
                "current_topic_id": 1,
                "error": progress_result.get("error", "Failed to get progress")
            }
        
        # Get current topic information
        current_topic_result = await progress_tracker.get_current_topic_for_exercise(
            user_id=user_id,
            stage_id=2,
            exercise_id=1
        )
        
        if not current_topic_result["success"]:
            print(f"❌ [COMPLETION] Failed to get current topic: {current_topic_result.get('error')}")
            return {
                "exercise_completed": False,
                "progress_percentage": 0,
                "completed_topics": 0,
                "total_topics": total_routines,
                "current_topic_id": 1,
                "error": current_topic_result.get("error", "Failed to get current topic")
            }
        
        # Extract progress data
        topic_progress = progress_result.get("data", [])
        current_topic_id = current_topic_result.get("current_topic_id", 1)
        is_exercise_completed = current_topic_result.get("is_completed", False)
        
        # Calculate completion metrics
        completed_topics = len(topic_progress) if topic_progress else 0
        progress_percentage = (completed_topics / total_routines) * 100 if total_routines > 0 else 0
        
        # Determine if exercise is truly completed
        # Exercise is completed ONLY when ALL topics are completed
        exercise_completed = completed_topics >= total_routines and completed_topics > 0
        
        print(f"📊 [COMPLETION] Completion status calculated:")
        print(f"   - Total routines: {total_routines}")
        print(f"   - Completed topics: {completed_topics}")
        print(f"   - Current topic ID: {current_topic_id}")
        print(f"   - Progress percentage: {progress_percentage:.1f}%")
        print(f"   - Exercise completed: {exercise_completed}")
        
        # Additional logging for completion logic
        if completed_topics >= total_routines:
            print(f"🎉 [COMPLETION] All {total_routines} routines completed! Exercise is finished!")
        elif completed_topics > 0:
            print(f"📈 [COMPLETION] {completed_topics}/{total_routines} routines completed. Exercise in progress...")
        else:
            print(f"🆕 [COMPLETION] No routines completed yet. Exercise just started.")
        
        return {
            "exercise_completed": exercise_completed,
            "progress_percentage": round(progress_percentage, 1),
            "completed_topics": completed_topics,
            "total_topics": total_routines,
            "current_topic_id": current_topic_id,
            "stage_id": 2,
            "exercise_id": 1,
            "exercise_name": "Daily Routine Narration",
            "stage_name": "Stage 2 – A2 Elementary",
            "completion_date": topic_progress[-1].get("created_at") if topic_progress and exercise_completed else None
        }
        
    except Exception as e:
        print(f"❌ [COMPLETION] Error checking exercise completion: {str(e)}")
        return {
            "exercise_completed": False,
            "progress_percentage": 0,
            "completed_topics": 0,
            "total_topics": 15,
            "current_topic_id": 1,
            "error": f"Failed to check completion status: {str(e)}"
        }


@router.get("/daily-routine-phrases")
async def get_all_phrases(current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)):
    """Get all available phrases for Daily Routine exercise from Supabase"""
    print("🔄 [API] GET /daily-routine-phrases endpoint called")
    try:
        print("🔄 [DB] Fetching all phrases for Stage 2, Exercise 1 from Supabase")
        # parent_id for 'Daily Routine Narration' is 10
        query = supabase.table("ai_tutor_content_hierarchy").select("id, topic_number, title, topic_data, category, difficulty").eq("level", "topic").eq("parent_id", 10).order("topic_number", desc=False)
        response = await run_in_threadpool(query.execute)

        if response.data:
            # Format data to be backward compatible with the old JSON structure.
            phrases = []
            for p in response.data:
                topic_data = p.get("topic_data", {})
                phrases.append({
                    "id": p.get("topic_number"),
                    "db_id": p.get("id"),
                    "title": p.get("title"),
                    "phrase": topic_data.get("phrase"),
                    "phrase_urdu": topic_data.get("phrase_urdu"),
                    "example": topic_data.get("example"),
                    "example_urdu": topic_data.get("example_urdu"),
                    "keywords": topic_data.get("keywords"),
                    "keywords_urdu": topic_data.get("keywords_urdu"),
                    "category": p.get("category"),
                    "difficulty": p.get("difficulty"),
                    "tense_focus": topic_data.get("tense_focus"),
                    "sentence_structure": topic_data.get("sentence_structure")
                })
            print(f"✅ [DB] Successfully loaded {len(phrases)} phrases from Supabase")
            return {"phrases": phrases}
        else:
            print("❌ [DB] No phrases found for Stage 2, Exercise 1")
            return {"phrases": []}
    except Exception as e:
        print(f"❌ [API] Error in get_all_phrases: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to load phrases from database: {str(e)}")

@router.get("/daily-routine-phrases/{phrase_id}")
async def get_phrase(phrase_id: int, current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)):
    """Get a specific phrase by ID"""
    print(f"🔄 [API] GET /daily-routine-phrases/{phrase_id} endpoint called")
    try:
        phrase_data = await get_phrase_by_id(phrase_id)
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
        phrase_data = await get_phrase_by_id(request.phrase_id)
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
                        topic_id=phrase_data['id'], # Use the actual database ID
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
                "grammar_score": grammar_score,
                "exercise_completed": exercise_completion_status["exercise_completed"]
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