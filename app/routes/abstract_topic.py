from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import json
import base64
from typing import List, Optional, Dict, Any
from fastapi.concurrency import run_in_threadpool
from app.services.feedback import evaluate_response_ex1_stage4
from app.services.stt import transcribe_audio_bytes_eng_only
from app.services.tts import synthesize_speech_exercises
from app.supabase_client import supabase, progress_tracker
from app.auth_middleware import get_current_user, require_student,require_admin_or_teacher_or_student
import os

router = APIRouter()

# Data models
class AudioEvaluationRequest(BaseModel):
    audio_base64: str
    topic_id: int
    filename: str
    user_id: str
    time_spent_seconds: int
    urdu_used: bool

# Load topics data
async def get_topic_by_id_from_db(topic_id: int):
    """Fetch an abstract topic from Supabase by its topic_number for Stage 4, Exercise 1."""
    print(f"🔍 [DB] Looking for topic with topic_number (ID): {topic_id} for Stage 4, Exercise 1")
    try:
        # parent_id for Stage 4, Exercise 1 ('Business Presentation Skills') is 16.
        query = supabase.table("ai_tutor_content_hierarchy").select("id, topic_number, title, title_urdu, topic_data, category, difficulty").eq("level", "topic").eq("parent_id", 16).eq("topic_number", topic_id).single()
        response = await run_in_threadpool(query.execute)
        
        if response.data:
            db_topic = response.data
            topic_data = db_topic.get("topic_data", {})
            
            formatted_topic = {
                "id": db_topic.get("topic_number"),
                "db_id": db_topic.get("id"),
                "topic": db_topic.get("title"),
                "topic_urdu": db_topic.get("title_urdu"),
                "category": db_topic.get("category"),
                "difficulty": db_topic.get("difficulty"),
                "speaking_duration": topic_data.get("speaking_duration"),
                "thinking_time": topic_data.get("thinking_time"),
                "expected_structure": topic_data.get("expected_structure"),
                "key_connectors": topic_data.get("key_connectors", []),
                "vocabulary_focus": topic_data.get("vocabulary_focus", []),
                "model_response": topic_data.get("model_response"),
                "model_response_urdu": topic_data.get("model_response_urdu"),
                "evaluation_criteria": topic_data.get("evaluation_criteria", {}),
                "learning_objectives": topic_data.get("learning_objectives", [])
            }
            print(f"✅ [DB] Found topic: {formatted_topic['topic']}")
            return formatted_topic
        else:
            print(f"❌ [DB] Topic with topic_number {topic_id} not found for parent_id 16")
            return None
    except Exception as e:
        print(f"❌ [DB] Error fetching topic from Supabase: {str(e)}")
        return None


async def check_exercise_completion(user_id: str) -> dict:
    """Check if user has completed the full Abstract Topic exercise (Stage 4, Exercise 1)"""
    print(f"🔍 [COMPLETION] Checking exercise completion for user: {user_id}")
    
    try:
        # Get total topics count from Supabase
        total_topics = 0
        try:
            # parent_id for 'Business Presentation Skills' is 16
            query = supabase.table("ai_tutor_content_hierarchy").select("id", count="exact").eq("level", "topic").eq("parent_id", 16)
            response = await run_in_threadpool(query.execute)
            if response.count is not None:
                total_topics = response.count
                print(f"📊 [COMPLETION] Total topics available from DB: {total_topics}")
            else:
                print("⚠️ [COMPLETION] Could not get count from Supabase, falling back to default.")
                total_topics = 5
        except Exception as e:
            print(f"❌ [COMPLETION] Error getting topic count from DB: {str(e)}")
            total_topics = 5 # Default fallback
        
        # Get user's progress for stage 4, exercise 1
        progress_result = await progress_tracker.get_user_topic_progress(
            user_id=user_id,
            stage_id=4,
            exercise_id=1
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
                "exercise_id": 1,
                "exercise_name": "Abstract Topic Monologue",
                "stage_name": "Stage 4 – B2 Upper Intermediate",
                "error": progress_result.get("error", "Failed to get progress")
            }
        
        user_progress = progress_result.get("data", [])
        completed_topics = len([record for record in user_progress if record.get("completed", False)])
        
        # Get current topic ID
        current_topic_result = await progress_tracker.get_current_topic_for_exercise(
            user_id=user_id,
            stage_id=4,
            exercise_id=1
        )
        
        current_topic_id = 1
        if current_topic_result["success"]:
            current_topic_id = current_topic_result.get("current_topic_id", 1)
        
        # Calculate progress percentage
        progress_percentage = (completed_topics / total_topics * 100) if total_topics > 0 else 0.0
        
        # Determine if exercise is truly completed
        # Exercise is completed ONLY when ALL topics are completed
        exercise_completed = completed_topics >= total_topics and total_topics > 0
        
        print(f"📊 [COMPLETION] Completion status calculated:")
        print(f"   - Total topics: {total_topics}")
        print(f"   - Completed topics: {completed_topics}")
        print(f"   - Current topic ID: {current_topic_id}")
        print(f"   - Progress percentage: {progress_percentage:.1f}%")
        print(f"   - Exercise completed: {exercise_completed}")
        
        # Additional logging for completion logic
        if completed_topics >= total_topics:
            print(f"🎉 [COMPLETION] User has completed all {total_topics} topics!")
        else:
            print(f"📚 [COMPLETION] User still needs to complete {total_topics - completed_topics} more topics")
        
        return {
            "exercise_completed": exercise_completed,
            "progress_percentage": progress_percentage,
            "completed_topics": completed_topics,
            "total_topics": total_topics,
            "current_topic_id": current_topic_id,
            "stage_id": 4,
            "exercise_id": 1,
            "exercise_name": "Abstract Topic Monologue",
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
            "exercise_id": 1,
            "exercise_name": "Abstract Topic Monologue",
            "stage_name": "Stage 4 – B2 Upper Intermediate",
            "error": str(e)
        }


