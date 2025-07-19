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

class GetCurrentTopicRequest(BaseModel):
    user_id: str
    stage_id: int
    exercise_id: int

class ProgressResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None
    message: Optional[str] = None

class ComprehensiveProgressRequest(BaseModel):
    user_id: str

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

@router.post("/get-current-topic", response_model=ProgressResponse)
async def get_current_topic_for_exercise(request: GetCurrentTopicRequest):
    """Get the current topic_id for a specific exercise"""
    print(f"🔄 [API] POST /get-current-topic called")
    print(f"📝 [API] Request data: {request}")
    
    try:
        print(f"🔄 [API] Getting current topic for user: {request.user_id}, stage: {request.stage_id}, exercise: {request.exercise_id}")
        
        result = await progress_tracker.get_current_topic_for_exercise(
            user_id=request.user_id,
            stage_id=request.stage_id,
            exercise_id=request.exercise_id
        )
        
        print(f"📊 [API] Get current topic result: {result}")
        
        if result["success"]:
            print(f"✅ [API] Current topic retrieved successfully")
            return ProgressResponse(
                success=True,
                data=result,
                message="Current topic retrieved successfully"
            )
        else:
            print(f"❌ [API] Get current topic failed: {result.get('error')}")
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to get current topic"))
            
    except Exception as e:
        print(f"❌ [API] Error in get_current_topic_for_exercise: {str(e)}")
        logger.error(f"Error in get_current_topic_for_exercise: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/comprehensive-progress", response_model=ProgressResponse)
