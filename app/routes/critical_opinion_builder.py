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
from app.services.feedback import evaluate_response_ex3_stage6
from app.supabase_client import supabase, progress_tracker
from app.auth_middleware import get_current_user, require_student, require_admin_or_teacher_or_student

router = APIRouter()

class AudioEvaluationRequest(BaseModel):
    audio_base64: str
    topic_id: int
    filename: str
    user_id: str
    time_spent_seconds: int
    urdu_used: bool

async def get_topic_by_id_from_db(topic_id: int):
    """Fetch a critical opinion topic from Supabase by its topic_number for Stage 6, Exercise 3."""
    print(f"🔍 [DB] Looking for topic with topic_number (ID): {topic_id} for Stage 6, Exercise 3")
    try:
        # parent_id for Stage 6, Exercise 3 ('Advanced Academic Debate') is 24.
        query = supabase.table("ai_tutor_content_hierarchy").select("id, topic_number, title, topic_data, category, difficulty").eq("level", "topic").eq("parent_id", 24).eq("topic_number", topic_id).single()
        response = await run_in_threadpool(query.execute)
        
        if response.data:
            db_item = response.data
            topic_data = db_item.get("topic_data", {})
            
            formatted_item = {
                "id": db_item.get("topic_number"),
                "db_id": db_item.get("id"),
                "topic": db_item.get("title"),
                "category": db_item.get("category"),
                "difficulty": db_item.get("difficulty"),
                "topic_type": topic_data.get("topic_type"),
                "controversy_level": topic_data.get("controversy_level"),
                "expected_structure": topic_data.get("expected_structure"),
                "expected_keywords": topic_data.get("expected_keywords", []),
                "vocabulary_focus": topic_data.get("vocabulary_focus", []),
                "academic_expressions": topic_data.get("academic_expressions", []),
                "model_response": topic_data.get("model_response"),
                "evaluation_criteria": topic_data.get("evaluation_criteria", {})
            }
            print(f"✅ [DB] Found topic: {formatted_item['topic']}")
            return formatted_item
        else:
            print(f"❌ [DB] Topic with topic_number {topic_id} not found for parent_id 24")
            return None
    except Exception as e:
        print(f"❌ [DB] Error fetching topic from Supabase: {str(e)}")
        return None


async def check_exercise_completion(user_id: str) -> dict:
    """Check if user has completed the full Critical Opinion Builder exercise (Stage 6, Exercise 3)"""
    print(f"🔍 [COMPLETION] Checking exercise completion for user: {user_id}")
    
    try:
        # Get total topics count from Supabase
        total_topics = 0
        try:
            # parent_id for 'Advanced Academic Debate' is 24
            query = supabase.table("ai_tutor_content_hierarchy").select("id", count="exact").eq("level", "topic").eq("parent_id", 24)
            response = await run_in_threadpool(query.execute)
            if response.count is not None:
                total_topics = response.count
                print(f"📊 [COMPLETION] Total topics available from DB: {total_topics}")
            else:
                print("⚠️ [COMPLETION] Could not get count from Supabase, falling back to default.")
                total_topics = 10 # Default fallback
        except Exception as e:
            print(f"❌ [COMPLETION] Error getting topic count from DB: {str(e)}")
            total_topics = 10 # Default fallback
        
        # Get user's progress for stage 6, exercise 3
        progress_result = await progress_tracker.get_user_topic_progress(
            user_id=user_id,
            stage_id=6,
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
                "stage_id": 6,
                "exercise_id": 3,
                "exercise_name": "Critical Opinion Builder",
                "stage_name": "Stage 6 – C2 Mastery",
                "error": progress_result.get("error", "Failed to get progress")
            }
        
        user_progress = progress_result.get("data", [])
        completed_topics = len([record for record in user_progress if record.get("completed", False)])
        
        # Get current topic ID
        current_topic_result = await progress_tracker.get_current_topic_for_exercise(
            user_id=user_id,
            stage_id=6,
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
        print(f"   - Total topics: {total_topics}")
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
            "stage_id": 6,
            "exercise_id": 3,
            "exercise_name": "Critical Opinion Builder",
            "stage_name": "Stage 6 – C2 Mastery"
        }
        
    except Exception as e:
        print(f"❌ [COMPLETION] Error checking exercise completion: {str(e)}")
        return {
            "exercise_completed": False,
            "progress_percentage": 0.0,
            "completed_topics": 0,
            "total_topics": 0,
            "current_topic_id": 1,
            "stage_id": 6,
            "exercise_id": 3,
            "exercise_name": "Critical Opinion Builder",
            "stage_name": "Stage 6 – C2 Mastery",
            "error": str(e)
        }

