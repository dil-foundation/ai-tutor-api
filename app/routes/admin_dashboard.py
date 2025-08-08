from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging
from datetime import date, datetime, timedelta
from app.supabase_client import supabase, progress_tracker
from app.auth_middleware import get_current_user, require_admin_or_teacher
import json

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["Admin Dashboard"])

# Pydantic models for request/response
class AdminDashboardResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None
    message: Optional[str] = None

class TimeRangeRequest(BaseModel):
    time_range: str = "all_time"  # "today", "this_week", "this_month", "all_time"

class LessonAccess(BaseModel):
    lesson_name: str
    stage: str
    accesses: int
    icon: str

class LearnFeatureUsage(BaseModel):
    today_access: int
    this_week: int

class KeyMetrics(BaseModel):
    total_users: int
    students: int
    students_percentage: float
    teachers: int
    teachers_percentage: float
    active_today: int

@router.get("/dashboard/overview", response_model=AdminDashboardResponse)
async def get_admin_dashboard_overview(
    time_range: str = "all_time",
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher)
):
    """
    Get comprehensive admin dashboard overview with all key metrics
    """
    print(f"🔄 [ADMIN] GET /admin/dashboard/overview called")
    print(f"📝 [ADMIN] Time range: {time_range}")
    print(f"👤 [ADMIN] Authenticated user: {current_user['email']} (Role: {current_user.get('role', 'unknown')})")
    
    try:
        # Get all required metrics
        key_metrics = await _get_key_metrics()
        learn_usage = await _get_learn_feature_usage()
        most_accessed_lessons = await _get_most_accessed_lessons()
        
        dashboard_data = {
            "key_metrics": key_metrics,
            "learn_feature_usage": learn_usage,
            "most_accessed_lessons": most_accessed_lessons,
            "last_updated": datetime.now().isoformat()
        }
        
        print(f"✅ [ADMIN] Dashboard data retrieved successfully")
        return AdminDashboardResponse(
            success=True,
            data=dashboard_data,
            message="Admin dashboard data retrieved successfully"
        )
        
    except Exception as e:
        print(f"❌ [ADMIN] Error in get_admin_dashboard_overview: {str(e)}")
        logger.error(f"Error in get_admin_dashboard_overview: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/dashboard/key-metrics", response_model=AdminDashboardResponse)
async def get_key_metrics(
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher)
):
    """
    Get key metrics for admin dashboard (Total Users, Students, Teachers, Active Today)
    """
    print(f"🔄 [ADMIN] GET /admin/dashboard/key-metrics called")
    print(f"👤 [ADMIN] Authenticated user: {current_user['email']} (Role: {current_user.get('role', 'unknown')})")
    
    try:
        metrics = await _get_key_metrics()
        
        return AdminDashboardResponse(
            success=True,
            data=metrics,
            message="Key metrics retrieved successfully"
        )
        
    except Exception as e:
        print(f"❌ [ADMIN] Error in get_key_metrics: {str(e)}")
        logger.error(f"Error in get_key_metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/dashboard/learn-usage", response_model=AdminDashboardResponse)
async def get_learn_feature_usage(
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher)
):
    """
    Get Learn feature usage summary (Today's Access, This Week's engagement)
    """
    print(f"🔄 [ADMIN] GET /admin/dashboard/learn-usage called")
    print(f"👤 [ADMIN] Authenticated user: {current_user['email']} (Role: {current_user.get('role', 'unknown')})")
    
    try:
        usage_data = await _get_learn_feature_usage()
        
        return AdminDashboardResponse(
            success=True,
            data=usage_data,
            message="Learn feature usage data retrieved successfully"
        )
        
    except Exception as e:
        print(f"❌ [ADMIN] Error in get_learn_feature_usage: {str(e)}")
        logger.error(f"Error in get_learn_feature_usage: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/dashboard/most-accessed-lessons", response_model=AdminDashboardResponse)
