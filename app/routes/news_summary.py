from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
import base64
import logging
from fastapi.concurrency import run_in_threadpool
from app.services.tts import synthesize_speech_exercises
from app.services.feedback import evaluate_response_ex3_stage4
from app.supabase_client import supabase, progress_tracker
from app.services.stt import transcribe_audio_bytes_eng_only
from app.auth_middleware import get_current_user, require_student, require_admin_or_teacher_or_student
import os

router = APIRouter(tags=["Stage 4 - Exercise 3 (News Summary)"])

async def get_news_item_by_id_from_db(news_id: int):
    """Fetch a news summary item from Supabase by its topic_number for Stage 4, Exercise 3."""
    print(f"🔍 [DB] Looking for news item with topic_number (ID): {news_id} for Stage 4, Exercise 3")
    try:
        # parent_id for Stage 4, Exercise 3 ('Leadership Communication') is 18.
        query = supabase.table("ai_tutor_content_hierarchy").select("id, topic_number, title, title_urdu, topic_data, category, difficulty").eq("level", "topic").eq("parent_id", 18).eq("topic_number", news_id).single()
        response = await run_in_threadpool(query.execute)
        
        if response.data:
            db_item = response.data
            topic_data = db_item.get("topic_data", {})
            
            formatted_item = {
                "id": db_item.get("topic_number"),
                "db_id": db_item.get("id"),
                "title": db_item.get("title"),
                "title_urdu": db_item.get("title_urdu"),
                "summary_text": topic_data.get("summary_text"),
                "summary_text_urdu": topic_data.get("summary_text_urdu"),
                "category": db_item.get("category"),
                "difficulty": db_item.get("difficulty"),
                "listening_duration": topic_data.get("listening_duration"),
                "summary_time": topic_data.get("summary_time"),
                "expected_structure": topic_data.get("expected_structure"),
                "expected_keywords": topic_data.get("expected_keywords", []),
                "expected_keywords_urdu": topic_data.get("expected_keywords_urdu", []),
                "vocabulary_focus": topic_data.get("vocabulary_focus", []),
                "vocabulary_focus_urdu": topic_data.get("vocabulary_focus_urdu", []),
                "model_summary": topic_data.get("model_summary"),
                "model_summary_urdu": topic_data.get("model_summary_urdu"),
                "evaluation_criteria": topic_data.get("evaluation_criteria", {}),
                "learning_objectives": topic_data.get("learning_objectives", [])
            }
            print(f"✅ [DB] Found news item: {formatted_item['title']}")
            return formatted_item
        else:
            print(f"❌ [DB] News item with topic_number {news_id} not found for parent_id 18")
            return None
    except Exception as e:
        print(f"❌ [DB] Error fetching news item from Supabase: {str(e)}")
        return None