@router.get(
    "/abstract-topics",
    summary="Get all abstract topics",
    description="Retrieve all available abstract topics for Stage 4 Exercise 1",
    tags=["Stage 4 - Exercise 1 (Abstract Topic Monologue)"]
)
async def get_abstract_topics(current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)):
    """Get all abstract topics from Supabase"""
    print("🔄 [API] GET /abstract-topics endpoint called")
    
    try:
        print("🔄 [DB] Fetching all topics for Stage 4, Exercise 1 from Supabase")
        query = supabase.table("ai_tutor_content_hierarchy").select("id, topic_number, title, title_urdu, topic_data, category, difficulty").eq("level", "topic").eq("parent_id", 16).order("topic_number", desc=False)
        response = await run_in_threadpool(query.execute)
        
        if response.data:
            topics = []
            for t in response.data:
                topic_data = t.get("topic_data", {})
                topics.append({
                    "id": t.get("topic_number"),
                    "db_id": t.get("id"),
                    "topic": t.get("title"),
                    "topic_urdu": t.get("title_urdu"),
                    "category": t.get("category"),
                    "difficulty": t.get("difficulty"),
                    "speaking_duration": topic_data.get("speaking_duration"),
                    "thinking_time": topic_data.get("thinking_time"),
                    "expected_structure": topic_data.get("expected_structure"),
                    "key_connectors": topic_data.get("key_connectors", []),
                    "vocabulary_focus": topic_data.get("vocabulary_focus", []),
                    "model_response": topic_data.get("model_response"),
                    "model_response_urdu": topic_data.get("model_response_urdu"),
                    "evaluation_criteria": topic_data.get("evaluation_criteria", {}),
                    "learning_objectives": topic_data.get("learning_objectives", [])
                })
            print(f"✅ [DB] Successfully loaded {len(topics)} topics from Supabase")
            return {
                "topics": topics,
                "total_count": len(topics)
            }
        else:
            print("❌ [DB] No topics found for Stage 4, Exercise 1")
            return {"topics": [], "total_count": 0}
    except Exception as e:
        print(f"❌ [API] Error retrieving topics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to load topics from database: {str(e)}")

@router.get(
    "/abstract-topics/{topic_id}",
    summary="Get specific abstract topic",
    description="Retrieve a specific abstract topic by ID",
    tags=["Stage 4 - Exercise 1 (Abstract Topic Monologue)"]
)
async def get_abstract_topic(topic_id: int, current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)):
    """Get a specific abstract topic by ID"""
    print(f"🔄 [API] GET /abstract-topics/{topic_id} endpoint called")
    
    try:
        topic = await get_topic_by_id_from_db(topic_id)
        if not topic:
            print(f"❌ [API] Topic {topic_id} not found")
            raise HTTPException(status_code=404, detail="Topic not found")
        
        print(f"✅ [API] Retrieved topic: {topic['topic']}")
        return topic
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [API] Error retrieving topic: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to load topic: {str(e)}")

