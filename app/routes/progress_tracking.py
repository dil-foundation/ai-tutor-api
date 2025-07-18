from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
import logging
from app.supabase_client import progress_tracker

logger = logging.getLogger(__name__)
router = APIRouter()

# Pydantic models for request/response
class TopicAttemptRequest(BaseModel):
    user_id: str
    stage_id: int
    exercise_id: int
    topic_id: int
    score: float
    urdu_used: bool
    time_spent_seconds: int
    completed: bool

class UserProgressRequest(BaseModel):
    user_id: str

class InitializeProgressRequest(BaseModel):
    user_id: str

class ProgressResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None
    message: Optional[str] = None

@router.post("/initialize-progress", response_model=ProgressResponse)
async def initialize_user_progress(request: InitializeProgressRequest):
    """Initialize user progress when they first start using the app"""
    print(f"🔄 [API] POST /initialize-progress called")
    print(f"📝 [API] Request data: {request}")
    
    try:
        print(f"🔄 [API] Starting progress initialization for user: {request.user_id}")
        
        result = await progress_tracker.initialize_user_progress(request.user_id)
        print(f"📊 [API] Progress initialization result: {result}")
        
        if result["success"]:
            print(f"✅ [API] Progress initialization successful")
            return ProgressResponse(
                success=True,
                data=result.get("data"),
                message=result.get("message", "Progress initialized successfully")
            )
        else:
            print(f"❌ [API] Progress initialization failed: {result.get('error')}")
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to initialize progress"))
            
    except Exception as e:
        print(f"❌ [API] Error in initialize_user_progress: {str(e)}")
        logger.error(f"Error in initialize_user_progress: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/record-topic-attempt", response_model=ProgressResponse)
async def record_topic_attempt(request: TopicAttemptRequest):
    """Record a topic attempt with detailed metrics"""
    print(f"🔄 [API] POST /record-topic-attempt called")
    print(f"📝 [API] Request data: {request}")
    print(f"📊 [API] Topic attempt details:")
    print(f"   - User ID: {request.user_id}")
    print(f"   - Stage: {request.stage_id}")
    print(f"   - Exercise: {request.exercise_id}")
    print(f"   - Topic: {request.topic_id}")
    print(f"   - Score: {request.score}")
    print(f"   - Urdu Used: {request.urdu_used}")
    print(f"   - Time Spent: {request.time_spent_seconds}s")
    print(f"   - Completed: {request.completed}")
    
    try:
        print(f"🔄 [API] Recording topic attempt...")
        
        result = await progress_tracker.record_topic_attempt(
            user_id=request.user_id,
            stage_id=request.stage_id,
            exercise_id=request.exercise_id,
            topic_id=request.topic_id,
            score=request.score,
            urdu_used=request.urdu_used,
            time_spent_seconds=request.time_spent_seconds,
            completed=request.completed
        )
        
        print(f"📊 [API] Topic attempt recording result: {result}")
        
        if result["success"]:
            print(f"🔄 [API] Checking for content unlocks...")
            # Check for content unlocks after recording attempt
            unlock_result = await progress_tracker.check_and_unlock_content(request.user_id)
            print(f"📊 [API] Content unlock check result: {unlock_result}")
            
            unlocked_content = unlock_result.get("unlocked_content", [])
            if unlocked_content:
                print(f"🎉 [API] Unlocked content: {unlocked_content}")
            
            print(f"✅ [API] Topic attempt recorded successfully")
            return ProgressResponse(
                success=True,
                data={
                    "topic_attempt": result.get("data"),
                    "unlocked_content": unlocked_content
                },
                message="Topic attempt recorded successfully"
            )
        else:
            print(f"❌ [API] Topic attempt recording failed: {result.get('error')}")
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to record topic attempt"))
            
    except Exception as e:
        print(f"❌ [API] Error in record_topic_attempt: {str(e)}")
        logger.error(f"Error in record_topic_attempt: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/user-progress/{user_id}", response_model=ProgressResponse)
async def get_user_progress(user_id: str):
    """Get comprehensive user progress data"""
    print(f"🔄 [API] GET /user-progress/{user_id} called")
    
    try:
        print(f"🔄 [API] Getting user progress for: {user_id}")
        
        result = await progress_tracker.get_user_progress(user_id)
        print(f"📊 [API] User progress result: {result}")
        
        if result["success"]:
            data = result.get("data", {})
            print(f"📊 [API] Progress data summary:")
            print(f"   - Summary exists: {data.get('summary') is not None}")
            print(f"   - Stages count: {len(data.get('stages', []))}")
            print(f"   - Exercises count: {len(data.get('exercises', []))}")
            print(f"   - Unlocks count: {len(data.get('unlocks', []))}")
            
            print(f"✅ [API] User progress retrieved successfully")
            return ProgressResponse(
                success=True,
                data=result.get("data"),
                message="User progress retrieved successfully"
            )
        else:
            print(f"❌ [API] User progress retrieval failed: {result.get('error')}")
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to get user progress"))
            
    except Exception as e:
        print(f"❌ [API] Error in get_user_progress: {str(e)}")
        logger.error(f"Error in get_user_progress: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/check-unlocks/{user_id}", response_model=ProgressResponse)
async def check_content_unlocks(user_id: str):
    """Check if user should unlock new content based on progress"""
    print(f"🔄 [API] POST /check-unlocks/{user_id} called")
    
    try:
        print(f"🔄 [API] Checking content unlocks for user: {user_id}")
        
        result = await progress_tracker.check_and_unlock_content(user_id)
        print(f"📊 [API] Content unlock check result: {result}")
        
        if result["success"]:
            unlocked_content = result.get("unlocked_content", [])
            if unlocked_content:
                print(f"🎉 [API] Unlocked content: {unlocked_content}")
            else:
                print(f"ℹ️ [API] No new content unlocked")
            
            print(f"✅ [API] Content unlock check completed")
            return ProgressResponse(
                success=True,
                data={"unlocked_content": unlocked_content},
                message="Content unlock check completed"
            )
        else:
            print(f"❌ [API] Content unlock check failed: {result.get('error')}")
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to check content unlocks"))
            
    except Exception as e:
        print(f"❌ [API] Error in check_content_unlocks: {str(e)}")
        logger.error(f"Error in check_content_unlocks: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/health")
async def health_check():
    """Health check endpoint for progress tracking service"""
    print(f"🔄 [API] GET /health called")
    print(f"✅ [API] Progress tracking service is healthy")
    return {"status": "healthy", "service": "progress_tracking"} 