async def check_exercise_completion(user_id: str) -> dict:
    """Check if user has completed the full News Summary exercise (Stage 4, Exercise 3)"""
    print(f"🔍 [COMPLETION] Checking exercise completion for user: {user_id}")
    
    try:
        # Get total news items count from Supabase
        total_topics = 0
        try:
            # parent_id for 'Leadership Communication' (News Summary) is 18
            query = supabase.table("ai_tutor_content_hierarchy").select("id", count="exact").eq("level", "topic").eq("parent_id", 18)
            response = await run_in_threadpool(query.execute)
            if response.count is not None:
                total_topics = response.count
                print(f"📊 [COMPLETION] Total news items available from DB: {total_topics}")
            else:
                print("⚠️ [COMPLETION] Could not get count from Supabase, falling back to default.")
                total_topics = 10
        except Exception as e:
            print(f"❌ [COMPLETION] Error getting news item count from DB: {str(e)}")
            total_topics = 10 # Default fallback
        
        # Get user's progress for stage 4, exercise 3
        progress_result = await progress_tracker.get_user_topic_progress(
            user_id=user_id,
            stage_id=4,
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
                "stage_id": 4,
                "exercise_id": 3,
                "exercise_name": "News Summary",
                "stage_name": "Stage 4 – B2 Upper Intermediate",
                "error": progress_result.get("error", "Failed to get progress")
            }
        
        user_progress = progress_result.get("data", [])
        completed_topics = len([record for record in user_progress if record.get("completed", False)])
        
        # Get current topic ID
        current_topic_result = await progress_tracker.get_current_topic_for_exercise(
            user_id=user_id,
            stage_id=4,
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
        print(f"   - Total news items: {total_topics}")
        print(f"   - Completed topics: {completed_topics}")
        print(f"   - Current topic ID: {current_topic_id}")
        print(f"   - Progress percentage: {progress_percentage:.1f}%")
        print(f"   - Exercise completed: {exercise_completed}")
        
        # Additional logging for completion logic
        if completed_topics >= total_topics:
            print(f"🎉 [COMPLETION] User has completed all {total_topics} news items!")
        else:
            print(f"📚 [COMPLETION] User still needs to complete {total_topics - completed_topics} more news items")
        
        return {
            "exercise_completed": exercise_completed,
            "progress_percentage": progress_percentage,
            "completed_topics": completed_topics,
            "total_topics": total_topics,
            "current_topic_id": current_topic_id,
            "stage_id": 4,
            "exercise_id": 3,
            "exercise_name": "News Summary",
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
            "exercise_id": 3,
            "exercise_name": "News Summary",
            "stage_name": "Stage 4 – B2 Upper Intermediate",
            "error": str(e)
        }


class AudioEvaluationRequest(BaseModel):
    audio_base64: str
    news_id: int
    filename: str
    user_id: str
    time_spent_seconds: int
    urdu_used: bool = False

@router.get(
    "/news-summary-items",
    summary="Get all news summary items",
    description="Retrieve all available news summary items for Stage 4 Exercise 3",
    tags=["Stage 4 - Exercise 3 (News Summary)"]
)
async def get_news_summary_items(current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)):
    """Get all news summary items from Supabase"""
    try:
        print("🔄 [DB] Fetching all news items for Stage 4, Exercise 3 from Supabase")
        query = supabase.table("ai_tutor_content_hierarchy").select("id, topic_number, title, title_urdu, topic_data, category, difficulty").eq("level", "topic").eq("parent_id", 18).order("topic_number", desc=False)
        response = await run_in_threadpool(query.execute)

        if response.data:
            news_items = []
            for item in response.data:
                topic_data = item.get("topic_data", {})
                news_items.append({
                    "id": item.get("topic_number"),
                    "db_id": item.get("id"),
                    "title": item.get("title"),
                    "title_urdu": item.get("title_urdu"),
                    "summary_text": topic_data.get("summary_text"),
                    "summary_text_urdu": topic_data.get("summary_text_urdu"),
                    "category": item.get("category"),
                    "difficulty": item.get("difficulty"),
                    "listening_duration": topic_data.get("listening_duration"),
                    "summary_time": topic_data.get("summary_time"),
                    "expected_structure": topic_data.get("expected_structure"),
                    "expected_keywords": topic_data.get("expected_keywords", []),
                    "expected_keywords_urdu": topic_data.get("expected_keywords_urdu", []),
                    "vocabulary_focus": topic_data.get("vocabulary_focus", []),
                    "vocabulary_focus_urdu": topic_data.get("vocabulary_focus_urdu", []),
                    "model_summary": topic_data.get("model_summary"),
                    "model_summary_urdu": topic_data.get("model_summary_urdu"),
                    "evaluation_criteria": topic_data.get("evaluation_criteria", {}),
                    "learning_objectives": topic_data.get("learning_objectives", [])
                })
            print(f"✅ [DB] Successfully loaded {len(news_items)} news items from Supabase")
            return {"news_items": news_items}
        else:
            print("❌ [DB] No news items found for Stage 4, Exercise 3")
            return {"news_items": []}
    except Exception as e:
        logging.error(f"Error fetching news summary items: {e}")
        raise HTTPException(status_code=500, detail="Failed to load news summary items from database")