@router.post(
    "/abstract-topic/{topic_id}",
    summary="Generate audio for abstract topic",
    description="Generate audio narration for a specific abstract topic",
    tags=["Stage 4 - Exercise 1 (Abstract Topic Monologue)"]
)
async def generate_abstract_topic_audio(
    topic_id: int,
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)
):
    """Generate audio for an abstract topic"""
    print(f"🔄 [API] POST /abstract-topic/{topic_id} endpoint called")
    
    try:
        topic = await get_topic_by_id_from_db(topic_id)
        if not topic:
            print(f"❌ [API] Topic {topic_id} not found")
            raise HTTPException(status_code=404, detail="Topic not found")
        
        # Create audio text from topic
        audio_text = f"""
        {topic['topic']}
        
        This is an abstract topic for Stage 4 Exercise 1. You have 10 seconds to think about your response, then speak for 60 to 90 seconds expressing your opinion on this topic.
        
        Remember to use transitional phrases like {', '.join(topic['key_connectors'][:3])} and focus on vocabulary related to {', '.join(topic['vocabulary_focus'][:3])}.
        
        Please provide a balanced argument with supporting points and counter-arguments. Good luck!
        """
        
        print(f"✅ [API] Generating audio for topic: {topic['topic']}")
        
        # Generate audio using TTS service
        audio_bytes = await synthesize_speech_exercises(audio_text)
        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
        
        return {
            "topic_id": topic_id,
            "topic": topic['topic'],
            "audio_base64": audio_base64,
            "message": "Audio generated successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [API] Error generating audio: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate audio: {str(e)}")