async def get_comprehensive_progress(request: ComprehensiveProgressRequest):
    """Get comprehensive progress data for the beautiful progress page"""
    print(f"🔄 [API] POST /comprehensive-progress called")
    print(f"📝 [API] Request data: {request}")
    
    try:
        print(f"🔄 [API] Getting comprehensive progress for user: {request.user_id}")
        
        # Get all progress data
        progress_result = await progress_tracker.get_user_progress(request.user_id)
        print(f"📊 [API] Progress result: {progress_result}")
        
        if not progress_result["success"]:
            print(f"❌ [API] Failed to get progress data: {progress_result.get('error')}")
            raise HTTPException(status_code=500, detail=progress_result.get("error", "Failed to get progress data"))
        
        progress_data = progress_result.get("data", {})
        summary = progress_data.get("summary", {})
        stages = progress_data.get("stages", [])
        exercises = progress_data.get("exercises", [])
        unlocks = progress_data.get("unlocks", [])
        
        print(f"📊 [API] Data summary:")
        print(f"   - Summary exists: {summary is not None}")
        print(f"   - Stages count: {len(stages)}")
        print(f"   - Exercises count: {len(exercises)}")
        print(f"   - Unlocks count: {len(unlocks)}")
        
        # Process and structure the data for frontend
        processed_data = await _process_progress_data_for_frontend(summary, stages, exercises, unlocks)
        
        print(f"✅ [API] Comprehensive progress data processed successfully")
        return ProgressResponse(
            success=True,
            data=processed_data,
            message="Comprehensive progress data retrieved successfully"
        )
        
    except Exception as e:
        print(f"❌ [API] Error in get_comprehensive_progress: {str(e)}")
        logger.error(f"Error in get_comprehensive_progress: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

async def _process_progress_data_for_frontend(summary: dict, stages: list, exercises: list, unlocks: list) -> dict:
    """Process raw progress data into frontend-friendly format"""
    print(f"🔄 [PROCESS] Processing progress data for frontend")
    
    try:
        # Stage definitions with exercise names
        stage_definitions = {
            1: {
                "name": "Stage 1 – A1 Beginner",
                "subtitle": "Foundation Building",
                "exercises": [
                    "Repeat After Me",
                    "Quick Response Prompts", 
                    "Listen and Reply"
                ]
            },
            2: {
                "name": "Stage 2 – A2 Elementary",
                "subtitle": "Daily Conversations",
                "exercises": [
                    "Daily Routine Narration",
                    "Question & Answer Chat",
                    "Roleplay Simulation – Food Order"
                ]
            },
            3: {
                "name": "Stage 3 – B1 Intermediate",
                "subtitle": "Storytelling & Dialogue",
                "exercises": [
                    "Storytelling Practice",
                    "Group Dialogue",
                    "Problem-Solving"
                ]
            },
            4: {
                "name": "Stage 4 – B2 Upper Intermediate",
                "subtitle": "Advanced Communication",
                "exercises": [
                    "Abstract Topic Monologue",
                    "Mock Interview Practice",
                    "News Summary Challenge"
                ]
            },
            5: {
                "name": "Stage 5 – C1 Advanced",
                "subtitle": "Critical Thinking & Presentations",
                "exercises": [
                    "Critical Thinking Dialogues",
                    "Academic Presentations",
                    "In-Depth Interview"
                ]
            },
            6: {
                "name": "Stage 6 – C2 Mastery",
                "subtitle": "Mastery & Spontaneity",
                "exercises": [
                    "Spontaneous Speech",
                    "Sensitive Scenario Roleplay",
                    "Critical Opinion Builder"
                ]
            }
        }
        
        # Process current stage info
        current_stage_id = summary.get('current_stage', 1)
        current_stage_info = stage_definitions.get(current_stage_id, stage_definitions[1])
        
        # Calculate stage progress
        processed_stages = []
        for stage_id in range(1, 7):
            stage_info = stage_definitions[stage_id]
            stage_progress = next((s for s in stages if s.get('stage_id') == stage_id), None)
            
            # Get exercises for this stage
            stage_exercises = []
            for exercise_id in range(1, 4):
                exercise_data = next((e for e in exercises if e.get('stage_id') == stage_id and e.get('exercise_id') == exercise_id), None)
                
                exercise_name = stage_info['exercises'][exercise_id - 1]
                exercise_status = "locked"
                
                if exercise_data:
                    attempts = exercise_data.get('attempts', 0)
                    if exercise_data.get('completed_at'):
                        exercise_status = "completed"
                    elif attempts > 0:
                        exercise_status = "in_progress"
                    
                    # Check if exercise is unlocked based on unlocks data
                    exercise_unlock = next((u for u in unlocks if u.get('stage_id') == stage_id and u.get('exercise_id') == exercise_id), None)
                    if exercise_unlock and exercise_unlock.get('is_unlocked'):
                        if exercise_status == "locked":
                            exercise_status = "in_progress"  # If unlocked but no attempts, show as in_progress
                
                stage_exercises.append({
                    "name": exercise_name,
                    "status": exercise_status,
                    "progress": exercise_data.get('average_score', 0) if exercise_data else 0,
                    "attempts": exercise_data.get('attempts', 0) if exercise_data else 0
                })
            
            # Calculate stage completion and progress
            completed_exercises = sum(1 for e in stage_exercises if e['status'] == 'completed')
            in_progress_exercises = sum(1 for e in stage_exercises if e['status'] == 'in_progress')
            
            # Calculate stage progress based on exercise completion and attempts
            total_progress = 0
            for exercise in stage_exercises:
                if exercise['status'] == 'completed':
                    total_progress += 100
                elif exercise['status'] == 'in_progress':
                    # Calculate progress based on attempts and scores
                    progress = min(90, exercise['progress'])  # Cap at 90% until completed
                    total_progress += progress
            
            stage_progress_percentage = total_progress / 3
            stage_completed = completed_exercises == 3
            
            # Check if stage should be unlocked (if any exercise is unlocked or in progress)
            stage_unlocked = any(e['status'] != 'locked' for e in stage_exercises)
            
            processed_stages.append({
                "stage_id": stage_id,
                "name": stage_info['name'],
                "subtitle": stage_info['subtitle'],
                "completed": stage_completed,
                "progress": stage_progress_percentage,
                "exercises": stage_exercises,
                "started_at": stage_progress.get('started_at') if stage_progress else None,
                "completed_at": stage_progress.get('completed_at') if stage_progress else None,
                "unlocked": stage_unlocked
            })
        
        # Calculate overall progress based on all stages and exercises
        total_progress = 0
        total_possible = 6 * 3  # 6 stages * 3 exercises each
        
        for stage in processed_stages:
            for exercise in stage['exercises']:
                if exercise['status'] == 'completed':
                    total_progress += 100
                elif exercise['status'] == 'in_progress':
                    total_progress += exercise['progress']
                # locked exercises contribute 0 to total progress
        
        overall_progress = (total_progress / total_possible) * 100
        
        # Get current stage progress
        current_stage_data = next((s for s in processed_stages if s['stage_id'] == current_stage_id), processed_stages[0])
        current_stage_progress = current_stage_data['progress']
        
        # Calculate current stage progress more accurately
        if current_stage_data['exercises']:
            stage_exercises = current_stage_data['exercises']
            total_exercise_progress = sum(e['progress'] for e in stage_exercises)
            current_stage_progress = total_exercise_progress / len(stage_exercises)
        
        # Process achievements (mock data for now - can be enhanced later)
        achievements = [
            {
                "name": "Beginner Badge",
                "icon": "star",
                "date": summary.get('first_activity_date', '2025-01-15'),
                "color": "#FFD700",
                "description": "Completed your first exercise"
            },
            {
                "name": f"{summary.get('streak_days', 0)}-Day Streak",
                "icon": "flame",
                "date": summary.get('last_activity_date', '2025-01-20'),
                "color": "#FF6B35",
                "description": f"Maintained a {summary.get('streak_days', 0)}-day learning streak"
            }
        ]
        
        # Calculate total completed stages
        total_completed_stages = sum(1 for stage in processed_stages if stage['completed'])
        
        # Add more achievements based on progress
        if total_completed_stages >= 1:
            achievements.append({
                "name": "First Stage Complete",
                "icon": "checkmark-circle",
                "date": summary.get('last_activity_date', '2025-01-10'),
                "color": "#58D68D",
                "description": "Completed your first learning stage"
            })
        
        if summary.get('total_time_spent_minutes', 0) >= 60:
            achievements.append({
                "name": "Dedicated Learner",
                "icon": "time",
                "date": summary.get('last_activity_date', '2025-01-18'),
                "color": "#3498DB",
                "description": "Spent over 1 hour learning"
            })
        
        # Generate fluency trend (mock data based on progress)
        base_score = 50
        progress_factor = overall_progress / 100
        fluency_trend = []
        for week in range(7):
            week_score = base_score + (progress_factor * 30) + (week * 2)
            fluency_trend.append(min(100, max(50, week_score)))
        
        processed_data = {
            "current_stage": {
                "id": current_stage_id,
                "name": current_stage_info['name'],
                "subtitle": current_stage_info['subtitle'],
                "progress": current_stage_progress
            },
            "overall_progress": overall_progress,
            "total_progress": overall_progress,  # For compatibility
            "streak_days": summary.get('streak_days', 0),
            "total_practice_time": round(summary.get('total_time_spent_minutes', 0) / 60, 1),
            "total_exercises_completed": summary.get('total_exercises_completed', 0),
            "longest_streak": summary.get('longest_streak', 0),
            "average_session_duration": summary.get('average_session_duration_minutes', 0),
            "weekly_learning_hours": summary.get('weekly_learning_hours', 0),
            "monthly_learning_hours": summary.get('monthly_learning_hours', 0),
            "first_activity_date": summary.get('first_activity_date'),
            "last_activity_date": summary.get('last_activity_date'),
            "stages": processed_stages,
            "achievements": achievements,
            "fluency_trend": fluency_trend,
            "unlocked_content": unlocks
        }
        
        print(f"✅ [PROCESS] Progress data processed successfully")
        print(f"📊 [PROCESS] Processed data summary:")
        print(f"   - Current stage: {current_stage_id}")
        print(f"   - Overall progress: {overall_progress:.1f}%")
        print(f"   - Streak days: {summary.get('streak_days', 0)}")
        print(f"   - Total practice time: {processed_data['total_practice_time']}h")
        print(f"   - Achievements count: {len(achievements)}")
        
        return processed_data
        
    except Exception as e:
        print(f"❌ [PROCESS] Error processing progress data: {str(e)}")
        logger.error(f"Error processing progress data: {str(e)}")
        # Return safe default data
        return {
            "current_stage": {"id": 1, "name": "Stage 1 – A1 Beginner", "subtitle": "Foundation Building", "progress": 0},
            "overall_progress": 0,
            "total_progress": 0,
            "streak_days": 0,
            "total_practice_time": 0,
            "total_exercises_completed": 0,
            "longest_streak": 0,
            "average_session_duration": 0,
            "weekly_learning_hours": 0,
            "monthly_learning_hours": 0,
            "first_activity_date": None,
            "last_activity_date": None,
            "stages": [],
            "achievements": [],
            "fluency_trend": [50, 50, 50, 50, 50, 50, 50],
            "unlocked_content": []
        }

@router.get("/health")
async def health_check():
    """Health check endpoint for progress tracking service"""
    print(f"🔄 [API] GET /health called")
    print(f"✅ [API] Progress tracking service is healthy")
    return {"status": "healthy", "service": "progress_tracking"} 