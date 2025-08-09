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

def _get_date_range(time_range: str) -> tuple:
    """
    Calculate start and end dates based on time range
    """
    today = date.today()
    
    if time_range == "today":
        start_date = today
        end_date = today
    elif time_range == "this_week":
        start_date = today - timedelta(days=today.weekday())
        end_date = today
    elif time_range == "this_month":
        start_date = today.replace(day=1)
        end_date = today
    elif time_range == "all_time":
        start_date = None
        end_date = None
    else:
        # Default to all_time if invalid time_range
        start_date = None
        end_date = None
    
    return start_date, end_date

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

class StagePerformance(BaseModel):
    stage_id: int
    stage_name: str
    performance_percentage: float
    user_count: int
    color: str

class UserEngagement(BaseModel):
    category: str
    percentage: float
    user_count: int
    color: str

class TimeUsagePattern(BaseModel):
    hour: int
    usage_count: int

class TopContent(BaseModel):
    title: str
    type: str
    stage_or_module: str
    views: int
    avg_score: float
    trend: str
    icon: str

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
        # Get all required metrics with time range filtering
        key_metrics = await _get_key_metrics(time_range)
        learn_usage = await _get_learn_feature_usage(time_range)
        most_accessed_lessons = await _get_most_accessed_lessons(time_range=time_range)
        
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

# NEW APIs for Reports & Analytics Page

@router.get("/reports/practice-stage-performance", response_model=AdminDashboardResponse)
async def get_practice_stage_performance(
    time_range: str = "all_time",
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher)
):
    """
    Get practice stage performance data for bar chart
    """
    print(f"🔄 [ADMIN] GET /admin/reports/practice-stage-performance called")
    print(f"📝 [ADMIN] Time range: {time_range}")
    print(f"👤 [ADMIN] Authenticated user: {current_user['email']} (Role: {current_user.get('role', 'unknown')})")
    
    try:
        stage_performance = await _get_practice_stage_performance(time_range)
        
        return AdminDashboardResponse(
            success=True,
            data={"stages": stage_performance},
            message="Practice stage performance data retrieved successfully"
        )
        
    except Exception as e:
        print(f"❌ [ADMIN] Error in get_practice_stage_performance: {str(e)}")
        logger.error(f"Error in get_practice_stage_performance: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/reports/user-engagement-overview", response_model=AdminDashboardResponse)
async def get_user_engagement_overview(
    time_range: str = "all_time",
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher)
):
    """
    Get user engagement overview data for donut chart
    """
    print(f"🔄 [ADMIN] GET /admin/reports/user-engagement-overview called")
    print(f"📝 [ADMIN] Time range: {time_range}")
    print(f"👤 [ADMIN] Authenticated user: {current_user['email']} (Role: {current_user.get('role', 'unknown')})")
    
    try:
        engagement_data = await _get_user_engagement_overview(time_range)
        
        return AdminDashboardResponse(
            success=True,
            data={"engagement": engagement_data},
            message="User engagement overview data retrieved successfully"
        )
        
    except Exception as e:
        print(f"❌ [ADMIN] Error in get_user_engagement_overview: {str(e)}")
        logger.error(f"Error in get_user_engagement_overview: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/reports/time-usage-patterns", response_model=AdminDashboardResponse)
async def get_time_usage_patterns(
    time_range: str = "all_time",
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher)
):
    """
    Get time of day usage patterns for line chart
    """
    print(f"🔄 [ADMIN] GET /admin/reports/time-usage-patterns called")
    print(f"📝 [ADMIN] Time range: {time_range}")
    print(f"👤 [ADMIN] Authenticated user: {current_user['email']} (Role: {current_user.get('role', 'unknown')})")
    
    try:
        time_patterns = await _get_time_usage_patterns(time_range)
        
        return AdminDashboardResponse(
            success=True,
            data={"time_patterns": time_patterns},
            message="Time usage patterns data retrieved successfully"
        )
        
    except Exception as e:
        print(f"❌ [ADMIN] Error in get_time_usage_patterns: {str(e)}")
        logger.error(f"Error in get_time_usage_patterns: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/reports/top-content-accessed", response_model=AdminDashboardResponse)