@router.post(
    "/evaluate-abstract-topic",
    summary="Evaluate user's audio recording against abstract topic",
    description="""
This endpoint evaluates the user's recorded audio against the abstract topic requirements.
It performs speech-to-text conversion and provides comprehensive feedback on the response quality.
Also records progress tracking data in Supabase database.
""",
    tags=["Stage 4 - Exercise 1 (Abstract Topic Monologue)"]
)
async def evaluate_abstract_topic(
    request: AudioEvaluationRequest,
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)
):
    """Evaluate user's response for abstract topic monologue"""
    print(f"🔄 [API] POST /evaluate-abstract-topic endpoint called")
    print(f"📊 [API] Request details: topic_id={request.topic_id}, user_id={request.user_id}")
    
    # Validate user_id and ensure user can only access their own data
    if not request.user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    
    if request.user_id != current_user['id']:
        raise HTTPException(status_code=403, detail="You can only access your own data")
    
    try:
        # Get topic data
        topic_data = await get_topic_by_id_from_db(request.topic_id)
        if not topic_data:
            print(f"❌ [API] Topic {request.topic_id} not found")
            raise HTTPException(status_code=404, detail="Topic not found")
        
        print(f"✅ [API] Found topic: {topic_data['topic']}")
        
        # Convert base64 audio to bytes
        try:
            audio_bytes = base64.b64decode(request.audio_base64)
            print(f"📊 [API] Audio decoded successfully, size: {len(audio_bytes)} bytes")
        except Exception as e:
            print(f"❌ [API] Error decoding audio: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid audio data")
        
        # Check if audio is too short (silence detection)
        if len(audio_bytes) < 1000:  # Less than 1KB indicates very short/silent audio
            print(f"⚠️ [API] Audio too short ({len(audio_bytes)} bytes), likely silent")
            return {
                "success": False,
                "error": "no_speech_detected",
                "message": "No speech detected. Please try again.",
                "key_connectors": topic_data['key_connectors'],
                "vocabulary_focus": topic_data['vocabulary_focus'],
                "topic": topic_data['topic']
            }
        
        # Transcribe audio to text
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
                    "message": "No clear speech detected. Please speak more clearly and provide a longer response.",
                    "key_connectors": topic_data['key_connectors'],
                    "vocabulary_focus": topic_data['vocabulary_focus'],
                    "topic": topic_data['topic']
                }

        except Exception as e:
            print(f"❌ [API] Error transcribing audio: {str(e)}")
            return {
                "success": False,
                "error": "transcription_failed",
                "message": "Failed to process audio. Please try again.",
                "key_connectors": topic_data['key_connectors'],
                "vocabulary_focus": topic_data['vocabulary_focus'],
                "topic": topic_data['topic']
            }
        
        # Evaluate the response
        try:
            print(f"🔄 [API] Evaluating response: '{user_text[:100]}...' vs expected criteria")
            evaluation = evaluate_response_ex1_stage4(
                user_response=user_text,
                topic=topic_data['topic'],
                key_connectors=topic_data['key_connectors'],
                vocabulary_focus=topic_data['vocabulary_focus'],
                model_response=topic_data['model_response']
            )
            print(f"✅ [API] Evaluation completed: {evaluation}")
            
            # Extract evaluation details for progress tracking
            score = evaluation.get("score", 0)
            is_correct = evaluation.get("is_correct", False)
            completed = evaluation.get("completed", False)
            suggested_improvement = evaluation.get("suggested_improvement", "")
            connector_matches = evaluation.get("connector_matches", [])
            total_connectors = evaluation.get("total_connectors", 0)
            matched_connectors_count = evaluation.get("matched_connectors_count", 0)
            vocabulary_matches = evaluation.get("vocabulary_matches", [])
            total_vocabulary = evaluation.get("total_vocabulary", 0)
            matched_vocabulary_count = evaluation.get("matched_vocabulary_count", 0)
            fluency_score = evaluation.get("fluency_score", 0)
            grammar_score = evaluation.get("grammar_score", 0)
            lexical_richness_score = evaluation.get("lexical_richness_score", 0)
            opinion_clarity_score = evaluation.get("opinion_clarity_score", 0)
            connector_usage_score = evaluation.get("connector_usage_score", 0)
            
            print(f"📊 [API] Evaluation details: score={score}, is_correct={is_correct}, completed={completed}")
            print(f"📊 [API] Connector matches: {matched_connectors_count}/{total_connectors}")
            print(f"📊 [API] Vocabulary matches: {matched_vocabulary_count}/{total_vocabulary}")
            print(f"📊 [API] Fluency score: {fluency_score}, Grammar score: {grammar_score}")
            print(f"📊 [API] Lexical richness: {lexical_richness_score}, Opinion clarity: {opinion_clarity_score}")
            
            # Validate evaluation data
            if not isinstance(score, (int, float)) or score < 0 or score > 100:
                print(f"⚠️ [API] Invalid score value: {score}, using default")
                score = 60
                is_correct = False
                completed = False
            
            # Record progress in Supabase database
            progress_recorded = False
            unlocked_content = []
            
            if request.user_id and request.user_id.strip():
                print(f"🔄 [API] Recording progress for user: {request.user_id}")
                try:
                    # Validate time spent (should be reasonable for 60-90 second monologue)
                    time_spent = max(1, min(request.time_spent_seconds, 1200))  # Between 1-1200 seconds for abstract topic
                    if time_spent != request.time_spent_seconds:
                        print(f"⚠️ [API] Adjusted time spent from {request.time_spent_seconds} to {time_spent} seconds")
                    
                    # Record the topic attempt
                    progress_result = await progress_tracker.record_topic_attempt(
                        user_id=request.user_id,
                        stage_id=4,  # Stage 4
                        exercise_id=1,  # Exercise 1 (Abstract Topic Monologue)
                        topic_id=topic_data['id'], # Use the topic_number
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
            if request.user_id and request.user_id.strip():
                try:
                    exercise_completion_status = await check_exercise_completion(request.user_id)
                    print(f"📊 [API] Exercise completion status: {exercise_completion_status}")
                except Exception as completion_error:
                    print(f"⚠️ [API] Failed to check exercise completion: {str(completion_error)}")
                    exercise_completion_status = {
                        "exercise_completed": False,
                        "progress_percentage": 0.0,
                        "completed_topics": 0,
                        "total_topics": 0,
                        "current_topic_id": 1,
                        "stage_id": 4,
                        "exercise_id": 1,
                        "exercise_name": "Abstract Topic Monologue",
                        "stage_name": "Stage 4 – B2 Upper Intermediate",
                        "error": str(completion_error)
                    }
            
            return {
                "success": True,
                "topic": topic_data['topic'],
                "key_connectors": topic_data['key_connectors'],
                "vocabulary_focus": topic_data['vocabulary_focus'],
                "user_text": user_text,
                "evaluation": evaluation,
                "suggested_improvement": suggested_improvement,
                "progress_recorded": progress_recorded,
                "unlocked_content": unlocked_content,
                "connector_matches": connector_matches,
                "total_connectors": total_connectors,
                "matched_connectors_count": matched_connectors_count,
                "vocabulary_matches": vocabulary_matches,
                "total_vocabulary": total_vocabulary,
                "matched_vocabulary_count": matched_vocabulary_count,
                "fluency_score": fluency_score,
                "grammar_score": grammar_score,
                "lexical_richness_score": lexical_richness_score,
                "opinion_clarity_score": opinion_clarity_score,
                "connector_usage_score": connector_usage_score,
                "response_type": evaluation.get("response_type", ""),
                "topic_title": topic_data['topic'],
                "topic_category": topic_data['category'],
                "exercise_completion": exercise_completion_status
            }

        except Exception as e:
            print(f"❌ [API] Error evaluating response: {str(e)}")
            
            # Check exercise completion status even for evaluation errors
            exercise_completion_status = None
            if request.user_id and request.user_id.strip():
                try:
                    exercise_completion_status = await check_exercise_completion(request.user_id)
                except Exception as completion_error:
                    print(f"⚠️ [API] Failed to check exercise completion: {str(completion_error)}")
                    exercise_completion_status = {
                        "exercise_completed": False,
                        "progress_percentage": 0.0,
                        "completed_topics": 0,
                        "total_topics": 0,
                        "current_topic_id": 1,
                        "stage_id": 4,
                        "exercise_id": 1,
                        "exercise_name": "Abstract Topic Monologue",
                        "stage_name": "Stage 4 – B2 Upper Intermediate",
                        "error": str(completion_error)
                    }
            
            return {
                "success": False,
                "error": "evaluation_failed",
                "message": "Failed to evaluate response. Please try again.",
                "key_connectors": topic_data['key_connectors'],
                "vocabulary_focus": topic_data['vocabulary_focus'],
                "topic": topic_data['topic'],
                "user_text": user_text,
                "exercise_completion": exercise_completion_status
            }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [API] Error in evaluate_abstract_topic: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get(
    "/abstract-topic-progress/{user_id}",
    summary="Get user's abstract topic progress",
    description="Retrieve the user's progress for Stage 4 Exercise 1 (Abstract Topic Monologue)",
    tags=["Stage 4 - Exercise 1 (Abstract Topic Monologue)"]
)
async def get_abstract_topic_progress(
    user_id: str,
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)
):
    """Get user's abstract topic progress"""
    print(f"🔄 [API] GET /abstract-topic-progress/{user_id} endpoint called")
    
    # Ensure user can only access their own data
    if user_id != current_user['id']:
        raise HTTPException(status_code=403, detail="You can only access your own data")
    
    try:
        # Get user's progress for Stage 4 Exercise 1
        progress_result = await progress_tracker.get_user_topic_progress(
            user_id=user_id,
            stage_id=4,
            exercise_id=1
        )
        
        if progress_result["success"]:
            print(f"✅ [API] Retrieved progress for user: {user_id}")
            return {
                "success": True,
                "topic_progress": progress_result.get("topic_progress", []),
                "overall_progress": progress_result.get("overall_progress", {})
            }
        else:
            print(f"❌ [API] Failed to retrieve progress: {progress_result.get('error')}")
            return {
                "success": False,
                "error": progress_result.get("error", "Failed to retrieve progress"),
                "topic_progress": [],
                "overall_progress": {}
            }
    except Exception as e:
        print(f"❌ [API] Error retrieving progress: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to retrieve progress: {str(e)}",
            "topic_progress": [],
            "overall_progress": {}
        }