@router.get(
    "/news-summary-items/{news_id}",
    summary="Get specific news summary item",
    description="Retrieve a specific news summary item by ID",
    tags=["Stage 4 - Exercise 3 (News Summary)"]
)
async def get_news_summary_item(news_id: int, current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)):
    """Get a specific news summary item by ID"""
    try:
        news_item = await get_news_item_by_id_from_db(news_id)
        
        if not news_item:
            raise HTTPException(status_code=404, detail="News summary item not found")
        
        print(f"✅ [API] Retrieved news item: {news_item['title']}")
        return news_item
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error fetching news summary item {news_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to load news summary item")

@router.post(
    "/news-summary/{news_id}",
    summary="Generate audio for news summary item",
    description="Generate audio pronunciation for a specific news summary item",
    tags=["Stage 4 - Exercise 3 (News Summary)"]
)
async def generate_news_summary_audio(
    news_id: int,
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)
):
    """Generate audio for a specific news summary item"""
    try:
        news_item = await get_news_item_by_id_from_db(news_id)
        
        if not news_item:
            raise HTTPException(status_code=404, detail="News summary item not found")
        
        # Create audio text with context
        audio_text = f"News Summary Challenge: {news_item['title']}. {news_item['summary_text']}"
        
        print(f"🔄 [API] Generating audio for news item: {news_item['title']}")
        
        # Generate audio using ElevenLabs
        audio_bytes = await synthesize_speech_exercises(audio_text)
        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
        
        print(f"✅ [API] Audio generated successfully for news item {news_id}")
        
        return {
            "news_id": news_id,
            "audio_base64": audio_base64,
            "title": news_item['title'],
            "summary_text": news_item['summary_text']
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error generating audio for news item {news_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate audio")

@router.post(
    "/evaluate-news-summary",
    summary="Evaluate user's news summary response",
    description="""
This endpoint evaluates the user's recorded audio against the news summary requirements.
It performs speech-to-text conversion and provides comprehensive feedback on the summary quality.
Also records progress tracking data in Supabase database.
""",
    tags=["Stage 4 - Exercise 3 (News Summary)"]
)
async def evaluate_news_summary(
    request: AudioEvaluationRequest,
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)
):
    """Evaluate user's news summary response"""
    try:
        print(f"🔄 [API] POST /evaluate-news-summary endpoint called")
        print(f"📊 [API] Request details: news_id={request.news_id}, user_id={request.user_id}")
        
        # Validate user_id and ensure user can only access their own data
        if not request.user_id:
            raise HTTPException(status_code=400, detail="user_id is required")
        
        if request.user_id != current_user['id']:
            raise HTTPException(status_code=403, detail="You can only access your own data")
        
        # Load news item data
        news_item = await get_news_item_by_id_from_db(request.news_id)
        
        if not news_item:
            raise HTTPException(status_code=404, detail="News summary item not found")
        
        print(f"✅ [API] Found news item: {news_item['title']}")
        
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
        evaluation = evaluate_response_ex3_stage4(
            user_response=user_text,
            news_title=news_item['title'],
            summary_text=news_item['summary_text'],
            expected_keywords=news_item['expected_keywords'],
            vocabulary_focus=news_item['vocabulary_focus'],
            model_summary=news_item['model_summary']
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
                exercise_id=3,
                topic_id=news_item['db_id'], # Use the actual database ID
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
            completion_status = await check_exercise_completion(request.user_id)
            evaluation["exercise_completion"] = completion_status
        except Exception as e:
            print(f"⚠️ [API] Exercise completion check failed: {e}")
            evaluation["exercise_completion"] = {
                "exercise_completed": False,
                "progress_percentage": 0.0,
                "completed_topics": 0,
                "total_topics": 0,
                "current_topic_id": 1,
                "stage_id": 4,
                "exercise_id": 3,
                "exercise_name": "News Summary",
                "stage_name": "Stage 4 – B2 Upper Intermediate",
                "error": str(e)
            }
        
        return evaluation
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error evaluating news summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to evaluate response")

@router.get(
    "/news-summary-progress/{user_id}",
    summary="Get user's news summary progress",
    description="Retrieve the user's progress for Stage 4 Exercise 3 (News Summary)",
    tags=["Stage 4 - Exercise 3 (News Summary)"]
)
async def get_news_summary_progress(
    user_id: str,
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)
):
    """Get user's news summary progress"""
    
    # Ensure user can only access their own data
    if user_id != current_user['id']:
        raise HTTPException(status_code=403, detail="You can only access your own data")
    
    try:
        print(f"🔄 [API] GET /news-summary-progress/{user_id} endpoint called")
        
        progress = await progress_tracker.get_user_topic_progress(
            user_id=user_id,
            stage_id=4,
            exercise_id=3
        )
        
        print(f"✅ [API] Retrieved progress for user: {user_id}")
        return progress
    except Exception as e:
        logging.error(f"Error fetching news summary progress: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch progress")

@router.get(
    "/news-summary-current-item/{user_id}",
    summary="Get current news summary item for user",
    description="Retrieve the current news summary item the user should practice",
    tags=["Stage 4 - Exercise 3 (News Summary)"]
)
async def get_current_news_summary_item(
    user_id: str,
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)
):
    """Get current news summary item for user"""
    
    # Ensure user can only access their own data
    if user_id != current_user['id']:
        raise HTTPException(status_code=403, detail="You can only access your own data")
    
    try:
        print(f"🔄 [API] GET /news-summary-current-item/{user_id} endpoint called")
        
        current_item = await progress_tracker.get_current_topic_for_exercise(
            user_id=user_id,
            stage_id=4,
            exercise_id=3
        )
        
        print(f"✅ [API] Retrieved current news item for user: {user_id}")
        return current_item
    except Exception as e:
        logging.error(f"Error fetching current news summary item: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch current item") 