@router.get("/critical-opinion-topics")
async def get_all_topics(current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)):
    """Get all available topics for Critical Opinion Builder exercise"""
    print("🔄 [API] GET /critical-opinion-topics endpoint called")
    try:
        print("🔄 [DB] Fetching all topics for Stage 6, Exercise 3 from Supabase")
        # parent_id for 'Advanced Academic Debate' is 24
        query = supabase.table("ai_tutor_content_hierarchy").select("id, topic_number, title, category, difficulty").eq("level", "topic").eq("parent_id", 24).order("topic_number", desc=False)
        response = await run_in_threadpool(query.execute)

        if response.data:
            topics = []
            for item in response.data:
                topics.append({
                    "id": item.get("topic_number"),
                    "db_id": item.get("id"),
                    "topic": item.get("title"),
                    "category": item.get("category"),
                    "difficulty": item.get("difficulty"),
                })
            print(f"✅ [DB] Successfully loaded {len(topics)} topics from Supabase")
            return {"topics": topics}
        else:
            print("❌ [DB] No topics found for Stage 6, Exercise 3")
            return {"topics": []}
    except Exception as e:
        print(f"❌ [API] Error in get_all_topics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to load topics from database: {str(e)}")

@router.get("/critical-opinion-topics/{topic_id}")
async def get_topic(topic_id: int, current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)):
    """Get a specific topic by ID"""
    print(f"🔄 [API] GET /critical-opinion-topics/{topic_id} endpoint called")
    try:
        topic_data = await get_topic_by_id_from_db(topic_id)
        if not topic_data:
            print(f"❌ [API] Topic {topic_id} not found")
            raise HTTPException(status_code=404, detail="Topic not found")
        print(f"✅ [API] Returning topic: {topic_data['topic']}")
        return topic_data
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [API] Error in get_topic: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post(
    "/critical-opinion-builder/{topic_id}",
    summary="Convert topic to audio for Critical Opinion Builder Exercise",
    description="""
This endpoint is part of Stage 6 - Exercise 3 (Critical Opinion Builder). 
It takes a topic ID from a predefined list, converts the corresponding topic into speech (TTS),
and returns the generated audio file as the response.
""",
    tags=["Stage 6 - Exercise 3 (Critical Opinion Builder)"]
)
async def critical_opinion_builder(topic_id: int, current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)):
    print(f"🔄 [API] POST /critical-opinion-builder/{topic_id} endpoint called")
    try:
        topic_data = await get_topic_by_id_from_db(topic_id)
        if not topic_data:
            print(f"❌ [API] Topic {topic_id} not found")
            raise HTTPException(status_code=404, detail="Topic not found")

        topic_text = topic_data['topic']
        print(f"🎤 [API] Converting topic to speech: '{topic_text}'")
        audio_content = await synthesize_speech_exercises(topic_text)
        print(f"✅ [API] Audio content generated, size: {len(audio_content)} bytes")
        
        # Convert to base64 for React Native compatibility
        audio_base64 = base64.b64encode(audio_content).decode('utf-8')
        print(f"✅ [API] Audio converted to base64, length: {len(audio_base64)}")
        
        # Return base64 string directly
        return {"audio_base64": audio_base64}
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [API] Error in critical_opinion_builder: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post(
    "/evaluate-critical-opinion",
    summary="Evaluate user's audio recording against expected keywords and argument structure",
    description="""
This endpoint evaluates the user's recorded audio against the expected keywords and argument structure for critical opinion topics.
It performs speech-to-text conversion and provides comprehensive feedback on the response quality.
Also records progress tracking data in Supabase database.
""",
    tags=["Stage 6 - Exercise 3 (Critical Opinion Builder)"]
)
async def evaluate_critical_opinion(
    request: AudioEvaluationRequest,
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)
):
    print(f"🔄 [API] POST /evaluate-critical-opinion endpoint called")
    print(f"📝 [API] Request details: topic_id={request.topic_id}, filename={request.filename}")
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
        # Get the expected topic and keywords
        topic_data = await get_topic_by_id_from_db(request.topic_id)
        if not topic_data:
            print(f"❌ [API] Topic {request.topic_id} not found")
            raise HTTPException(status_code=404, detail="Topic not found")

        expected_keywords = topic_data['expected_keywords']
        vocabulary_focus = topic_data['vocabulary_focus']
        academic_expressions = topic_data['academic_expressions']
        topic_text = topic_data['topic']
        model_response = topic_data['model_response']
        expected_structure = topic_data['expected_structure']
        
        print(f"✅ [API] Expected keywords: {expected_keywords}")
        print(f"✅ [API] Vocabulary focus: {vocabulary_focus}")
        print(f"✅ [API] Academic expressions: {academic_expressions}")
        print(f"✅ [API] Topic: '{topic_text}'")
        print(f"✅ [API] Expected structure: '{expected_structure}'")

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
                "topic": topic_text
            }

        # Transcribe the audio
        try:
            print("🔄 [API] Transcribing audio...")
            transcription_result = transcribe_audio_bytes_eng_only(audio_bytes)
            user_text = transcription_result.get("text", "").strip()
            print(f"✅ [API] Transcription result: '{user_text}'")
            
            # Check if transcription is empty or too short
            if not user_text or len(user_text) < 10:
                print(f"⚠️ [API] Transcription too short or empty: '{user_text}'")
                return {
                    "success": False,
                    "error": "no_speech_detected",
                    "message": "No clear speech detected. Please speak more clearly and provide a complete opinion.",
                    "expected_keywords": expected_keywords,
                    "topic": topic_text
                }

        except Exception as e:
            print(f"❌ [API] Error transcribing audio: {str(e)}")
            return {
                "success": False,
                "error": "transcription_failed",
                "message": "Failed to process audio. Please try again.",
                "expected_keywords": expected_keywords,
                "topic": topic_text
            }

        # Evaluate the response
        try:
            print(f"🔄 [API] Evaluating response: '{user_text}' vs expected keywords: {expected_keywords}")
            evaluation = evaluate_response_ex3_stage6(
                user_text, 
                topic_text, 
                expected_keywords, 
                vocabulary_focus, 
                academic_expressions, 
                model_response, 
                expected_structure
            )
            print(f"✅ [API] Evaluation completed: {evaluation}")
            
            # Extract evaluation details for progress tracking
            score = evaluation.get("score", 0)
            is_correct = evaluation.get("is_correct", False)
            completed = evaluation.get("completed", False)
            suggested_improvement = evaluation.get("suggested_improvement", "")
            keyword_matches = evaluation.get("keyword_matches", 0)
            total_keywords = evaluation.get("total_keywords", len(expected_keywords))
            academic_expressions_used = evaluation.get("academic_expressions_used", 0)
            total_academic_expressions = evaluation.get("total_academic_expressions", len(academic_expressions))
            
            print(f"📊 [API] Evaluation details: score={score}, is_correct={is_correct}, completed={completed}")
            print(f"📊 [API] Keyword matches: {keyword_matches}/{total_keywords}")
            print(f"📊 [API] Academic expressions: {academic_expressions_used}/{total_academic_expressions}")
            
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
                    time_spent = max(1, min(request.time_spent_seconds, 900))  # Between 1-900 seconds for critical opinion
                    if time_spent != request.time_spent_seconds:
                        print(f"⚠️ [API] Adjusted time spent from {request.time_spent_seconds} to {time_spent} seconds")
                    
                    # Record the topic attempt
                    progress_result = await progress_tracker.record_topic_attempt(
                        user_id=request.user_id,
                        stage_id=6,  # Stage 6
                        exercise_id=3,  # Exercise 3 (Critical Opinion Builder)
                        topic_id=topic_data['db_id'],
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
                print(f"📊 [CRITICAL_OPINION] Exercise completion status: {exercise_completion_status}")
            except Exception as completion_error:
                print(f"⚠️ [CRITICAL_OPINION] Failed to check exercise completion: {str(completion_error)}")
                exercise_completion_status = {
                    "exercise_completed": False,
                    "progress_percentage": 0.0,
                    "completed_topics": 0,
                    "total_topics": 0,
                    "current_topic_id": 1,
                    "stage_id": 6,
                    "exercise_id": 3,
                    "exercise_name": "Critical Opinion Builder",
                    "stage_name": "Stage 6 – C2 Mastery",
                    "error": str(completion_error)
                }
            
            return {
                "success": True,
                "topic": topic_text,
                "expected_keywords": expected_keywords,
                "vocabulary_focus": vocabulary_focus,
                "academic_expressions": academic_expressions,
                "user_text": user_text,
                "evaluation": evaluation,
                "suggested_improvement": suggested_improvement,
                "progress_recorded": progress_recorded,
                "unlocked_content": unlocked_content,
                "keyword_matches": keyword_matches,
                "total_keywords": total_keywords,
                "academic_expressions_used": academic_expressions_used,
                "total_academic_expressions": total_academic_expressions,
                "exercise_completion": exercise_completion_status
            }

        except Exception as e:
            print(f"❌ [API] Error evaluating response: {str(e)}")
            return {
                "success": False,
                "error": "evaluation_failed",
                "message": "Failed to evaluate response. Please try again.",
                "expected_keywords": expected_keywords,
                "topic": topic_text,
                "user_text": user_text
            }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [API] Unexpected error in evaluate_critical_opinion: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}") 