async def get_most_accessed_lessons(
    limit: int = 5,
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher)
):
    """
    Get most accessed practice lessons with their stages and access counts
    """
    print(f"🔄 [ADMIN] GET /admin/dashboard/most-accessed-lessons called")
    print(f"👤 [ADMIN] Authenticated user: {current_user['email']} (Role: {current_user.get('role', 'unknown')})")
    print(f"📊 [ADMIN] Limit: {limit}")
    
    try:
        lessons = await _get_most_accessed_lessons(limit)
        
        return AdminDashboardResponse(
            success=True,
            data={"lessons": lessons},
            message="Most accessed lessons data retrieved successfully"
        )
        
    except Exception as e:
        print(f"❌ [ADMIN] Error in get_most_accessed_lessons: {str(e)}")
        logger.error(f"Error in get_most_accessed_lessons: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

async def _get_key_metrics() -> Dict[str, Any]:
    """
    Get key metrics for admin dashboard
    """
    try:
        print(f"🔄 [ADMIN] Calculating key metrics...")
        
        # Get total users count from auth.users table
        try:
            total_users_result = supabase.table('auth.users').select('id', count='exact').execute()
            total_users = total_users_result.count if total_users_result.count is not None else 0
        except Exception as e:
            print(f"⚠️ [ADMIN] Error getting total users, using fallback: {str(e)}")
            # Fallback: count from progress summary table
            total_users_result = supabase.table('ai_tutor_user_progress_summary').select('user_id', count='exact').execute()
            total_users = total_users_result.count if total_users_result.count is not None else 0
        
        # Get students count (users with progress data)
        students_result = supabase.table('ai_tutor_user_progress_summary').select('user_id', count='exact').execute()
        students_count = students_result.count if students_result.count is not None else 0
        
        # Calculate teachers count (total users - students)
        teachers_count = max(0, total_users - students_count)
        
        # Calculate percentages
        students_percentage = round((students_count / total_users * 100) if total_users > 0 else 0, 1)
        teachers_percentage = round((teachers_count / total_users * 100) if total_users > 0 else 0, 1)
        
        # Get active today count (users who had activity today)
        today = date.today().isoformat()
        active_today_result = supabase.table('ai_tutor_daily_learning_analytics').select(
            'user_id'
        ).eq('analytics_date', today).execute()
        
        active_today = len(active_today_result.data) if active_today_result.data else 0
        
        metrics = {
            "total_users": total_users,
            "students": students_count,
            "students_percentage": students_percentage,
            "teachers": teachers_count,
            "teachers_percentage": teachers_percentage,
            "active_today": active_today
        }
        
        print(f"📊 [ADMIN] Key metrics calculated:")
        print(f"   - Total Users: {total_users}")
        print(f"   - Students: {students_count} ({students_percentage}%)")
        print(f"   - Teachers: {teachers_count} ({teachers_percentage}%)")
        print(f"   - Active Today: {active_today}")
        
        return metrics
        
    except Exception as e:
        print(f"❌ [ADMIN] Error calculating key metrics: {str(e)}")
        logger.error(f"Error calculating key metrics: {str(e)}")
        raise

async def _get_learn_feature_usage() -> Dict[str, Any]:
    """
    Get Learn feature usage summary
    """
    try:
        print(f"🔄 [ADMIN] Calculating Learn feature usage...")
        
        today = date.today().isoformat()
        week_start = (date.today() - timedelta(days=date.today().weekday())).isoformat()
        
        # Get today's access count (users who accessed Learn feature today)
        today_access_result = supabase.table('ai_tutor_daily_learning_analytics').select(
            'user_id'
        ).eq('analytics_date', today).execute()
        
        today_access = len(today_access_result.data) if today_access_result.data else 0
        
        # Get this week's total engagement
        this_week_result = supabase.table('ai_tutor_daily_learning_analytics').select(
            'user_id'
        ).gte('analytics_date', week_start).execute()
        
        this_week = len(this_week_result.data) if this_week_result.data else 0
        
        usage_data = {
            "today_access": today_access,
            "this_week": this_week
        }
        
        print(f"📊 [ADMIN] Learn feature usage calculated:")
        print(f"   - Today's Access: {today_access}")
        print(f"   - This Week: {this_week}")
        
        return usage_data
        
    except Exception as e:
        print(f"❌ [ADMIN] Error calculating Learn feature usage: {str(e)}")
        logger.error(f"Error calculating Learn feature usage: {str(e)}")
        raise

async def _get_most_accessed_lessons(limit: int = 5) -> List[Dict[str, Any]]:
    """
    Get most accessed practice lessons
    """
    try:
        print(f"🔄 [ADMIN] Calculating most accessed lessons...")
        
        # Get lesson access data from topic progress
        # This will give us the most accessed topics/exercises
        lessons_result = supabase.table('ai_tutor_user_topic_progress').select(
            'stage_id, exercise_id, topic_id'
        ).execute()
        
        if not lessons_result.data:
            print(f"ℹ️ [ADMIN] No lesson access data found")
            return []
        
        # Count accesses per lesson
        lesson_accesses = {}
        
        for record in lessons_result.data:
            stage_id = record.get('stage_id', 1)
            exercise_id = record.get('exercise_id', 1)
            topic_id = record.get('topic_id', 1)
            
            # Create a unique lesson key
            lesson_key = f"stage_{stage_id}_exercise_{exercise_id}_topic_{topic_id}"
            
            if lesson_key not in lesson_accesses:
                lesson_accesses[lesson_key] = {
                    'stage_id': stage_id,
                    'exercise_id': exercise_id,
                    'topic_id': topic_id,
                    'accesses': 0
                }
            
            lesson_accesses[lesson_key]['accesses'] += 1
        
        # Sort by access count and get top lessons
        sorted_lessons = sorted(
            lesson_accesses.values(),
            key=lambda x: x['accesses'],
            reverse=True
        )[:limit]
        
        # Map to lesson names and stages
        lesson_mapping = {
            # Stage 1
            (1, 1): {"name": "Basic Conversation Starters", "stage": "Stage 1", "icon": "chatbubble"},
            (1, 2): {"name": "Daily Routine Vocabulary", "stage": "Stage 1", "icon": "time"},
            (1, 3): {"name": "Quick Response Practice", "stage": "Stage 1", "icon": "flash"},
            
            # Stage 2
            (2, 1): {"name": "Roleplay Simulation", "stage": "Stage 2", "icon": "people"},
            (2, 2): {"name": "Storytelling", "stage": "Stage 2", "icon": "book"},
            (2, 3): {"name": "Group Dialogue", "stage": "Stage 2", "icon": "chatbubbles"},
            
            # Stage 3
            (3, 1): {"name": "Problem Solving", "stage": "Stage 3", "icon": "bulb"},
            (3, 2): {"name": "Critical Thinking Dialogues", "stage": "Stage 3", "icon": "brain"},
            (3, 3): {"name": "Academic Presentations", "stage": "Stage 3", "icon": "school"},
            
            # Stage 4
            (4, 1): {"name": "Abstract Topic Discussion", "stage": "Stage 4", "icon": "globe"},
            (4, 2): {"name": "Mock Interview", "stage": "Stage 4", "icon": "briefcase"},
            (4, 3): {"name": "News Summary", "stage": "Stage 4", "icon": "newspaper"},
            
            # Stage 5
            (5, 1): {"name": "In-depth Interview", "stage": "Stage 5", "icon": "person"},
            (5, 2): {"name": "Academic Presentation", "stage": "Stage 5", "icon": "presentation"},
            (5, 3): {"name": "Critical Opinion Builder", "stage": "Stage 5", "icon": "analytics"},
            
            # Stage 6
            (6, 1): {"name": "Spontaneous Speech", "stage": "Stage 6", "icon": "mic"},
            (6, 2): {"name": "Sensitive Scenario", "stage": "Stage 6", "icon": "shield"},
            (6, 3): {"name": "Advanced Roleplay", "stage": "Stage 6", "icon": "theater"}
        }
        
        formatted_lessons = []
        for lesson in sorted_lessons:
            stage_id = lesson['stage_id']
            exercise_id = lesson['exercise_id']
            
            lesson_info = lesson_mapping.get((stage_id, exercise_id), {
                "name": f"Stage {stage_id} Exercise {exercise_id}",
                "stage": f"Stage {stage_id}",
                "icon": "document"
            })
            
            formatted_lessons.append({
                "lesson_name": lesson_info["name"],
                "stage": lesson_info["stage"],
                "accesses": lesson['accesses'],
                "icon": lesson_info["icon"]
            })
        
        print(f"📊 [ADMIN] Most accessed lessons calculated: {len(formatted_lessons)} lessons")
        
        return formatted_lessons
        
    except Exception as e:
        print(f"❌ [ADMIN] Error calculating most accessed lessons: {str(e)}")
        logger.error(f"Error calculating most accessed lessons: {str(e)}")
        raise

@router.get("/health")
async def admin_health_check():
    """
    Health check endpoint for admin routes
    """
    return {"status": "healthy", "service": "admin_dashboard"}