@router.get(
    "/abstract-topic-current-topic/{user_id}",
    summary="Get user's current abstract topic",
    description="Retrieve the user's current topic for Stage 4 Exercise 1 (Abstract Topic Monologue)",
    tags=["Stage 4 - Exercise 1 (Abstract Topic Monologue)"]
)
async def get_abstract_topic_current_topic(
    user_id: str,
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)
):
    """Get user's current abstract topic"""
    print(f"🔄 [API] GET /abstract-topic-current-topic/{user_id} endpoint called")
    
    # Ensure user can only access their own data
    if user_id != current_user['id']:
        raise HTTPException(status_code=403, detail="You can only access your own data")
    
    try:
        # Get user's current topic for Stage 4 Exercise 1
        current_topic_result = await progress_tracker.get_current_topic_for_exercise(
            user_id=user_id,
            stage_id=4,
            exercise_id=1
        )
        
        if current_topic_result["success"]:
            print(f"✅ [API] Retrieved current topic for user: {user_id}")
            return {
                "success": True,
                "current_topic_id": current_topic_result.get("current_topic_id", 1),
                "total_topics": current_topic_result.get("total_topics", 5),
                "is_completed": current_topic_result.get("is_completed", False)
            }
        else:
            print(f"❌ [API] Failed to retrieve current topic: {current_topic_result.get('error')}")
            return {
                "success": False,
                "error": current_topic_result.get("error", "Failed to retrieve current topic"),
                "current_topic_id": 1,
                "total_topics": 5
            }
    except Exception as e:
        print(f"❌ [API] Error retrieving current topic: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to retrieve current topic: {str(e)}",
            "current_topic_id": 1,
            "total_topics": 5
        } 