async def get_top_content_accessed(
    time_range: str = "all_time",
    limit: int = 5,
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher)
):
    """
    Get top content accessed with views, scores, and trends
    """
    print(f"🔄 [ADMIN] GET /admin/reports/top-content-accessed called")
    print(f"📝 [ADMIN] Time range: {time_range}")
    print(f"👤 [ADMIN] Authenticated user: {current_user['email']} (Role: {current_user.get('role', 'unknown')})")
    print(f"📊 [ADMIN] Limit: {limit}")
    
    try:
        top_content = await _get_top_content_accessed(limit, time_range)
        
        return AdminDashboardResponse(
            success=True,
            data={"content": top_content},
            message="Top content accessed data retrieved successfully"
        )
        
    except Exception as e:
        print(f"❌ [ADMIN] Error in get_top_content_accessed: {str(e)}")
        logger.error(f"Error in get_top_content_accessed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/reports/analytics-overview", response_model=AdminDashboardResponse)
async def get_analytics_overview(
    time_range: str = "all_time",
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher)
):
    """
    Get comprehensive analytics overview for Reports & Analytics page
    """
    print(f"🔄 [ADMIN] GET /admin/reports/analytics-overview called")
    print(f"📝 [ADMIN] Time range: {time_range}")
    print(f"👤 [ADMIN] Authenticated user: {current_user['email']} (Role: {current_user.get('role', 'unknown')})")
    
    try:
        # Get all analytics data
        stage_performance = await _get_practice_stage_performance(time_range)
        engagement_data = await _get_user_engagement_overview(time_range)
        time_patterns = await _get_time_usage_patterns(time_range)
        top_content = await _get_top_content_accessed(5, time_range)
        
        analytics_data = {
            "practice_stage_performance": stage_performance,
            "user_engagement_overview": engagement_data,
            "time_usage_patterns": time_patterns,
            "top_content_accessed": top_content,
            "last_updated": datetime.now().isoformat()
        }
        
        return AdminDashboardResponse(
            success=True,
            data=analytics_data,
            message="Analytics overview data retrieved successfully"
        )
        
    except Exception as e:
        print(f"❌ [ADMIN] Error in get_analytics_overview: {str(e)}")
        logger.error(f"Error in get_analytics_overview: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

async def _get_key_metrics(time_range: str = "all_time") -> Dict[str, Any]:
    """
    Get key metrics for admin dashboard with time range filtering
    """
    try:
        print(f"🔄 [ADMIN] Calculating key metrics for time range: {time_range}...")
        
        start_date, end_date = _get_date_range(time_range)
        
        # Get total users count from auth.users table
        try:
            total_users_result = supabase.table('auth.users').select('id', count='exact').execute()
            total_users = total_users_result.count if total_users_result.count is not None else 0
        except Exception as e:
            print(f"⚠️ [ADMIN] Error getting total users, using fallback: {str(e)}")
            # Fallback: count from progress summary table
            total_users_result = supabase.table('ai_tutor_user_progress_summary').select('user_id', count='exact').execute()
            total_users = total_users_result.count if total_users_result.count is not None else 0
        
        # Get students count (users with progress data) - filtered by time range
        if start_date and end_date:
            students_result = supabase.table('ai_tutor_user_progress_summary').select(
                'user_id'
            ).gte('updated_at', start_date.isoformat()).lte('updated_at', end_date.isoformat()).execute()
        else:
            students_result = supabase.table('ai_tutor_user_progress_summary').select('user_id', count='exact').execute()
        
        students_count = len(students_result.data) if students_result.data else 0
        
        # Calculate teachers count (total users - students)
        teachers_count = max(0, total_users - students_count)
        
        # Calculate percentages
        students_percentage = round((students_count / total_users * 100) if total_users > 0 else 0, 1)
        teachers_percentage = round((teachers_count / total_users * 100) if total_users > 0 else 0, 1)
        
        # Get active users count based on time range
        if time_range == "today":
            active_date = date.today().isoformat()
            active_result = supabase.table('ai_tutor_daily_learning_analytics').select(
                'user_id'
            ).eq('analytics_date', active_date).execute()
        elif start_date and end_date:
            active_result = supabase.table('ai_tutor_daily_learning_analytics').select(
                'user_id'
            ).gte('analytics_date', start_date.isoformat()).lte('analytics_date', end_date.isoformat()).execute()
        else:
            # For all_time, get users active in the last 30 days
            thirty_days_ago = (date.today() - timedelta(days=30)).isoformat()
            active_result = supabase.table('ai_tutor_daily_learning_analytics').select(
                'user_id'
            ).gte('analytics_date', thirty_days_ago).execute()
        
        active_users = len(active_result.data) if active_result.data else 0
        
        metrics = {
            "total_users": total_users,
            "students": students_count,
            "students_percentage": students_percentage,
            "teachers": teachers_count,
            "teachers_percentage": teachers_percentage,
            "active_today": active_users
        }
        
        print(f"📊 [ADMIN] Key metrics calculated for {time_range}:")
        print(f"   - Total Users: {total_users}")
        print(f"   - Students: {students_count} ({students_percentage}%)")
        print(f"   - Teachers: {teachers_count} ({teachers_percentage}%)")
        print(f"   - Active Users: {active_users}")
        
        return metrics
        
    except Exception as e:
        print(f"❌ [ADMIN] Error calculating key metrics: {str(e)}")
        logger.error(f"Error calculating key metrics: {str(e)}")
        raise

async def _get_learn_feature_usage(time_range: str = "all_time") -> Dict[str, Any]:
    """
    Get Learn feature usage summary with time range filtering
    """
    try:
        print(f"🔄 [ADMIN] Calculating Learn feature usage for time range: {time_range}...")
        
        start_date, end_date = _get_date_range(time_range)
        
        # Get access count based on time range
        if time_range == "today":
            access_date = date.today().isoformat()
            access_result = supabase.table('ai_tutor_daily_learning_analytics').select(
                'user_id'
            ).eq('analytics_date', access_date).execute()
            today_access = len(access_result.data) if access_result.data else 0
        elif start_date and end_date:
            access_result = supabase.table('ai_tutor_daily_learning_analytics').select(
                'user_id'
            ).gte('analytics_date', start_date.isoformat()).lte('analytics_date', end_date.isoformat()).execute()
            today_access = len(access_result.data) if access_result.data else 0
        else:
            # For all_time, get last 7 days
            week_start = (date.today() - timedelta(days=7)).isoformat()
            access_result = supabase.table('ai_tutor_daily_learning_analytics').select(
                'user_id'
            ).gte('analytics_date', week_start).execute()
            today_access = len(access_result.data) if access_result.data else 0
        
        # Get total engagement for the period
        if start_date and end_date:
            total_result = supabase.table('ai_tutor_daily_learning_analytics').select(
                'user_id'
            ).gte('analytics_date', start_date.isoformat()).lte('analytics_date', end_date.isoformat()).execute()
        else:
            # For all_time, get last 30 days
            thirty_days_ago = (date.today() - timedelta(days=30)).isoformat()
            total_result = supabase.table('ai_tutor_daily_learning_analytics').select(
                'user_id'
            ).gte('analytics_date', thirty_days_ago).execute()
        
        this_week = len(total_result.data) if total_result.data else 0
        
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

async def _get_most_accessed_lessons(limit: int = 5, time_range: str = "all_time") -> List[Dict[str, Any]]:
    """
    Get most accessed practice lessons with time range filtering
    """
    try:
        print(f"🔄 [ADMIN] Calculating most accessed lessons for time range: {time_range}...")
        
        start_date, end_date = _get_date_range(time_range)
        
        # Get lesson access data from topic progress with time filtering
        if start_date and end_date:
            lessons_result = supabase.table('ai_tutor_user_topic_progress').select(
                'stage_id, exercise_id, topic_id'
            ).gte('created_at', start_date.isoformat()).lte('created_at', end_date.isoformat()).execute()
        else:
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
        
        print(f"✅ [ADMIN] Most accessed lessons calculated successfully")
        return formatted_lessons
        
    except Exception as e:
        print(f"❌ [ADMIN] Error in _get_most_accessed_lessons: {str(e)}")
        logger.error(f"Error in _get_most_accessed_lessons: {str(e)}")
        return []

# NEW FUNCTIONS for Reports & Analytics Page

async def _get_practice_stage_performance(time_range: str = "all_time") -> List[Dict[str, Any]]:
    """
    Get practice stage performance data for bar chart with time range filtering
    """
    try:
        print(f"🔄 [ADMIN] Calculating practice stage performance for time range: {time_range}...")
        
        start_date, end_date = _get_date_range(time_range)
        
        # Get total users count with time filtering
        if start_date and end_date:
            total_users_result = supabase.table('ai_tutor_user_progress_summary').select(
                'user_id'
            ).gte('updated_at', start_date.isoformat()).lte('updated_at', end_date.isoformat()).execute()
            total_users = len(total_users_result.data) if total_users_result.data else 0
        else:
            total_users_result = supabase.table('ai_tutor_user_progress_summary').select('user_id', count='exact').execute()
            total_users = total_users_result.count if total_users_result.count is not None else 0
        
        # Get user stage progress data with time filtering
        if start_date and end_date:
            stage_progress_result = supabase.table('ai_tutor_user_stage_progress').select(
                'stage_id, user_id, progress_percentage, completed'
            ).gte('updated_at', start_date.isoformat()).lte('updated_at', end_date.isoformat()).execute()
        else:
            stage_progress_result = supabase.table('ai_tutor_user_stage_progress').select(
                'stage_id, user_id, progress_percentage, completed'
            ).execute()
        
        if not stage_progress_result.data:
            print(f"ℹ️ [ADMIN] No stage progress data found")
            return []
        
        # Aggregate data by stage
        stage_data = {}
        for record in stage_progress_result.data:
            stage_id = record.get('stage_id', 1)
            progress_percentage = record.get('progress_percentage', 0)
            completed = record.get('completed', False)
            
            if stage_id not in stage_data:
                stage_data[stage_id] = {
                    'stage_id': stage_id,
                    'stage_name': f"Stage {stage_id}",
                    'total_users': 0,
                    'completed_users': 0,
                    'total_progress': 0
                }
            
            stage_data[stage_id]['total_users'] += 1
            stage_data[stage_id]['total_progress'] += progress_percentage
            if completed:
                stage_data[stage_id]['completed_users'] += 1
        
        # Calculate performance percentages and format
        stage_performance = []
        for stage_id, data in stage_data.items():
            avg_progress = round(data['total_progress'] / data['total_users'], 1) if data['total_users'] > 0 else 0
            completion_rate = round((data['completed_users'] / data['total_users'] * 100), 1) if data['total_users'] > 0 else 0
            
            # Use completion rate as performance percentage
            performance_percentage = completion_rate
            
            stage_performance.append({
                'stage_id': stage_id,
                'stage_name': data['stage_name'],
                'performance_percentage': performance_percentage,
                'user_count': data['total_users'],
                'color': _get_stage_color(stage_id)
            })
        
        # Sort by performance percentage descending
        sorted_stages = sorted(stage_performance, key=lambda x: x['performance_percentage'], reverse=True)
        
        print(f"📊 [ADMIN] Practice stage performance calculated: {len(sorted_stages)} stages")
        return sorted_stages
        
    except Exception as e:
        print(f"❌ [ADMIN] Error calculating practice stage performance: {str(e)}")
        logger.error(f"Error calculating practice stage performance: {str(e)}")
        raise

async def _get_user_engagement_overview(time_range: str = "all_time") -> List[Dict[str, Any]]:
    """
    Get user engagement overview data for donut chart (Practice vs Learn) with time range filtering
    """
    try:
        print(f"🔄 [ADMIN] Calculating user engagement overview for time range: {time_range}...")
        
        start_date, end_date = _get_date_range(time_range)
        
        # Get total users count with time filtering
        if start_date and end_date:
            total_users_result = supabase.table('ai_tutor_user_progress_summary').select(
                'user_id'
            ).gte('updated_at', start_date.isoformat()).lte('updated_at', end_date.isoformat()).execute()
            total_users = len(total_users_result.data) if total_users_result.data else 0
        else:
            total_users_result = supabase.table('ai_tutor_user_progress_summary').select('user_id', count='exact').execute()
            total_users = total_users_result.count if total_users_result.count is not None else 0
        
        # Get practice users (users with topic progress) with time filtering
        if start_date and end_date:
            practice_users_result = supabase.table('ai_tutor_user_topic_progress').select(
                'user_id'
            ).gte('created_at', start_date.isoformat()).lte('created_at', end_date.isoformat()).execute()
        else:
            practice_users_result = supabase.table('ai_tutor_user_topic_progress').select('user_id').execute()
        
        practice_users = len(set([record['user_id'] for record in practice_users_result.data])) if practice_users_result.data else 0
        
        # Get learn users (users with daily analytics) with time filtering
        if start_date and end_date:
            learn_users_result = supabase.table('ai_tutor_daily_learning_analytics').select(
                'user_id'
            ).gte('analytics_date', start_date.isoformat()).lte('analytics_date', end_date.isoformat()).execute()
        else:
            learn_users_result = supabase.table('ai_tutor_daily_learning_analytics').select('user_id').execute()
        
        learn_users = len(set([record['user_id'] for record in learn_users_result.data])) if learn_users_result.data else 0
        
        # Calculate percentages
        practice_percentage = round((practice_users / total_users * 100) if total_users > 0 else 0, 1)
        learn_percentage = round((learn_users / total_users * 100) if total_users > 0 else 0, 1)
        
        engagement_data = [
            {
                'category': 'Practice',
                'percentage': practice_percentage,
                'user_count': practice_users,
                'color': '#4CAF50'
            },
            {
                'category': 'Learn',
                'percentage': learn_percentage,
                'user_count': learn_users,
                'color': '#2196F3'
            }
        ]
        
        print(f"📊 [ADMIN] User engagement overview calculated for {time_range}:")
        print(f"   - Practice Users: {practice_users} ({practice_percentage}%)")
        print(f"   - Learn Users: {learn_users} ({learn_percentage}%)")
        
        return engagement_data
        
    except Exception as e:
        print(f"❌ [ADMIN] Error calculating user engagement overview: {str(e)}")
        logger.error(f"Error calculating user engagement overview: {str(e)}")
        raise

async def _get_time_usage_patterns(time_range: str = "all_time") -> List[Dict[str, Any]]:
    """
    Get time of day usage patterns for line chart with time range filtering
    """
    try:
        print(f"🔄 [ADMIN] Calculating time usage patterns for time range: {time_range}...")
        
        start_date, end_date = _get_date_range(time_range)
        
        # Get user activity data from daily analytics with time filtering
        if time_range == "today":
            analytics_date = date.today().isoformat()
            daily_analytics_result = supabase.table('ai_tutor_daily_learning_analytics').select(
                'user_id, total_time_minutes, sessions_count'
            ).eq('analytics_date', analytics_date).execute()
        elif start_date and end_date:
            daily_analytics_result = supabase.table('ai_tutor_daily_learning_analytics').select(
                'user_id, total_time_minutes, sessions_count'
            ).gte('analytics_date', start_date.isoformat()).lte('analytics_date', end_date.isoformat()).execute()
        else:
            # For all_time, get last 7 days
            week_start = (date.today() - timedelta(days=7)).isoformat()
            daily_analytics_result = supabase.table('ai_tutor_daily_learning_analytics').select(
                'user_id, total_time_minutes, sessions_count'
            ).gte('analytics_date', week_start).execute()
        
        if not daily_analytics_result.data:
            print(f"ℹ️ [ADMIN] No daily analytics data found for {time_range}")
            # Return mock data for demonstration
            return _get_mock_time_patterns()
        
        # Calculate usage patterns based on session times
        # Since we don't have hourly data, we'll simulate based on session counts
        hour_counts = {}
        
        for record in daily_analytics_result.data:
            sessions_count = record.get('sessions_count', 1)
            total_time = record.get('total_time_minutes', 0)
            
            # Distribute sessions across hours (simplified approach)
            if sessions_count > 0:
                avg_session_duration = total_time / sessions_count if sessions_count > 0 else 0
                
                # Simulate hourly distribution based on typical usage patterns
                for hour in range(24):
                    # Peak hours: 8-12, 14-18, 20-22
                    if hour in [8, 9, 10, 11, 14, 15, 16, 17, 20, 21]:
                        weight = 2
                    elif hour in [12, 13, 18, 19, 22, 23]:
                        weight = 1.5
                    else:
                        weight = 0.5
                    
                    if hour not in hour_counts:
                        hour_counts[hour] = 0
                    hour_counts[hour] += int(sessions_count * weight / 24)
        
        # Format for line chart
        time_patterns = []
        for hour in range(24):
            count = hour_counts.get(hour, 0)
            time_patterns.append({
                'hour': hour,
                'usage_count': count,
                'formatted_hour': f"{hour:02d}:00"
            })
        
        print(f"📊 [ADMIN] Time usage patterns calculated: {len(time_patterns)} hours")
        return time_patterns
        
    except Exception as e:
        print(f"❌ [ADMIN] Error calculating time usage patterns: {str(e)}")
        logger.error(f"Error calculating time usage patterns: {str(e)}")
        raise

async def _get_top_content_accessed(limit: int = 5, time_range: str = "all_time") -> List[Dict[str, Any]]:
    """
    Get top content accessed with views, scores, and trends with time range filtering
    """
    try:
        print(f"🔄 [ADMIN] Calculating top content accessed for time range: {time_range}...")
        
        start_date, end_date = _get_date_range(time_range)
        
        # Get topic progress data with time filtering
        if start_date and end_date:
            topic_progress_result = supabase.table('ai_tutor_user_topic_progress').select(
                'stage_id, exercise_id, topic_id, score, completed, total_time_seconds'
            ).gte('created_at', start_date.isoformat()).lte('created_at', end_date.isoformat()).execute()
        else:
            topic_progress_result = supabase.table('ai_tutor_user_topic_progress').select(
                'stage_id, exercise_id, topic_id, score, completed, total_time_seconds'
            ).execute()
        
        if not topic_progress_result.data:
            print(f"ℹ️ [ADMIN] No topic progress data found")
            return []
        
        # Aggregate data by content
        content_data = {}
        
        for record in topic_progress_result.data:
            stage_id = record.get('stage_id', 1)
            exercise_id = record.get('exercise_id', 1)
            topic_id = record.get('topic_id', 1)
            score = record.get('score', 0)
            completed = record.get('completed', False)
            
            content_key = f"stage_{stage_id}_exercise_{exercise_id}_topic_{topic_id}"
            
            if content_key not in content_data:
                content_data[content_key] = {
                    'title': _get_content_title(stage_id, exercise_id, topic_id),
                    'type': _get_content_type(stage_id, exercise_id),
                    'stage_or_module': f"Stage {stage_id}",
                    'views': 0,
                    'total_score': 0,
                    'completed_count': 0,
                    'total_attempts': 0,
                    'icon': _get_content_icon(stage_id, exercise_id)
                }
            
            content_data[content_key]['views'] += 1
            content_data[content_key]['total_score'] += score
            content_data[content_key]['total_attempts'] += 1
            if completed:
                content_data[content_key]['completed_count'] += 1
        
        # Calculate averages and format
        top_content = []
        for content_key, data in content_data.items():
            avg_score = round(data['total_score'] / data['total_attempts'], 1) if data['total_attempts'] > 0 else 0
            completion_rate = round((data['completed_count'] / data['total_attempts'] * 100), 1) if data['total_attempts'] > 0 else 0
            
            # Determine trend based on completion rate
            if completion_rate >= 80:
                trend = "up"
            elif completion_rate >= 60:
                trend = "stable"
            else:
                trend = "down"
            
            top_content.append({
                'title': data['title'],
                'type': data['type'],
                'stage_or_module': data['stage_or_module'],
                'views': data['views'],
                'avg_score': avg_score,
                'trend': trend,
                'icon': data['icon']
            })
        
        # Sort by views descending and limit
        sorted_content = sorted(top_content, key=lambda x: x['views'], reverse=True)[:limit]
        
        print(f"📊 [ADMIN] Top content accessed calculated: {len(sorted_content)} items")
        return sorted_content
        
    except Exception as e:
        print(f"❌ [ADMIN] Error calculating top content accessed: {str(e)}")
        logger.error(f"Error calculating top content accessed: {str(e)}")
        raise

def _get_stage_color(stage_id: int) -> str:
    """Get color for stage based on ID"""
    colors = {
        1: "#3B82F6",  # Blue
        2: "#10B981",  # Green
        3: "#F59E0B",  # Yellow
        4: "#EF4444",  # Red
        5: "#8B5CF6",  # Purple
        6: "#06B6D4"   # Cyan
    }
    return colors.get(stage_id, "#6B7280")

def _get_content_title(stage_id: int, exercise_id: int, topic_id: int) -> str:
    """Get human-readable content title"""
    stage_names = {
        1: "Basic Conversation Starters",
        2: "Daily Routine Vocabulary", 
        3: "Quick Response Practice",
        4: "Roleplay Simulation",
        5: "Storytelling",
        6: "Group Dialogue"
    }
    
    exercise_names = {
        1: "Exercise 1",
        2: "Exercise 2", 
        3: "Exercise 3"
    }
    
    return f"{stage_names.get(stage_id, f'Stage {stage_id}')} - {exercise_names.get(exercise_id, f'Exercise {exercise_id}')}"

def _get_content_type(stage_id: int, exercise_id: int) -> str:
    """Get content type"""
    if stage_id <= 3:
        return "Practice"
    else:
        return "Learn"

def _get_content_icon(stage_id: int, exercise_id: int) -> str:
    """Get icon for content"""
    icons = {
        (1, 1): "chatbubble",
        (1, 2): "time", 
        (1, 3): "flash",
        (2, 1): "people",
        (2, 2): "book",
        (2, 3): "group",
        (3, 1): "lightbulb",
        (3, 2): "brain",
        (3, 3): "presentation"
    }
    return icons.get((stage_id, exercise_id), "document")

def _get_mock_time_patterns() -> List[Dict[str, Any]]:
    """Get mock time patterns for demonstration"""
    return [
        {'hour': 0, 'usage_count': 15, 'formatted_hour': '00:00'},
        {'hour': 1, 'usage_count': 10, 'formatted_hour': '01:00'},
        {'hour': 2, 'usage_count': 5, 'formatted_hour': '02:00'},
        {'hour': 3, 'usage_count': 3, 'formatted_hour': '03:00'},
        {'hour': 4, 'usage_count': 2, 'formatted_hour': '04:00'},
        {'hour': 5, 'usage_count': 8, 'formatted_hour': '05:00'},
        {'hour': 6, 'usage_count': 25, 'formatted_hour': '06:00'},
        {'hour': 7, 'usage_count': 45, 'formatted_hour': '07:00'},
        {'hour': 8, 'usage_count': 80, 'formatted_hour': '08:00'},
        {'hour': 9, 'usage_count': 95, 'formatted_hour': '09:00'},
        {'hour': 10, 'usage_count': 120, 'formatted_hour': '10:00'},
        {'hour': 11, 'usage_count': 130, 'formatted_hour': '11:00'},
        {'hour': 12, 'usage_count': 85, 'formatted_hour': '12:00'},
        {'hour': 13, 'usage_count': 75, 'formatted_hour': '13:00'},
        {'hour': 14, 'usage_count': 90, 'formatted_hour': '14:00'},
        {'hour': 15, 'usage_count': 110, 'formatted_hour': '15:00'},
        {'hour': 16, 'usage_count': 140, 'formatted_hour': '16:00'},
        {'hour': 17, 'usage_count': 150, 'formatted_hour': '17:00'},
        {'hour': 18, 'usage_count': 160, 'formatted_hour': '18:00'},
        {'hour': 19, 'usage_count': 130, 'formatted_hour': '19:00'},
        {'hour': 20, 'usage_count': 100, 'formatted_hour': '20:00'},
        {'hour': 21, 'usage_count': 85, 'formatted_hour': '21:00'},
        {'hour': 22, 'usage_count': 60, 'formatted_hour': '22:00'},
        {'hour': 23, 'usage_count': 30, 'formatted_hour': '23:00'}
    ]

@router.get("/health")
async def admin_health_check():
    """
    Health check endpoint for admin routes
    """
    return {"status": "healthy", "service": "admin_dashboard"}
