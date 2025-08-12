from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging
from datetime import date, datetime, timedelta
from app.supabase_client import supabase, progress_tracker
from app.auth_middleware import get_current_user, require_admin_or_teacher
import json

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/teacher", tags=["Teacher Dashboard"])

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
    elif time_range == "this_year":
        start_date = today.replace(month=1, day=1)
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
class TeacherDashboardResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None
    message: Optional[str] = None

class LearnFeatureEngagementSummary(BaseModel):
    total_students_engaged: int
    active_today: int
    total_time_spent_hours: float
    time_period: str
    avg_responses_per_student: int
    responses_period: str
    engagement_rate: float
    engagement_change: str

class TopUsedPracticeLesson(BaseModel):
    lesson_name: str
    stage: str
    access_count: int
    trend: str

# New Pydantic models for student details
class StudentBasicInfo(BaseModel):
    user_id: str
    student_name: str
    email: str
    phone: Optional[str] = None
    role: str
    first_activity_date: str
    last_activity_date: str

class StudentProgressOverview(BaseModel):
    current_stage: int
    current_exercise: int
    overall_progress_percentage: float
    total_time_spent_minutes: int
    total_exercises_completed: int
    streak_days: int
    longest_streak: int
    average_session_duration_minutes: float
    weekly_learning_hours: float
    monthly_learning_hours: float

class StageProgress(BaseModel):
    stage_id: int
    stage_name: str
    completed: bool
    mature: bool
    average_score: float
    progress_percentage: float
    total_score: float
    best_score: float
    time_spent_minutes: int
    attempts_count: int
    exercises_completed: int
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    last_attempt_at: Optional[str] = None

class ExerciseProgress(BaseModel):
    stage_id: int
    exercise_id: int
    exercise_name: str
    attempts: int
    average_score: float
    best_score: float
    total_score: float
    time_spent_minutes: int
    mature: bool
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    last_attempt_at: Optional[str] = None

class LearningMilestone(BaseModel):
    milestone_type: str
    milestone_title: str
    milestone_description: str
    milestone_value: Optional[str] = None
    earned_at: str
    is_notified: bool

class WeeklyProgress(BaseModel):
    week_start_date: str
    total_sessions: int
    total_time_hours: float
    average_daily_time_minutes: float
    average_score: float
    score_improvement: float
    consistency_score: float
    stages_completed: int
    exercises_mastered: int
    milestones_earned: int
    weekly_recommendations: List[str]

class DailyAnalytics(BaseModel):
    analytics_date: str
    sessions_count: int
    total_time_minutes: int
    average_session_duration: float
    average_score: float
    best_score: float
    exercises_attempted: int
    exercises_completed: int

class StudentDetailsResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None
    message: Optional[str] = None

@router.get("/dashboard/overview", response_model=TeacherDashboardResponse)
async def get_teacher_dashboard_overview(
    time_range: str = "all_time",
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher)
):
    """
    Get comprehensive teacher dashboard overview with learn feature engagement summary and top used practice lessons
    """
    print(f"🔄 [TEACHER] GET /teacher/dashboard/overview called")
    print(f"📝 [TEACHER] Time range: {time_range}")
    print(f"👤 [TEACHER] Authenticated user: {current_user['email']} (Role: {current_user.get('role', 'unknown')})")
    
    try:
        # Get all required metrics with time range filtering
        learn_engagement_summary = await _get_learn_feature_engagement_summary(time_range)
        top_used_lessons = await _get_top_used_practice_lessons(time_range=time_range)
        
        dashboard_data = {
            "learn_feature_engagement_summary": learn_engagement_summary,
            "top_used_practice_lessons": top_used_lessons,
            "last_updated": datetime.now().isoformat()
        }
        
        print(f"✅ [TEACHER] Dashboard data retrieved successfully")
        return TeacherDashboardResponse(
            success=True,
            data=dashboard_data,
            message="Teacher dashboard data retrieved successfully"
        )
        
    except Exception as e:
        print(f"❌ [TEACHER] Error in get_teacher_dashboard_overview: {str(e)}")
        logger.error(f"Error in get_teacher_dashboard_overview: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/dashboard/learn-engagement-summary", response_model=TeacherDashboardResponse)
async def get_learn_feature_engagement_summary(
    time_range: str = "all_time",
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher)
):
    """
    Get learn feature engagement summary for teacher dashboard
    """
    print(f"🔄 [TEACHER] GET /teacher/dashboard/learn-engagement-summary called")
    print(f"👤 [TEACHER] Authenticated user: {current_user['email']} (Role: {current_user.get('role', 'unknown')})")
    
    try:
        engagement_summary = await _get_learn_feature_engagement_summary(time_range)
        
        return TeacherDashboardResponse(
            success=True,
            data=engagement_summary,
            message="Learn feature engagement summary retrieved successfully"
        )
        
    except Exception as e:
        print(f"❌ [TEACHER] Error in get_learn_feature_engagement_summary: {str(e)}")
        logger.error(f"Error in get_learn_feature_engagement_summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/dashboard/top-used-lessons", response_model=TeacherDashboardResponse)
async def get_top_used_practice_lessons(
    limit: int = 5,
    time_range: str = "all_time",
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher)
):
    """
    Get top used practice lessons for teacher dashboard
    """
    print(f"🔄 [TEACHER] GET /teacher/dashboard/top-used-lessons called")
    print(f"👤 [TEACHER] Authenticated user: {current_user['email']} (Role: {current_user.get('role', 'unknown')})")
    print(f"📊 [TEACHER] Limit: {limit}")
    
    try:
        lessons = await _get_top_used_practice_lessons(limit, time_range)
        
        return TeacherDashboardResponse(
            success=True,
            data={"lessons": lessons},
            message="Top used practice lessons data retrieved successfully"
        )
        
    except Exception as e:
        print(f"❌ [TEACHER] Error in get_top_used_practice_lessons: {str(e)}")
        logger.error(f"Error in get_top_used_practice_lessons: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

async def _get_learn_feature_engagement_summary(time_range: str = "all_time") -> Dict[str, Any]:
    """
    Get learn feature engagement summary with time range filtering
    """
    try:
        print(f"🔄 [TEACHER] Calculating learn feature engagement summary for time range: {time_range}...")
        
        start_date, end_date = _get_date_range(time_range)
        
        # 1. Total Students Engaged
        if start_date and end_date:
            total_students_result = supabase.table('ai_tutor_user_progress_summary').select(
                'user_id'
            ).gte('updated_at', start_date.isoformat()).lte('updated_at', end_date.isoformat()).execute()
        else:
            total_students_result = supabase.table('ai_tutor_user_progress_summary').select('user_id').execute()
        
        total_students_engaged = len(total_students_result.data) if total_students_result.data else 0
        
        # 2. Active Today
        today_date = date.today().isoformat()
        active_today_result = supabase.table('ai_tutor_daily_learning_analytics').select(
            'user_id'
        ).eq('analytics_date', today_date).execute()
        
        active_today = len(active_today_result.data) if active_today_result.data else 0
        
        # 3. Total Time Spent (in hours)
        if start_date and end_date:
            time_spent_result = supabase.table('ai_tutor_daily_learning_analytics').select(
                'total_time_minutes'
            ).gte('analytics_date', start_date.isoformat()).lte('analytics_date', end_date.isoformat()).execute()
        else:
            time_spent_result = supabase.table('ai_tutor_daily_learning_analytics').select('total_time_minutes').execute()
        
        total_time_minutes = sum([record.get('total_time_minutes', 0) for record in time_spent_result.data]) if time_spent_result.data else 0
        total_time_spent_hours = round(total_time_minutes / 60, 1)
        
        # 4. Average Responses per Student
        if start_date and end_date:
            responses_result = supabase.table('ai_tutor_user_topic_progress').select(
                'user_id'
            ).gte('created_at', start_date.isoformat()).lte('created_at', end_date.isoformat()).execute()
        else:
            responses_result = supabase.table('ai_tutor_user_topic_progress').select('user_id').execute()
        
        total_responses = len(responses_result.data) if responses_result.data else 0
        avg_responses_per_student = round(total_responses / total_students_engaged, 0) if total_students_engaged > 0 else 0
        
        # 5. Engagement Rate (percentage of students who used the learn feature)
        if start_date and end_date:
            engaged_students_result = supabase.table('ai_tutor_daily_learning_analytics').select(
                'user_id'
            ).gte('analytics_date', start_date.isoformat()).lte('analytics_date', end_date.isoformat()).execute()
        else:
            engaged_students_result = supabase.table('ai_tutor_daily_learning_analytics').select('user_id').execute()
        
        engaged_students = len(set([record['user_id'] for record in engaged_students_result.data])) if engaged_students_result.data else 0
        engagement_rate = round((engaged_students / total_students_engaged * 100), 0) if total_students_engaged > 0 else 0
        
        # 6. Engagement Change (compare with previous period)
        engagement_change = await _calculate_engagement_change(time_range, engagement_rate)
        
        # Determine time period labels
        time_period = _get_time_period_label(time_range)
        responses_period = _get_responses_period_label(time_range)
        
        engagement_summary = {
            "total_students_engaged": total_students_engaged,
            "active_today": active_today,
            "total_time_spent_hours": total_time_spent_hours,
            "time_period": time_period,
            "avg_responses_per_student": avg_responses_per_student,
            "responses_period": responses_period,
            "engagement_rate": engagement_rate,
            "engagement_change": engagement_change
        }
        
        print(f"📊 [TEACHER] Learn feature engagement summary calculated:")
        print(f"   - Total Students Engaged: {total_students_engaged}")
        print(f"   - Active Today: {active_today}")
        print(f"   - Total Time Spent: {total_time_spent_hours}h ({time_period})")
        print(f"   - Avg Responses per Student: {avg_responses_per_student} ({responses_period})")
        print(f"   - Engagement Rate: {engagement_rate}% ({engagement_change})")
        
        return engagement_summary
        
    except Exception as e:
        print(f"❌ [TEACHER] Error calculating learn feature engagement summary: {str(e)}")
        logger.error(f"Error calculating learn feature engagement summary: {str(e)}")
        raise

async def _get_top_used_practice_lessons(limit: int = 5, time_range: str = "all_time") -> List[Dict[str, Any]]:
    """
    Get top used practice lessons with time range filtering
    """
    try:
        print(f"🔄 [TEACHER] Calculating top used practice lessons for time range: {time_range}...")
        
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
            print(f"ℹ️ [TEACHER] No lesson access data found")
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
            (1, 1): {"name": "Daily Routine Conversations", "stage": "Stage 1"},
            (1, 2): {"name": "Basic Conversation Starters", "stage": "Stage 1"},
            (1, 3): {"name": "Quick Response Practice", "stage": "Stage 1"},
            
            # Stage 2
            (2, 1): {"name": "Roleplay Simulation", "stage": "Stage 2"},
            (2, 2): {"name": "Storytelling", "stage": "Stage 2"},
            (2, 3): {"name": "Group Dialogue", "stage": "Stage 2"},
            
            # Stage 3
            (3, 1): {"name": "Problem Solving", "stage": "Stage 3"},
            (3, 2): {"name": "Critical Thinking Dialogues", "stage": "Stage 3"},
            (3, 3): {"name": "Academic Presentations", "stage": "Stage 3"},
            
            # Stage 4
            (4, 1): {"name": "Abstract Topic Discussion", "stage": "Stage 4"},
            (4, 2): {"name": "Job Interview Practice", "stage": "Stage 4"},
            (4, 3): {"name": "News Summary", "stage": "Stage 4"},
            
            # Stage 5
            (5, 1): {"name": "In-depth Interview", "stage": "Stage 5"},
            (5, 2): {"name": "Academic Presentation", "stage": "Stage 5"},
            (5, 3): {"name": "Critical Opinion Builder", "stage": "Stage 5"},
            
            # Stage 6
            (6, 1): {"name": "Spontaneous Speech", "stage": "Stage 6"},
            (6, 2): {"name": "Sensitive Scenario", "stage": "Stage 6"},
            (6, 3): {"name": "Advanced Roleplay", "stage": "Stage 6"}
        }
        
        formatted_lessons = []
        for lesson in sorted_lessons:
            stage_id = lesson['stage_id']
            exercise_id = lesson['exercise_id']
            
            lesson_info = lesson_mapping.get((stage_id, exercise_id), {
                "name": f"Stage {stage_id} Exercise {exercise_id}",
                "stage": f"Stage {stage_id}"
            })
            
            # Calculate trend (simplified - you can enhance this based on historical data)
            trend = _calculate_lesson_trend(lesson['accesses'])
            
            formatted_lessons.append({
                "lesson_name": lesson_info["name"],
                "stage": lesson_info["stage"],
                "access_count": lesson['accesses'],
                "trend": trend
            })
        
        print(f"✅ [TEACHER] Top used practice lessons calculated successfully")
        return formatted_lessons
        
    except Exception as e:
        print(f"❌ [TEACHER] Error in _get_top_used_practice_lessons: {str(e)}")
        logger.error(f"Error in _get_top_used_practice_lessons: {str(e)}")
        return []

async def _calculate_engagement_change(time_range: str, current_engagement: float) -> str:
    """
    Calculate engagement change compared to previous period
    """
    try:
        # Get previous period data for comparison
        if time_range == "this_week":
            # Compare with last week
            last_week_start = (date.today() - timedelta(days=date.today().weekday() + 7)).isoformat()
            last_week_end = (date.today() - timedelta(days=date.today().weekday() + 1)).isoformat()
            
            last_week_result = supabase.table('ai_tutor_daily_learning_analytics').select(
                'user_id'
            ).gte('analytics_date', last_week_start).lte('analytics_date', last_week_end).execute()
            
            last_week_engaged = len(set([record['user_id'] for record in last_week_result.data])) if last_week_result.data else 0
            
            # Get total students for last week
            last_week_students_result = supabase.table('ai_tutor_user_progress_summary').select(
                'user_id'
            ).gte('updated_at', last_week_start).lte('updated_at', last_week_end).execute()
            
            last_week_total = len(last_week_students_result.data) if last_week_students_result.data else 1
            last_week_engagement = (last_week_engaged / last_week_total * 100) if last_week_total > 0 else 0
            
        elif time_range == "this_month":
            # Compare with last month
            last_month_start = (date.today().replace(day=1) - timedelta(days=1)).replace(day=1).isoformat()
            last_month_end = (date.today().replace(day=1) - timedelta(days=1)).isoformat()
            
            last_month_result = supabase.table('ai_tutor_daily_learning_analytics').select(
                'user_id'
            ).gte('analytics_date', last_month_start).lte('analytics_date', last_month_end).execute()
            
            last_month_engaged = len(set([record['user_id'] for record in last_month_result.data])) if last_month_result.data else 0
            
            # Get total students for last month
            last_month_students_result = supabase.table('ai_tutor_user_progress_summary').select(
                'user_id'
            ).gte('updated_at', last_month_start).lte('updated_at', last_month_end).execute()
            
            last_month_total = len(last_month_students_result.data) if last_month_students_result.data else 1
            last_month_engagement = (last_month_engaged / last_month_total * 100) if last_month_total > 0 else 0
            
        else:
            # For other time ranges, return a default positive change
            return "+0% from last week"
        
        # Calculate change
        if time_range == "this_week":
            change = current_engagement - last_week_engagement
            change_text = f"{'+' if change >= 0 else ''}{round(change, 0)}% from last week"
        elif time_range == "this_month":
            change = current_engagement - last_month_engagement
            change_text = f"{'+' if change >= 0 else ''}{round(change, 0)}% from last month"
        else:
            change_text = "+0% from last week"
        
        return change_text
        
    except Exception as e:
        print(f"⚠️ [TEACHER] Error calculating engagement change: {str(e)}")
        return "+0% from last week"

def _get_time_period_label(time_range: str) -> str:
    """Get time period label for display"""
    if time_range == "today":
        return "Today"
    elif time_range == "this_week":
        return "This week"
    elif time_range == "this_month":
        return "This month"
    elif time_range == "this_year":
        return "This year"
    else:
        return "All time"

def _get_responses_period_label(time_range: str) -> str:
    """Get responses period label for display"""
    if time_range == "today":
        return "Per student today"
    elif time_range == "this_week":
        return "Per student this week"
    elif time_range == "this_month":
        return "Per student this month"
    elif time_range == "this_year":
        return "Per student this year"
    else:
        return "Per student all time"

def _calculate_lesson_trend(access_count: int) -> str:
    """Calculate trend for lesson based on access count"""
    if access_count > 100:
        return "Up"
    elif access_count > 50:
        return "Stable"
    else:
        return "Down"

@router.get("/dashboard/behavior-insights", response_model=TeacherDashboardResponse)
async def get_behavior_insights(
    time_range: str = "all_time",
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher)
):
    """
    Get behavior insights for teacher dashboard (only features possible with existing database)
    """
    print(f"🔄 [TEACHER] GET /teacher/dashboard/behavior-insights called")
    print(f"👤 [TEACHER] Authenticated user: {current_user['email']} (Role: {current_user.get('role', 'unknown')})")
    
    try:
        behavior_insights = await _get_behavior_insights(time_range)
        
        return TeacherDashboardResponse(
            success=True,
            data=behavior_insights,
            message="Behavior insights retrieved successfully"
        )
        
    except Exception as e:
        print(f"❌ [TEACHER] Error in get_behavior_insights: {str(e)}")
        logger.error(f"Error in get_behavior_insights: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/dashboard/high-retry-students", response_model=TeacherDashboardResponse)
async def get_high_retry_students(
    stage_id: Optional[int] = None,
    retry_threshold: int = 5,
    time_range: str = "all_time",
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher)
):
    """
    Get students with high retry rates (excessive retries)
    """
    print(f"🔄 [TEACHER] GET /teacher/dashboard/high-retry-students called")
    print(f"👤 [TEACHER] Authenticated user: {current_user['email']} (Role: {current_user.get('role', 'unknown')})")
    print(f"📊 [TEACHER] Stage ID: {stage_id}, Retry Threshold: {retry_threshold}")
    
    try:
        high_retry_data = await _get_high_retry_students(stage_id, retry_threshold, time_range)
        
        return TeacherDashboardResponse(
            success=True,
            data=high_retry_data,
            message="High retry students data retrieved successfully"
        )
        
    except Exception as e:
        print(f"❌ [TEACHER] Error in get_high_retry_students: {str(e)}")
        logger.error(f"Error in get_high_retry_students: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/dashboard/stuck-students", response_model=TeacherDashboardResponse)
async def get_stuck_students(
    stage_id: Optional[int] = None,
    days_threshold: int = 7,
    time_range: str = "all_time",
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher)
):
    """
    Get students who are stuck at their current stage for a specified number of days
    """
    print(f"🔄 [TEACHER] GET /teacher/dashboard/stuck-students called")
    print(f"👤 [TEACHER] Authenticated user: {current_user['email']} (Role: {current_user.get('role', 'unknown')})")
    print(f"📊 [TEACHER] Stage ID: {stage_id}, Days Threshold: {days_threshold}")
    
    try:
        stuck_students_data = await _get_stuck_students(stage_id, days_threshold, time_range)
        
        return TeacherDashboardResponse(
            success=True,
            data=stuck_students_data,
            message="Stuck students data retrieved successfully"
        )
        
    except Exception as e:
        print(f"❌ [TEACHER] Error in get_stuck_students: {str(e)}")
        logger.error(f"Error in get_stuck_students: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/dashboard/inactive-students", response_model=TeacherDashboardResponse)
async def get_inactive_students(
    stage_id: Optional[int] = None,
    days_threshold: int = 30,
    time_range: str = "all_time",
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher)
):
    """
    Get students who have been inactive for a specified number of days
    """
    print(f"🔄 [TEACHER] GET /teacher/dashboard/inactive-students called")
    print(f"👤 [TEACHER] Authenticated user: {current_user['email']} (Role: {current_user.get('role', 'unknown')})")
    print(f"📊 [TEACHER] Stage ID: {stage_id}, Days Threshold: {days_threshold}")
    
    try:
        inactive_students_data = await _get_inactive_students(stage_id, days_threshold, time_range)
        
        return TeacherDashboardResponse(
            success=True,
            data=inactive_students_data,
            message="Inactive students data retrieved successfully"
        )
        
    except Exception as e:
        print(f"❌ [TEACHER] Error in get_inactive_students: {str(e)}")
        logger.error(f"Error in get_inactive_students: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/dashboard/progress-overview", response_model=TeacherDashboardResponse)
async def get_student_progress_overview(
    search_query: Optional[str] = None,
    stage_id: Optional[int] = None,
    lesson_id: Optional[int] = None,
    time_range: str = "all_time",
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher)
):
    """
    Get comprehensive student progress overview for the Progress tab
    """
    print(f"🔄 [TEACHER] GET /teacher/dashboard/progress-overview called")
    print(f"👤 [TEACHER] Authenticated user: {current_user['email']} (Role: {current_user.get('role', 'unknown')})")
    print(f"📊 [TEACHER] Search: {search_query}, Stage: {stage_id}, Lesson: {lesson_id}")
    
    try:
        progress_data = await _get_student_progress_overview(search_query, stage_id, lesson_id, time_range)
        
        return TeacherDashboardResponse(
            success=True,
            data=progress_data,
            message="Student progress overview retrieved successfully"
        )
        
    except Exception as e:
        print(f"❌ [TEACHER] Error in get_student_progress_overview: {str(e)}")
        logger.error(f"Error in get_student_progress_overview: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/dashboard/progress-metrics", response_model=TeacherDashboardResponse)
async def get_progress_metrics(
    stage_id: Optional[int] = None,
    time_range: str = "all_time",
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher)
):
    """
    Get key progress metrics (Total Students, Average Completion, Average Score, Students at Risk)
    """
    print(f"🔄 [TEACHER] GET /teacher/dashboard/progress-metrics called")
    print(f"👤 [TEACHER] Authenticated user: {current_user['email']} (Role: {current_user.get('role', 'unknown')})")
    print(f"📊 [TEACHER] Stage ID: {stage_id}, Time Range: {time_range}")
    
    try:
        metrics_data = await _get_progress_metrics(stage_id, time_range)
        
        return TeacherDashboardResponse(
            success=True,
            data=metrics_data,
            message="Progress metrics retrieved successfully"
        )
        
    except Exception as e:
        print(f"❌ [TEACHER] Error in get_progress_metrics: {str(e)}")
        logger.error(f"Error in get_progress_metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/dashboard/stages", response_model=TeacherDashboardResponse)
async def get_available_stages(
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher)
):
    """
    Get all available stages for filtering
    """
    print(f"🔄 [TEACHER] GET /teacher/dashboard/stages called")
    print(f"👤 [TEACHER] Authenticated user: {current_user['email']} (Role: {current_user.get('role', 'unknown')})")
    
    try:
        stages_data = _get_available_stages()
        
        return TeacherDashboardResponse(
            success=True,
            data={"stages": stages_data},
            message="Available stages retrieved successfully"
        )
        
    except Exception as e:
        print(f"❌ [TEACHER] Error in get_available_stages: {str(e)}")
        logger.error(f"Error in get_available_stages: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/dashboard/lessons/{stage_id}", response_model=TeacherDashboardResponse)
async def get_lessons_by_stage(
    stage_id: int,
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher)
):
    """
    Get lessons available for a specific stage
    """
    print(f"🔄 [TEACHER] GET /teacher/dashboard/lessons/{stage_id} called")
    print(f"👤 [TEACHER] Authenticated user: {current_user['email']} (Role: {current_user.get('role', 'unknown')})")
    print(f"📊 [TEACHER] Stage ID: {stage_id}")
    
    try:
        lessons_data = _get_lessons_by_stage(stage_id)
        
        return TeacherDashboardResponse(
            success=True,
            data={"lessons": lessons_data},
            message=f"Lessons for stage {stage_id} retrieved successfully"
        )
        
    except Exception as e:
        print(f"❌ [TEACHER] Error in get_lessons_by_stage: {str(e)}")
        logger.error(f"Error in get_lessons_by_stage: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/dashboard/export-progress", response_model=TeacherDashboardResponse)
async def export_progress_data(
    format_type: str = "csv",
    search_query: Optional[str] = None,
    stage_id: Optional[int] = None,
    lesson_id: Optional[int] = None,
    time_range: str = "all_time",
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher)
):
    """
    Export progress data in CSV or PDF format
    """
    print(f"🔄 [TEACHER] GET /teacher/dashboard/export-progress called")
    print(f"👤 [TEACHER] Authenticated user: {current_user['email']} (Role: {current_user.get('role', 'unknown')})")
    print(f"📊 [TEACHER] Format: {format_type}, Search: {search_query}, Stage: {stage_id}")
    
    try:
        export_data = await _export_progress_data(format_type, search_query, stage_id, lesson_id, time_range)
        
        return TeacherDashboardResponse(
            success=True,
            data=export_data,
            message=f"Progress data exported successfully in {format_type.upper()} format"
        )
        
    except Exception as e:
        print(f"❌ [TEACHER] Error in export_progress_data: {str(e)}")
        logger.error(f"Error in export_progress_data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

async def _get_behavior_insights(time_range: str = "all_time") -> Dict[str, Any]:
    """
    Get behavior insights (only features possible with existing database)
    """
    try:
        print(f"🔄 [TEACHER] Calculating behavior insights for time range: {time_range}...")
        
        start_date, end_date = _get_date_range(time_range)
        
        # 1. High Retry Rate Detection (POSSIBLE - using attempt_num)
        high_retry_insight = await _get_high_retry_insight(start_date, end_date)
        
        # 2. Low Engagement Detection (POSSIBLE - using daily analytics)
        low_engagement_insight = await _get_low_engagement_insight(start_date, end_date)
        
        # 3. Inactivity Detection (POSSIBLE - using daily analytics)
        inactivity_insight = await _get_inactivity_insight(start_date, end_date)
        
        # 4. Students Stuck at Stages Detection (POSSIBLE - using progress summary and activity data)
        stuck_students_insight = await _get_stuck_students_insight(start_date, end_date)
        
        behavior_insights = {
            "high_retry_rate": high_retry_insight,
            "low_engagement": low_engagement_insight,
            "inactivity": inactivity_insight,
            "stuck_students": stuck_students_insight,
            "total_flags": sum([
                1 if high_retry_insight['has_alert'] else 0,
                1 if low_engagement_insight['has_alert'] else 0,
                1 if inactivity_insight['has_alert'] else 0,
                1 if stuck_students_insight['has_alert'] else 0
            ])
        }
        
        print(f"✅ [TEACHER] Behavior insights calculated successfully")
        return behavior_insights
        
    except Exception as e:
        print(f"❌ [TEACHER] Error calculating behavior insights: {str(e)}")
        logger.error(f"Error calculating behavior insights: {str(e)}")
        raise

async def _get_high_retry_insight(start_date: Optional[date], end_date: Optional[date]) -> Dict[str, Any]:
    """
    Get high retry rate insight (POSSIBLE - using attempt_num from topic progress)
    """
    try:
        # Get students with high retry rates (more than 5 attempts on any topic)
        retry_query = supabase.table('ai_tutor_user_topic_progress').select(
            'user_id, stage_id, exercise_id, topic_id, attempt_num'
        )
        
        if start_date and end_date:
            retry_query = retry_query.gte('created_at', start_date.isoformat()).lte('created_at', end_date.isoformat())
        
        retry_result = retry_query.execute()
        
        if not retry_result.data:
            return {
                "has_alert": False,
                "message": "No retry data available",
                "affected_students": 0
            }
        
        # Group by user and count total attempts
        user_attempts = {}
        for record in retry_result.data:
            user_id = record['user_id']
            if user_id not in user_attempts:
                user_attempts[user_id] = {
                    'total_attempts': 0,
                    'stages': set(),
                    'topics': set()
                }
            
            user_attempts[user_id]['total_attempts'] += record['attempt_num']
            user_attempts[user_id]['stages'].add(record['stage_id'])
            user_attempts[user_id]['topics'].add(record['topic_id'])
        
        # Find students with excessive retries (>5 attempts)
        excessive_retry_students = []
        for user_id, data in user_attempts.items():
            if data['total_attempts'] > 5:  # Threshold for excessive retries
                # Get real student name from auth.users table
                student_name = await _get_student_name(user_id)
                
                excessive_retry_students.append({
                    'user_id': user_id,
                    'student_name': student_name,
                    'total_attempts': data['total_attempts'],
                    'stages_affected': list(data['stages']),
                    'topics_affected': len(data['topics'])
                })
        
        if not excessive_retry_students:
            return {
                "has_alert": False,
                "message": "No excessive retries detected",
                "affected_students": 0
            }
        
        return {
            "has_alert": True,
            "message": f"{len(excessive_retry_students)} students showing excessive retries",
            "affected_students": len(excessive_retry_students),
            "details": excessive_retry_students
        }
        
    except Exception as e:
        print(f"⚠️ [TEACHER] Error calculating high retry insight: {str(e)}")
        return {
            "has_alert": False,
            "message": "Error calculating retry insight",
            "affected_students": 0
        }

async def _get_high_retry_students(stage_id: Optional[int], retry_threshold: int, time_range: str) -> Dict[str, Any]:
    """
    Get detailed list of students with high retry rates (POSSIBLE - using attempt_num)
    """
    try:
        print(f"🔄 [TEACHER] Getting high retry students with threshold: {retry_threshold}")
        
        start_date, end_date = _get_date_range(time_range)
        
        # Build query for topic progress
        query = supabase.table('ai_tutor_user_topic_progress').select(
            'user_id, stage_id, exercise_id, topic_id, attempt_num, created_at'
        )
        
        if stage_id:
            query = query.eq('stage_id', stage_id)
        
        if start_date and end_date:
            query = query.gte('created_at', start_date.isoformat()).lte('created_at', end_date.isoformat())
        
        result = query.execute()
        
        if not result.data:
            return {
                "students": [],
                "total_affected": 0,
                "stage_filter": stage_id,
                "retry_threshold": retry_threshold
            }
        
        # Group by user and calculate retry statistics
        user_retries = {}
        for record in result.data:
            user_id = record['user_id']
            if user_id not in user_retries:
                user_retries[user_id] = {
                    'total_attempts': 0,
                    'topics_attempted': set(),
                    'stages_worked_on': set(),
                    'last_activity': record['created_at']
                }
            
            user_retries[user_id]['total_attempts'] += record['attempt_num']
            user_retries[user_id]['topics_attempted'].add(record['topic_id'])
            user_retries[user_id]['stages_worked_on'].add(record['stage_id'])
        
        # Filter students above threshold
        high_retry_students = []
        for user_id, data in user_retries.items():
            if data['total_attempts'] >= retry_threshold:
                # Get real student name from auth.users table
                student_name = await _get_student_name(user_id)
                
                student_info = {
                    'user_id': user_id,
                    'student_name': student_name,
                    'retries': data['total_attempts'],
                    'current_lesson': _get_current_lesson_name(list(data['stages_worked_on'])[0] if data['stages_worked_on'] else 1),
                    'stages_affected': list(data['stages_worked_on']),
                    'topics_affected': len(data['topics_attempted']),
                    'last_activity': data['last_activity']
                }
                high_retry_students.append(student_info)
        
        # Sort by retry count (highest first)
        high_retry_students.sort(key=lambda x: x['retries'], reverse=True)
        
        return {
            "students": high_retry_students,
            "total_affected": len(high_retry_students),
            "stage_filter": stage_id,
            "retry_threshold": retry_threshold,
            "time_range": time_range
        }
        
    except Exception as e:
        print(f"❌ [TEACHER] Error in _get_high_retry_students: {str(e)}")
        logger.error(f"Error in _get_high_retry_students: {str(e)}")
        return {
            "students": [],
            "total_affected": 0,
            "error": str(e)
        }

async def _get_low_engagement_insight(start_date: Optional[date], end_date: Optional[date]) -> Dict[str, Any]:
    """
    Get low engagement insight (POSSIBLE - using daily learning analytics)
    """
    try:
        # Get students with low engagement (no activity in last 7 days)
        seven_days_ago = (date.today() - timedelta(days=7)).isoformat()
        
        # Get users with recent activity
        recent_activity_query = supabase.table('ai_tutor_daily_learning_analytics').select(
            'user_id'
        ).gte('analytics_date', seven_days_ago)
        
        if start_date and end_date:
            recent_activity_query = recent_activity_query.gte('analytics_date', start_date.isoformat()).lte('analytics_date', end_date.isoformat())
        
        recent_activity_result = recent_activity_query.execute()
        
        # Get total users
        total_users_result = supabase.table('ai_tutor_user_progress_summary').select('user_id').execute()
        total_users = len(total_users_result.data) if total_users_result.data else 0
        
        if total_users == 0:
            return {
                "has_alert": False,
                "message": "No user data available",
                "affected_students": 0
            }
        
        # Calculate low engagement
        active_users = len(set([record['user_id'] for record in recent_activity_result.data])) if recent_activity_result.data else 0
        low_engagement_users = total_users - active_users
        engagement_rate = (active_users / total_users * 100) if total_users > 0 else 0
        
        if engagement_rate < 50:  # Threshold for low engagement
            return {
                "has_alert": True,
                "message": f"Low engagement detected: {low_engagement_users} inactive students",
                "affected_students": low_engagement_users,
                "engagement_rate": round(engagement_rate, 1)
            }
        else:
            return {
                "has_alert": False,
                "message": f"Engagement is healthy: {round(engagement_rate, 1)}%",
                "affected_students": 0
            }
            
    except Exception as e:
        print(f"⚠️ [TEACHER] Error calculating low engagement insight: {str(e)}")
        return {
            "has_alert": False,
            "message": "Error calculating engagement insight",
            "affected_students": 0
        }

async def _get_inactivity_insight(start_date: Optional[date], end_date: Optional[date]) -> Dict[str, Any]:
    """
    Get inactivity insight (POSSIBLE - using daily learning analytics and progress summary)
    """
    try:
        print(f"🔄 [TEACHER] Calculating inactivity insight...")
        
        # Get inactive students data using the helper function
        inactive_students_data = await _get_inactive_students(None, 30, "all_time")
        inactive_count = inactive_students_data.get('total_affected', 0)
        
        # Get total users for percentage calculation
        total_users_result = supabase.table('ai_tutor_user_progress_summary').select('user_id').execute()
        total_users = len(total_users_result.data) if total_users_result.data else 0
        
        if total_users == 0:
            return {
                "has_alert": False,
                "message": "No user data available",
                "affected_students": 0
            }
        
        # Calculate inactivity rate
        inactivity_rate = round((inactive_count / total_users * 100), 1) if total_users > 0 else 0
        
        if inactive_count > (total_users * 0.2):  # More than 20% inactive
            return {
                "has_alert": True,
                "message": f"High inactivity detected: {inactive_count} inactive students ({inactivity_rate}%)",
                "affected_students": inactive_count,
                "inactivity_rate": inactivity_rate
            }
        else:
            return {
                "has_alert": False,
                "message": f"Inactivity is normal: {inactivity_rate}%",
                "affected_students": 0
            }
            
    except Exception as e:
        print(f"⚠️ [TEACHER] Error calculating inactivity insight: {str(e)}")
        return {
            "has_alert": False,
            "message": "Error calculating inactivity insight",
            "affected_students": 0
        }

async def _get_stuck_students_insight(start_date: Optional[date], end_date: Optional[date]) -> Dict[str, Any]:
    """
    Get stuck students insight (POSSIBLE - using progress summary and activity data)
    """
    try:
        # Get students who haven't progressed from their current stage in 7+ days
        seven_days_ago = (date.today() - timedelta(days=7)).isoformat()
        
        # Get users with recent activity in the last 7 days
        recent_activity_query = supabase.table('ai_tutor_daily_learning_analytics').select(
            'user_id'
        ).gte('analytics_date', seven_days_ago)
        
        if start_date and end_date:
            recent_activity_query = recent_activity_query.gte('analytics_date', start_date.isoformat()).lte('analytics_date', end_date.isoformat())
        
        recent_activity_result = recent_activity_query.execute()
        
        # Get all users with their current stage and last activity
        all_users_query = supabase.table('ai_tutor_user_progress_summary').select(
            'user_id, current_stage, current_exercise, last_activity_date, overall_progress_percentage'
        )
        
        if start_date and end_date:
            all_users_query = all_users_query.gte('updated_at', start_date.isoformat()).lte('updated_at', end_date.isoformat())
        
        all_users_result = all_users_query.execute()
        
        if not all_users_result.data:
            return {
                "has_alert": False,
                "message": "No user data available",
                "affected_students": 0
            }
        
        # Calculate stuck students
        active_users = set([record['user_id'] for record in recent_activity_result.data]) if recent_activity_result.data else set()
        stuck_students = []
        
        for user_record in all_users_result.data:
            user_id = user_record['user_id']
            current_stage = user_record.get('current_stage', 1)
            last_activity = user_record.get('last_activity_date')
            
            # Check if user has been inactive for 7+ days
            if last_activity:
                try:
                    last_activity_date = datetime.strptime(last_activity, '%Y-%m-%d').date()
                    days_inactive = (date.today() - last_activity_date).days
                    
                    if days_inactive >= 7 and user_id not in active_users:
                        # Get real student name
                        student_name = await _get_student_name(user_id)
                        
                        # Get current lesson name
                        current_lesson = _get_current_lesson_name(current_stage)
                        
                        stuck_students.append({
                            'user_id': user_id,
                            'student_name': student_name,
                            'current_stage': _get_stage_display_name(current_stage),
                            'days_stuck': days_inactive,
                            'current_lesson': current_lesson,
                            'progress_percentage': user_record.get('overall_progress_percentage', 0)
                        })
                except (ValueError, TypeError):
                    # Skip if date parsing fails
                    continue
        
        if not stuck_students:
            return {
                "has_alert": False,
                "message": "No students stuck at stages detected",
                "affected_students": 0
            }
        
        # Sort by days stuck (highest first)
        stuck_students.sort(key=lambda x: x['days_stuck'], reverse=True)
        
        return {
            "has_alert": True,
            "message": f"{len(stuck_students)} students haven't progressed from their current stage in 7+ days",
            "affected_students": len(stuck_students),
            "details": stuck_students
        }
        
    except Exception as e:
        print(f"⚠️ [TEACHER] Error calculating stuck students insight: {str(e)}")
        return {
            "has_alert": False,
            "message": "Error calculating stuck students insight",
            "affected_students": 0
        }

async def _get_stuck_students(stage_id: Optional[int], days_threshold: int, time_range: str) -> Dict[str, Any]:
    """
    Get detailed list of students stuck at stages (POSSIBLE - using progress summary and activity data)
    """
    try:
        print(f"🔄 [TEACHER] Getting stuck students with threshold: {days_threshold} days")
        
        start_date, end_date = _get_date_range(time_range)
        
        # Calculate the cutoff date for stuck students
        cutoff_date = (date.today() - timedelta(days=days_threshold)).isoformat()
        
        # Build query for progress summary
        query = supabase.table('ai_tutor_user_progress_summary').select(
            'user_id, current_stage, current_exercise, last_activity_date, overall_progress_percentage, created_at'
        )
        
        if stage_id:
            query = query.eq('current_stage', stage_id)
        
        if start_date and end_date:
            query = query.gte('updated_at', start_date.isoformat()).lte('updated_at', end_date.isoformat())
        
        result = query.execute()
        
        if not result.data:
            return {
                "students": [],
                "total_affected": 0,
                "stage_filter": stage_id,
                "days_threshold": days_threshold
            }
        
        # Get recent activity data for comparison
        recent_activity_query = supabase.table('ai_tutor_daily_learning_analytics').select(
            'user_id'
        ).gte('analytics_date', cutoff_date)
        
        if start_date and end_date:
            recent_activity_query = recent_activity_query.gte('analytics_date', start_date.isoformat()).lte('analytics_date', end_date.isoformat())
        
        recent_activity_result = recent_activity_query.execute()
        active_users = set([record['user_id'] for record in recent_activity_result.data]) if recent_activity_result.data else set()
        
        # Filter stuck students
        stuck_students = []
        for record in result.data:
            user_id = record['user_id']
            last_activity = record.get('last_activity_date')
            
            # Skip if user has recent activity
            if user_id in active_users:
                continue
            
            # Check if user is stuck based on last activity
            if last_activity:
                try:
                    last_activity_date = datetime.strptime(last_activity, '%Y-%m-%d').date()
                    days_inactive = (date.today() - last_activity_date).days
                    
                    if days_inactive >= days_threshold:
                        # Get real student name
                        student_name = await _get_student_name(user_id)
                        
                        # Get current lesson name
                        current_stage = record.get('current_stage', 1)
                        current_lesson = _get_current_lesson_name(current_stage)
                        
                        student_info = {
                            'user_id': user_id,
                            'student_name': student_name,
                            'current_stage': _get_stage_display_name(current_stage),
                            'days_stuck': days_inactive,
                            'current_lesson': current_lesson,
                            'progress_percentage': record.get('overall_progress_percentage', 0),
                            'last_activity': last_activity
                        }
                        stuck_students.append(student_info)
                        
                except (ValueError, TypeError):
                    # Skip if date parsing fails
                    continue
        
        # Sort by days stuck (highest first)
        stuck_students.sort(key=lambda x: x['days_stuck'], reverse=True)
        
        return {
            "students": stuck_students,
            "total_affected": len(stuck_students),
            "stage_filter": stage_id,
            "days_threshold": days_threshold,
            "time_range": time_range
        }
        
    except Exception as e:
        print(f"❌ [TEACHER] Error in _get_stuck_students: {str(e)}")
        logger.error(f"Error in _get_stuck_students: {str(e)}")
        return {
            "students": [],
            "total_affected": 0,
            "error": str(e)
        }

async def _get_inactive_students(stage_id: Optional[int], days_threshold: int, time_range: str) -> Dict[str, Any]:
    """
    Get detailed list of students who have been inactive for a specified number of days
    """
    try:
        print(f"🔄 [TEACHER] Getting inactive students with threshold: {days_threshold} days")
        
        start_date, end_date = _get_date_range(time_range)
        
        # Calculate the cutoff date for inactive students
        cutoff_date = (date.today() - timedelta(days=days_threshold)).isoformat()
        
        # Build query for progress summary
        query = supabase.table('ai_tutor_user_progress_summary').select(
            'user_id, current_stage, current_exercise, last_activity_date, overall_progress_percentage, created_at'
        )
        
        if stage_id:
            query = query.eq('current_stage', stage_id)
        
        if start_date and end_date:
            query = query.gte('updated_at', start_date.isoformat()).lte('updated_at', end_date.isoformat())
        
        result = query.execute()
        
        if not result.data:
            return {
                "students": [],
                "total_affected": 0,
                "stage_filter": stage_id,
                "days_threshold": days_threshold
            }
        
        # Get recent activity data for comparison
        recent_activity_query = supabase.table('ai_tutor_daily_learning_analytics').select(
            'user_id'
        ).gte('analytics_date', cutoff_date)
        
        if start_date and end_date:
            recent_activity_query = recent_activity_query.gte('analytics_date', start_date.isoformat()).lte('analytics_date', end_date.isoformat())
        
        recent_activity_result = recent_activity_query.execute()
        active_users = set([record['user_id'] for record in recent_activity_result.data]) if recent_activity_result.data else set()
        
        # Filter inactive students
        inactive_students = []
        for record in result.data:
            user_id = record['user_id']
            last_activity = record.get('last_activity_date')
            
            # Skip if user has recent activity
            if user_id in active_users:
                continue
            
            # Check if user is inactive based on last activity
            if last_activity:
                try:
                    last_activity_date = datetime.strptime(last_activity, '%Y-%m-%d').date()
                    days_inactive = (date.today() - last_activity_date).days
                    
                    if days_inactive >= days_threshold:
                        # Get real student name
                        student_name = await _get_student_name(user_id)
                        
                        # Get current lesson name
                        current_stage = record.get('current_stage', 1)
                        current_lesson = _get_current_lesson_name(current_stage)
                        
                        student_info = {
                            'user_id': user_id,
                            'student_name': student_name,
                            'current_stage': _get_stage_display_name(current_stage),
                            'days_inactive': days_inactive,
                            'current_lesson': current_lesson,
                            'progress_percentage': record.get('overall_progress_percentage', 0),
                            'last_activity': last_activity
                        }
                        inactive_students.append(student_info)
                        
                except (ValueError, TypeError):
                    # Skip if date parsing fails
                    continue
        
        # Sort by days inactive (highest first)
        inactive_students.sort(key=lambda x: x['days_inactive'], reverse=True)
        
        return {
            "students": inactive_students,
            "total_affected": len(inactive_students),
            "stage_filter": stage_id,
            "days_threshold": days_threshold,
            "time_range": time_range
        }
        
    except Exception as e:
        print(f"❌ [TEACHER] Error in _get_inactive_students: {str(e)}")
        logger.error(f"Error in _get_inactive_students: {str(e)}")
        return {
            "students": [],
            "total_affected": 0,
            "error": str(e)
        }

async def _get_student_progress_overview(search_query: Optional[str], stage_id: Optional[int], lesson_id: Optional[int], time_range: str) -> Dict[str, Any]:
    """
    Get comprehensive student progress overview with detailed student data
    """
    try:
        print(f"🔄 [TEACHER] Getting student progress overview...")
        
        start_date, end_date = _get_date_range(time_range)
        
        # Build base query for student progress
        base_query = supabase.table('ai_tutor_user_progress_summary').select(
            'user_id, current_stage, current_exercise, overall_progress_percentage, last_activity_date, total_time_spent_minutes, total_exercises_completed'
        )
        
        # Apply filters
        if stage_id:
            base_query = base_query.eq('current_stage', stage_id)
        
        if start_date and end_date:
            base_query = base_query.gte('updated_at', start_date.isoformat()).lte('updated_at', end_date.isoformat())
        
        result = base_query.execute()
        
        if not result.data:
            return {
                "students": [],
                "total_students": 0,
                "avg_completion_percentage": 0,
                "avg_score": 0,
                "students_at_risk_count": 0,
                "filters_applied": {
                    "search_query": search_query,
                    "stage_id": stage_id,
                    "lesson_id": lesson_id,
                    "time_range": time_range
                }
            }
        
        # Process student data
        students_data = []
        total_completion = 0
        total_score = 0
        at_risk_count = 0
        
        for record in result.data:
            user_id = record['user_id']
            
            # Get student name and email
            student_name = await _get_student_name(user_id)
            student_email = await _get_student_email(user_id)
            
            # Get current stage and lesson info
            current_stage = record.get('current_stage', 1)
            current_exercise = record.get('current_exercise', 1)
            
            # Calculate average score from exercise progress
            avg_score = await _get_student_average_score(user_id, current_stage)
            
            # Generate AI feedback
            ai_feedback = await _generate_ai_feedback(record, avg_score)
            
            # Get last activity
            last_activity = record.get('last_activity_date', 'Unknown')
            
            # Calculate progress percentage
            progress_percentage = record.get('overall_progress_percentage', 0)
            total_completion += progress_percentage
            total_score += avg_score
            
            # Check if student is at risk
            is_at_risk = progress_percentage < 50 or avg_score < 60
            if is_at_risk:
                at_risk_count += 1
            
            # Apply search filter if provided
            if search_query:
                search_lower = search_query.lower()
                if (search_lower not in student_name.lower() and 
                    search_lower not in student_email.lower()):
                    continue
            
            student_info = {
                'user_id': user_id,
                'student_name': student_name,
                'email': student_email,
                'current_stage': _get_stage_display_name(current_stage),
                'current_lesson': _get_current_lesson_name(current_stage),
                'avg_score': round(avg_score, 1),
                'ai_feedback': ai_feedback['text'],
                'feedback_sentiment': ai_feedback['sentiment'],
                'last_active': last_activity,
                'progress_percentage': round(progress_percentage, 1),
                'is_at_risk': is_at_risk,
                'total_time_minutes': record.get('total_time_spent_minutes', 0),
                'exercises_completed': record.get('total_exercises_completed', 0)
            }
            
            students_data.append(student_info)
        
        # Calculate averages
        total_students = len(students_data)
        avg_completion = round(total_completion / len(result.data), 1) if result.data else 0
        avg_score = round(total_score / len(result.data), 1) if result.data else 0
        
        # Sort students by progress (highest first)
        students_data.sort(key=lambda x: x['progress_percentage'], reverse=True)
        
        return {
            "students": students_data,
            "total_students": total_students,
            "avg_completion_percentage": avg_completion,
            "avg_score": avg_score,
            "students_at_risk_count": at_risk_count,
            "filters_applied": {
                "search_query": search_query,
                "stage_id": stage_id,
                "lesson_id": lesson_id,
                "time_range": time_range
            }
        }
        
    except Exception as e:
        print(f"❌ [TEACHER] Error in _get_student_progress_overview: {str(e)}")
        logger.error(f"Error in _get_student_progress_overview: {str(e)}")
        raise

async def _get_student_email(user_id: str) -> str:
    """
    Get student email from profiles table
    """
    try:
        profile_result = supabase.table('profiles').select('email').eq('id', user_id).execute()
        
        if profile_result.data and len(profile_result.data) > 0:
            return profile_result.data[0].get('email', 'No email')
        
        return 'No email'
        
    except Exception as e:
        print(f"⚠️ [TEACHER] Error getting email for {user_id}: {str(e)}")
        return 'No email'

async def _get_student_average_score(user_id: str, stage_id: int) -> float:
    """
    Get student's average score for a specific stage
    """
    try:
        # Get scores from exercise progress
        score_result = supabase.table('ai_tutor_user_exercise_progress').select(
            'average_score, best_score'
        ).eq('user_id', user_id).eq('stage_id', stage_id).execute()
        
        if not score_result.data:
            return 0.0
        
        # Calculate average of all available scores
        scores = []
        for record in score_result.data:
            if record.get('average_score'):
                scores.append(float(record['average_score']))
            if record.get('best_score'):
                scores.append(float(record['best_score']))
        
        if not scores:
            return 0.0
        
        return round(sum(scores) / len(scores), 1)
        
    except Exception as e:
        print(f"⚠️ [TEACHER] Error getting average score for {user_id}: {str(e)}")
        return 0.0

async def _generate_ai_feedback(progress_record: Dict[str, Any], avg_score: float) -> Dict[str, Any]:
    """
    Generate AI feedback based on student progress data
    """
    try:
        progress_percentage = progress_record.get('overall_progress_percentage', 0)
        current_stage = progress_record.get('current_stage', 1)
        exercises_completed = progress_record.get('total_exercises_completed', 0)
        time_spent = progress_record.get('total_time_spent_minutes', 0)
        
        # Determine feedback sentiment and text based on performance
        if progress_percentage >= 80 and avg_score >= 85:
            sentiment = "positive"
            if current_stage >= 4:
                feedback = "Exceptional performance across all areas. Ready for advanced challenges and leadership roles."
            elif current_stage >= 2:
                feedback = "Shows excellent progress in conversational skills and demonstrates strong learning potential."
            else:
                feedback = "Making excellent progress in foundational skills. Keep up the great work!"
                
        elif progress_percentage >= 60 and avg_score >= 70:
            sentiment = "positive"
            if current_stage >= 3:
                feedback = "Making steady progress with good understanding of concepts. Continue practicing for mastery."
            else:
                feedback = "Shows good progress in basic skills. Regular practice will lead to significant improvement."
                
        elif progress_percentage >= 40 and avg_score >= 60:
            sentiment = "mixed"
            if current_stage >= 3:
                feedback = "Making steady progress but struggling with complex concepts. Additional support and practice needed."
            else:
                feedback = "Basic understanding demonstrated but needs more consistent practice to build confidence."
                
        else:
            sentiment = "negative"
            if current_stage >= 2:
                feedback = "Needs more consistent practice and additional support. Consider reviewing foundational concepts."
            else:
                feedback = "Requires focused attention on basic skills. Regular practice sessions recommended."
        
        # Add stage-specific recommendations
        stage_recommendations = {
            1: "Focus on daily conversation practice and basic vocabulary building.",
            2: "Work on roleplay scenarios and storytelling to improve fluency.",
            3: "Practice problem-solving dialogues and critical thinking exercises.",
            4: "Engage in abstract topic discussions and interview preparation.",
            5: "Focus on in-depth interview skills and academic presentations.",
            6: "Practice spontaneous speech and handle sensitive scenarios confidently."
        }
        
        if current_stage in stage_recommendations:
            feedback += f" {stage_recommendations[current_stage]}"
        
        return {
            "text": feedback,
            "sentiment": sentiment,
            "progress_level": "high" if progress_percentage >= 80 else "medium" if progress_percentage >= 60 else "low"
        }
        
    except Exception as e:
        print(f"⚠️ [TEACHER] Error generating AI feedback: {str(e)}")
        return {
            "text": "Progress data analysis in progress. Continue with current learning path.",
            "sentiment": "neutral",
            "progress_level": "unknown"
        }

async def _get_progress_metrics(stage_id: Optional[int], time_range: str) -> Dict[str, Any]:
    """
    Get key progress metrics (Total Students, Average Completion, Average Score, Students at Risk)
    """
    try:
        print(f"🔄 [TEACHER] Getting progress metrics for stage: {stage_id}, time_range: {time_range}")
        
        start_date, end_date = _get_date_range(time_range)
        
        # 1. Total Students
        total_students_query = supabase.table('ai_tutor_user_progress_summary').select(
            'user_id'
        ).execute()
        total_students = len(total_students_query.data) if total_students_query.data else 0
        
        # 2. Average Completion Percentage
        completion_query = supabase.table('ai_tutor_user_progress_summary').select(
            'overall_progress_percentage'
        ).execute()
        completion_data = [record.get('overall_progress_percentage', 0) for record in completion_query.data]
        avg_completion = round(sum(completion_data) / len(completion_data), 1) if completion_data else 0
        
        # 3. Average Score
        score_query = supabase.table('ai_tutor_user_progress_summary').select(
            'overall_progress_percentage'
        ).execute()
        score_data = [record.get('overall_progress_percentage', 0) for record in score_query.data]
        avg_score = round(sum(score_data) / len(score_data), 1) if score_data else 0
        
        # 4. Students at Risk (defined as students with < 50% completion)
        at_risk_students = []
        if start_date and end_date:
            at_risk_query = supabase.table('ai_tutor_user_progress_summary').select(
                'user_id, overall_progress_percentage'
            ).gte('updated_at', start_date.isoformat()).lte('updated_at', end_date.isoformat())
        else:
            at_risk_query = supabase.table('ai_tutor_user_progress_summary').select(
                'user_id, overall_progress_percentage'
            )
        
        if stage_id:
            at_risk_query = at_risk_query.eq('current_stage', stage_id)
        
        at_risk_result = at_risk_query.execute()
        
        for record in at_risk_result.data:
            user_id = record['user_id']
            completion_percentage = record.get('overall_progress_percentage', 0)
            if completion_percentage < 50:
                student_name = await _get_student_name(user_id)
                at_risk_students.append({
                    'user_id': user_id,
                    'student_name': student_name,
                    'completion_percentage': completion_percentage
                })
        
        metrics_data = {
            "total_students": total_students,
            "avg_completion_percentage": avg_completion,
            "avg_score": avg_score,
            "students_at_risk": at_risk_students,
            "time_range": time_range
        }
        
        print(f"📊 [TEACHER] Progress metrics calculated:")
        print(f"   - Total Students: {total_students}")
        print(f"   - Avg Completion: {avg_completion}%")
        print(f"   - Avg Score: {avg_score}%")
        print(f"   - Students at Risk: {len(at_risk_students)}")
        print(f"   - Time Range: {time_range}")
        
        return metrics_data
        
    except Exception as e:
        print(f"❌ [TEACHER] Error in _get_progress_metrics: {str(e)}")
        logger.error(f"Error in _get_progress_metrics: {str(e)}")
        raise

def _get_available_stages() -> List[Dict[str, Any]]:
    """
    Get all available stages for filtering in the Progress tab.
    This is a placeholder and would ideally fetch from a stages table.
    """
    return [
        {"id": 1, "name": "All Stages"},
        {"id": 2, "name": "Stage 2"},
        {"id": 3, "name": "Stage 3"},
        {"id": 4, "name": "Stage 4"},
        {"id": 5, "name": "Stage 5"},
        {"id": 6, "name": "Stage 6"}
    ]

def _get_lessons_by_stage(stage_id: int) -> List[Dict[str, Any]]:
    """
    Get lessons available for a specific stage.
    This is a placeholder and would ideally fetch from a lessons table.
    """
    if stage_id == 1:
        return [
            {"id": 1, "name": "Daily Routine Conversations", "stage": "Stage 1"},
            {"id": 2, "name": "Basic Conversation Starters", "stage": "Stage 1"},
            {"id": 3, "name": "Quick Response Practice", "stage": "Stage 1"}
        ]
    elif stage_id == 2:
        return [
            {"id": 1, "name": "Roleplay Simulation", "stage": "Stage 2"},
            {"id": 2, "name": "Storytelling", "stage": "Stage 2"},
            {"id": 3, "name": "Group Dialogue", "stage": "Stage 2"}
        ]
    elif stage_id == 3:
        return [
            {"id": 1, "name": "Problem Solving", "stage": "Stage 3"},
            {"id": 2, "name": "Critical Thinking Dialogues", "stage": "Stage 3"},
            {"id": 3, "name": "Academic Presentations", "stage": "Stage 3"}
        ]
    elif stage_id == 4:
        return [
            {"id": 1, "name": "Abstract Topic Discussion", "stage": "Stage 4"},
            {"id": 2, "name": "Job Interview Practice", "stage": "Stage 4"},
            {"id": 3, "name": "News Summary", "stage": "Stage 4"}
        ]
    elif stage_id == 5:
        return [
            {"id": 1, "name": "In-depth Interview", "stage": "Stage 5"},
            {"id": 2, "name": "Academic Presentation", "stage": "Stage 5"},
            {"id": 3, "name": "Critical Opinion Builder", "stage": "Stage 5"}
        ]
    elif stage_id == 6:
        return [
            {"id": 1, "name": "Spontaneous Speech", "stage": "Stage 6"},
            {"id": 2, "name": "Sensitive Scenario", "stage": "Stage 6"},
            {"id": 3, "name": "Advanced Roleplay", "stage": "Stage 6"}
        ]
    else:
        return []

async def _export_progress_data(format_type: str, search_query: Optional[str], stage_id: Optional[int], lesson_id: Optional[int], time_range: str) -> Dict[str, Any]:
    """
    Export real progress data in CSV or PDF format
    """
    print(f"🔄 [TEACHER] Exporting progress data in {format_type.upper()} format...")
    
    try:
        # Fetch real student progress data using the existing helper function
        progress_data = await _get_student_progress_overview(
            search_query=search_query,
            stage_id=stage_id,
            lesson_id=lesson_id,
            time_range=time_range
        )
        
        # Format data for export
        data_to_export = []
        for student in progress_data.get('students', []):
            export_record = {
                "user_id": student['user_id'],
                "student_name": student['student_name'],
                "email": student['email'],
                "current_stage": student['current_stage'],
                "current_lesson": student['current_lesson'],
                "avg_score": student['avg_score'],
                "progress_percentage": student['progress_percentage'],
                "ai_feedback": student['ai_feedback'],
                "feedback_sentiment": student['feedback_sentiment'],
                "last_active": student['last_active'],
                "is_at_risk": student['is_at_risk'],
                "total_time_minutes": student['total_time_minutes'],
                "exercises_completed": student['exercises_completed']
            }
            data_to_export.append(export_record)
        
        print(f"   - Exporting {len(data_to_export)} real student records")
        print(f"   - Search Query: {search_query}")
        print(f"   - Stage Filter: {stage_id}")
        print(f"   - Lesson Filter: {lesson_id}")
        print(f"   - Time Range: {time_range}")
        
        if format_type == "csv":
            # In a real app, you'd use a library like pandas or a CSV generation library
            # For demonstration, we'll just return the data as a dict
            return {"data": data_to_export, "format": "csv"}
        elif format_type == "pdf":
            # In a real app, you'd use a PDF generation library like ReportLab or FPDF
            # For demonstration, we'll just return the data as a dict
            return {"data": data_to_export, "format": "pdf"}
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported format: {format_type}")
            
    except Exception as e:
        print(f"❌ [TEACHER] Error in _export_progress_data: {str(e)}")
        logger.error(f"Error in _export_progress_data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error exporting progress data: {str(e)}")

def _get_current_lesson_name(stage_id: int) -> str:
    """Get lesson name based on stage ID"""
    lesson_mapping = {
        1: "Daily Routine Conversations",
        2: "Roleplay Simulation", 
        3: "Problem Solving",
        4: "Abstract Topic Discussion",
        5: "In-depth Interview",
        6: "Spontaneous Speech"
    }
    return lesson_mapping.get(stage_id, f"Stage {stage_id} Lesson")

def _get_stage_display_name(stage_id: int) -> str:
    """Get stage display name for UI"""
    stage_names = {
        1: "Stage 1",
        2: "Stage 2", 
        3: "Stage 3",
        4: "Stage 4",
        5: "Stage 5",
        6: "Stage 6"
    }
    return stage_names.get(stage_id, f"Stage {stage_id}")

async def _get_student_name(user_id: str) -> str:
    """
    Get real student name from profiles table
    Uses first_name + last_name as display name
    """
    try:
        # Get the real student name from profiles table
        try:
            profile_result = supabase.table('profiles').select(
                'first_name, last_name, email'
            ).eq('id', user_id).execute()
            
            if profile_result.data and len(profile_result.data) > 0:
                profile = profile_result.data[0]
                
                # Priority: first_name + last_name > first_name only > last_name only > email
                if profile.get('first_name') and profile.get('last_name') and profile['first_name'].strip() and profile['last_name'].strip():
                    full_name = f"{profile['first_name']} {profile['last_name']}"
                    print(f"✅ [TEACHER] Found full name for {user_id}: {full_name}")
                    return full_name
                elif profile.get('first_name') and profile['first_name'].strip():
                    print(f"✅ [TEACHER] Found first name for {user_id}: {profile['first_name']}")
                    return profile['first_name']
                elif profile.get('last_name') and profile['last_name'].strip():
                    print(f"✅ [TEACHER] Found last name for {user_id}: {profile['last_name']}")
                    return profile['last_name']
                elif profile.get('email') and profile['email'].strip():
                    print(f"⚠️ [TEACHER] Using email as name for {user_id}: {profile['email']}")
                    return profile['email']
            
        except Exception as profile_error:
            print(f"❌ [TEACHER] Profiles table error for {user_id}: {str(profile_error)}")
        
        # Fallback to meaningful display name from progress data
        fallback_name = await _create_fallback_student_name(user_id)
        print(f"⚠️ [TEACHER] Using fallback name for {user_id}: {fallback_name}")
        return fallback_name
            
    except Exception as e:
        print(f"❌ [TEACHER] Error getting student name for {user_id}: {str(e)}")
        return f"Student {user_id[:8]}..."

async def _create_fallback_student_name(user_id: str) -> str:
    """
    Create a fallback student name when profiles table is not available
    """
    try:
        # Get user progress data to create a meaningful display name
        progress_result = supabase.table('ai_tutor_user_progress_summary').select(
            'current_stage, current_exercise, overall_progress_percentage, last_activity_date'
        ).eq('user_id', user_id).execute()
        
        if progress_result.data and len(progress_result.data) > 0:
            user_data = progress_result.data[0]
            stage = user_data.get('current_stage', 1)
            progress = user_data.get('overall_progress_percentage', 0)
            
            # Create a descriptive name
            short_id = user_id[:6]
            stage_name = _get_stage_name(stage)
            
            if progress > 0:
                return f"Student {short_id} ({stage_name}, {progress:.0f}%)"
            else:
                return f"Student {short_id} ({stage_name})"
        else:
            # No progress data, use basic format
            short_id = user_id[:6]
            return f"Student {short_id}"
            
    except Exception as e:
        print(f"⚠️ [TEACHER] Error creating fallback name for {user_id}: {str(e)}")
        return f"Student {user_id[:8]}..."

def _get_stage_name(stage_id: int) -> str:
    """Get human-readable stage name"""
    stage_names = {
        1: "Beginner",
        2: "Elementary", 
        3: "Intermediate",
        4: "Upper-Intermediate",
        5: "Advanced",
        6: "Expert"
    }
    return stage_names.get(stage_id, f"Stage {stage_id}")

@router.get("/health")
async def teacher_health_check():
    """
    Health check endpoint for teacher routes
    """
    return {"status": "healthy", "service": "teacher_dashboard"}

@router.get("/dashboard/student/{user_id}", response_model=StudentDetailsResponse)
async def get_student_details(
    user_id: str,
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher)
):
    """
    Get comprehensive details of a particular student by user_id
    This API fetches all available data for the student from various tables
    """
    print(f"🔄 [TEACHER] GET /teacher/dashboard/student/{user_id} called")
    print(f"👤 [TEACHER] Authenticated user: {current_user['email']} (Role: {current_user.get('role', 'unknown')})")
    print(f"🎯 [TEACHER] Requesting details for student: {user_id}")
    
    try:
        # Validate UUID format
        if not _is_valid_uuid(user_id):
            raise HTTPException(status_code=400, detail="Invalid user_id format. Must be a valid UUID.")
        
        # Get comprehensive student details
        student_details = await _get_comprehensive_student_details(user_id)
        
        if not student_details:
            raise HTTPException(status_code=404, detail=f"Student with user_id {user_id} not found")
        
        return StudentDetailsResponse(
            success=True,
            data=student_details,
            message=f"Student details retrieved successfully for {student_details.get('basic_info', {}).get('student_name', 'Unknown')}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [TEACHER] Error in get_student_details: {str(e)}")
        logger.error(f"Error in get_student_details: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Helper functions for student details
async def _get_comprehensive_student_details(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Get comprehensive student details from all available tables
    """
    try:
        print(f"🔍 [TEACHER] Fetching comprehensive details for student: {user_id}")
        
        # 1. Basic student information
        basic_info = await _get_student_basic_info(user_id)
        if not basic_info:
            print(f"❌ [TEACHER] No basic info found for student: {user_id}")
            return None
        
        # 2. Progress overview
        progress_overview = await _get_student_progress_overview(user_id)
        
        # 3. Stage progress for all stages
        stage_progress = await _get_student_stage_progress(user_id)
        
        # 4. Exercise progress for all stages
        exercise_progress = await _get_student_exercise_progress(user_id)
        
        # 5. Learning milestones
        learning_milestones = await _get_student_learning_milestones(user_id)
        
        # 6. Weekly progress summaries (last 4 weeks)
        weekly_progress = await _get_student_weekly_progress(user_id)
        
        # 7. Daily analytics (last 7 days)
        daily_analytics = await _get_student_daily_analytics(user_id)
        
        # 8. Learning unlocks
        learning_unlocks = await _get_student_learning_unlocks(user_id)
        
        # 9. Topic progress details
        topic_progress = await _get_student_topic_progress(user_id)
        
        # 10. Performance insights
        performance_insights = await _get_student_performance_insights(user_id)
        
        comprehensive_data = {
            "basic_info": basic_info,
            "progress_overview": progress_overview,
            "stage_progress": stage_progress,
            "exercise_progress": exercise_progress,
            "learning_milestones": learning_milestones,
            "weekly_progress": weekly_progress,
            "daily_analytics": daily_analytics,
            "learning_unlocks": learning_unlocks,
            "topic_progress": topic_progress,
            "performance_insights": performance_insights,
            "last_updated": datetime.now().isoformat()
        }
        
        print(f"✅ [TEACHER] Comprehensive details compiled for student: {user_id}")
        return comprehensive_data
        
    except Exception as e:
        print(f"❌ [TEACHER] Error getting comprehensive student details: {str(e)}")
        raise

async def _get_student_basic_info(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Get basic student information from profiles table and progress summary
    """
    try:
        # Try to get from user_profiles table first
        try:
            profile_result = supabase.table('profiles').select(
                'id, display_name, first_name, last_name, email, phone, role'
            ).eq('id', user_id).execute()
            
            if profile_result.data and len(profile_result.data) > 0:
                profile = profile_result.data[0]
                
                # Get progress data for activity dates
                progress_result = supabase.table('ai_tutor_user_progress_summary').select(
                    'first_activity_date, last_activity_date'
                ).eq('user_id', user_id).execute()
                
                progress_data = progress_result.data[0] if progress_result.data else {}
                
                # Create display name
                if profile.get('display_name') and profile['display_name'].strip():
                    student_name = profile['display_name']
                elif profile.get('first_name') and profile.get('last_name') and profile['first_name'].strip() and profile['last_name'].strip():
                    student_name = f"{profile['first_name']} {profile['last_name']}"
                elif profile.get('first_name') and profile['first_name'].strip():
                    student_name = profile['first_name']
                elif profile.get('last_name') and profile['last_name'].strip():
                    student_name = profile['last_name']
                else:
                    student_name = profile.get('email', f"Student {user_id[:8]}...")

                # Handle date formatting safely
                first_activity = progress_data.get('first_activity_date')
                last_activity = progress_data.get('last_activity_date')
                
                # Convert to string if it's a date object, otherwise use as is
                first_activity_str = first_activity.isoformat() if hasattr(first_activity, 'isoformat') else str(first_activity) if first_activity else date.today().isoformat()
                last_activity_str = last_activity.isoformat() if hasattr(last_activity, 'isoformat') else str(last_activity) if last_activity else date.today().isoformat()
                
                return {
                    "user_id": user_id,
                    "student_name": student_name,
                    "email": profile.get('email', ''),
                    "phone": profile.get('phone'),
                    "role": profile.get('role', 'student'),
                    "first_activity_date": first_activity_str,
                    "last_activity_date": last_activity_str
                }
                
        except Exception as profile_error:
            print(f"⚠️ [TEACHER] Profiles table error for {user_id}: {str(profile_error)}")
        
        # Fallback: get from progress summary only
        progress_result = supabase.table('ai_tutor_user_progress_summary').select(
            'user_id, first_activity_date, last_activity_date'
        ).eq('user_id', user_id).execute()
        
        if progress_result.data and len(progress_result.data) > 0:
            progress_data = progress_result.data[0]
            
            # Create fallback name
            fallback_name = await _create_fallback_student_name(user_id)

            # Handle date formatting safely for fallback
            first_activity = progress_data.get('first_activity_date')
            last_activity = progress_data.get('last_activity_date')
            
            first_activity_str = first_activity.isoformat() if hasattr(first_activity, 'isoformat') else str(first_activity) if first_activity else date.today().isoformat()
            last_activity_str = last_activity.isoformat() if hasattr(last_activity, 'isoformat') else str(last_activity) if last_activity else date.today().isoformat()

            
            return {
                "user_id": user_id,
                "student_name": fallback_name,
                "email": f"student_{user_id[:8]}@example.com",  # Placeholder
                "phone": None,
                "role": "student",
                "first_activity_date": first_activity_str,
                "last_activity_date": last_activity_str
            }
        
        return None
        
    except Exception as e:
        print(f"❌ [TEACHER] Error getting student basic info: {str(e)}")
        return None

async def _get_student_progress_overview(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Get student progress overview from ai_tutor_user_progress_summary
    """
    try:
        result = supabase.table('ai_tutor_user_progress_summary').select('*').eq('user_id', user_id).execute()
        
        if result.data and len(result.data) > 0:
            data = result.data[0]
            return {
                "current_stage": data.get('current_stage', 1),
                "current_exercise": data.get('current_exercise', 1),
                "overall_progress_percentage": float(data.get('overall_progress_percentage', 0)),
                "total_time_spent_minutes": data.get('total_time_spent_minutes', 0),
                "total_exercises_completed": data.get('total_exercises_completed', 0),
                "streak_days": data.get('streak_days', 0),
                "longest_streak": data.get('longest_streak', 0),
                "average_session_duration_minutes": float(data.get('average_session_duration_minutes', 0)),
                "weekly_learning_hours": float(data.get('weekly_learning_hours', 0)),
                "monthly_learning_hours": float(data.get('monthly_learning_hours', 0))
            }
        
        return None
        
    except Exception as e:
        print(f"❌ [TEACHER] Error getting student progress overview: {str(e)}")
        return None

async def _get_student_stage_progress(user_id: str) -> List[Dict[str, Any]]:
    """
    Get student progress for all stages
    """
    try:
        result = supabase.table('ai_tutor_user_stage_progress').select('*').eq('user_id', user_id).order('stage_id').execute()
        
        stage_progress = []
        for data in result.data:
            stage_progress.append({
                "stage_id": data.get('stage_id', 1),
                "stage_name": _get_stage_name(data.get('stage_id', 1)),
                "completed": data.get('completed', False),
                "mature": data.get('mature', False),
                "average_score": float(data.get('average_score', 0)),
                "progress_percentage": float(data.get('progress_percentage', 0)),
                "total_score": float(data.get('total_score', 0)),
                "best_score": float(data.get('best_score', 0)),
                "time_spent_minutes": data.get('time_spent_minutes', 0),
                "attempts_count": data.get('attempts_count', 0),
                "exercises_completed": data.get('exercises_completed', 0),
                "started_at": data.get('started_at'),
                "completed_at": data.get('completed_at'),
                "last_attempt_at": data.get('last_attempt_at')
            })
        
        return stage_progress
        
    except Exception as e:
        print(f"❌ [TEACHER] Error getting student stage progress: {str(e)}")
        return []

async def _get_student_exercise_progress(user_id: str) -> List[Dict[str, Any]]:
    """
    Get student progress for all exercises
    """
    try:
        result = supabase.table('ai_tutor_user_exercise_progress').select('*').eq('user_id', user_id).order('stage_id, exercise_id').execute()
        
        exercise_progress = []
        for data in result.data:
            exercise_progress.append({
                "stage_id": data.get('stage_id', 1),
                "exercise_id": data.get('exercise_id', 1),
                "exercise_name": _get_exercise_name(data.get('stage_id', 1), data.get('exercise_id', 1)),
                "attempts": data.get('attempts', 0),
                "average_score": float(data.get('average_score', 0)),
                "best_score": float(data.get('best_score', 0)),
                "total_score": float(data.get('total_score', 0)),
                "time_spent_minutes": data.get('time_spent_minutes', 0),
                "mature": data.get('mature', False),
                "started_at": data.get('started_at'),
                "completed_at": data.get('completed_at'),
                "last_attempt_at": data.get('last_attempt_at')
            })
        
        return exercise_progress
        
    except Exception as e:
        print(f"❌ [TEACHER] Error getting student exercise progress: {str(e)}")
        return []

async def _get_student_learning_milestones(user_id: str) -> List[Dict[str, Any]]:
    """
    Get student learning milestones
    """
    try:
        result = supabase.table('ai_tutor_learning_milestones').select('*').eq('user_id', user_id).order('earned_at', desc=True).execute()
        
        milestones = []
        for data in result.data:
            milestones.append({
                "milestone_type": data.get('milestone_type', ''),
                "milestone_title": data.get('milestone_title', ''),
                "milestone_description": data.get('milestone_description', ''),
                "milestone_value": data.get('milestone_value'),
                "earned_at": data.get('earned_at'),
                "is_notified": data.get('is_notified', False)
            })
        
        return milestones
        
    except Exception as e:
        print(f"❌ [TEACHER] Error getting student learning milestones: {str(e)}")
        return []

async def _get_student_weekly_progress(user_id: str) -> List[Dict[str, Any]]:
    """
    Get student weekly progress summaries (last 4 weeks)
    """
    try:
        result = supabase.table('ai_tutor_weekly_progress_summaries').select('*').eq('user_id', user_id).order('week_start_date', desc=True).limit(4).execute()
        
        weekly_progress = []
        for data in result.data:
            weekly_progress.append({
                "week_start_date": data.get('week_start_date'),
                "total_sessions": data.get('total_sessions', 0),
                "total_time_hours": float(data.get('total_time_hours', 0)),
                "average_daily_time_minutes": float(data.get('average_daily_time_minutes', 0)),
                "average_score": float(data.get('average_score', 0)),
                "score_improvement": float(data.get('score_improvement', 0)),
                "consistency_score": float(data.get('consistency_score', 0)),
                "stages_completed": data.get('stages_completed', 0),
                "exercises_mastered": data.get('exercises_mastered', 0),
                "milestones_earned": data.get('milestones_earned', 0),
                "weekly_recommendations": data.get('weekly_recommendations', [])
            })
        
        return weekly_progress
        
    except Exception as e:
        print(f"❌ [TEACHER] Error getting student weekly progress: {str(e)}")
        return []

async def _get_student_daily_analytics(user_id: str) -> List[Dict[str, Any]]:
    """
    Get student daily analytics (last 7 days)
    """
    try:
        # Get last 7 days
        end_date = date.today()
        start_date = end_date - timedelta(days=6)
        
        result = supabase.table('ai_tutor_daily_learning_analytics').select('*').eq('user_id', user_id).gte('analytics_date', start_date.isoformat()).lte('analytics_date', end_date.isoformat()).order('analytics_date', desc=True).execute()
        
        daily_analytics = []
        for data in result.data:
            daily_analytics.append({
                "analytics_date": data.get('analytics_date'),
                "sessions_count": data.get('sessions_count', 0),
                "total_time_minutes": data.get('total_time_minutes', 0),
                "average_session_duration": float(data.get('average_session_duration', 0)),
                "average_score": float(data.get('average_score', 0)),
                "best_score": float(data.get('best_score', 0)),
                "exercises_attempted": data.get('exercises_attempted', 0),
                "exercises_completed": data.get('exercises_completed', 0)
            })
        
        return daily_analytics
        
    except Exception as e:
        print(f"❌ [TEACHER] Error getting student daily analytics: {str(e)}")
        return []

async def _get_student_learning_unlocks(user_id: str) -> List[Dict[str, Any]]:
    """
    Get student learning unlocks
    """
    try:
        result = supabase.table('ai_tutor_learning_unlocks').select('*').eq('user_id', user_id).order('stage_id, exercise_id').execute()
        
        unlocks = []
        for data in result.data:
            unlocks.append({
                "stage_id": data.get('stage_id', 1),
                "exercise_id": data.get('exercise_id'),
                "is_unlocked": data.get('is_unlocked', False),
                "unlock_criteria_met": data.get('unlock_criteria_met', False),
                "unlocked_at": data.get('unlocked_at'),
                "unlocked_by_criteria": data.get('unlocked_by_criteria'),
                "created_at": data.get('created_at')
            })
        
        return unlocks
        
    except Exception as e:
        print(f"❌ [TEACHER] Error getting student learning unlocks: {str(e)}")
        return []

async def _get_student_topic_progress(user_id: str) -> List[Dict[str, Any]]:
    """
    Get student topic progress details
    """
    try:
        result = supabase.table('ai_tutor_user_topic_progress').select('*').eq('user_id', user_id).order('stage_id, exercise_id, topic_id, attempt_num').execute()
        
        topic_progress = []
        for data in result.data:
            topic_progress.append({
                "stage_id": data.get('stage_id', 1),
                "exercise_id": data.get('exercise_id', 1),
                "topic_id": data.get('topic_id', 1),
                "attempt_num": data.get('attempt_num', 1),
                "score": float(data.get('score', 0)) if data.get('score') else None,
                "urdu_used": data.get('urdu_used', False),
                "completed": data.get('completed', False),
                "started_at": data.get('started_at'),
                "completed_at": data.get('completed_at'),
                "total_time_seconds": data.get('total_time_seconds', 0),
                "created_at": data.get('created_at')
            })
        
        return topic_progress
        
    except Exception as e:
        print(f"❌ [TEACHER] Error getting student topic progress: {str(e)}")
        return []

async def _get_student_performance_insights(user_id: str) -> Dict[str, Any]:
    """
    Get performance insights and analytics for the student
    """
    try:
        # Get overall performance metrics
        progress_result = supabase.table('ai_tutor_user_progress_summary').select('*').eq('user_id', user_id).execute()
        
        if not progress_result.data:
            return {}
        
        progress_data = progress_result.data[0]
        
        # Calculate performance insights
        current_stage = progress_data.get('current_stage', 1)
        overall_progress = float(progress_data.get('overall_progress_percentage', 0))
        total_time = progress_data.get('total_time_spent_minutes', 0)
        streak = progress_data.get('streak_days', 0)
        
        # Performance level assessment
        if overall_progress >= 80:
            performance_level = "Excellent"
        elif overall_progress >= 60:
            performance_level = "Good"
        elif overall_progress >= 40:
            performance_level = "Average"
        elif overall_progress >= 20:
            performance_level = "Below Average"
        else:
            performance_level = "Needs Improvement"
        
        # Learning pace assessment
        if total_time > 0:
            progress_per_minute = overall_progress / total_time
            if progress_per_minute > 0.5:
                learning_pace = "Fast Learner"
            elif progress_per_minute > 0.2:
                learning_pace = "Steady Progress"
            else:
                learning_pace = "Slow but Steady"
        else:
            learning_pace = "New Learner"
        
        # Consistency assessment
        if streak >= 7:
            consistency = "Highly Consistent"
        elif streak >= 3:
            consistency = "Moderately Consistent"
        elif streak >= 1:
            consistency = "Occasionally Active"
        else:
            consistency = "Inactive"
        
        # Recommendations based on performance
        recommendations = []
        if overall_progress < 50:
            recommendations.append("Focus on completing current stage exercises")
            recommendations.append("Practice more with current topics")
        if streak < 3:
            recommendations.append("Try to maintain daily learning routine")
        if current_stage < 3:
            recommendations.append("Build strong foundation in early stages")
        
        return {
            "performance_level": performance_level,
            "learning_pace": learning_pace,
            "consistency": consistency,
            "current_stage_name": _get_stage_name(current_stage),
            "progress_efficiency": round(progress_per_minute, 3) if total_time > 0 else 0,
            "recommendations": recommendations,
            "strength_areas": _identify_strength_areas(user_id),
            "improvement_areas": _identify_improvement_areas(user_id)
        }
        
    except Exception as e:
        print(f"❌ [TEACHER] Error getting student performance insights: {str(e)}")
        return {}

def _identify_strength_areas(user_id: str) -> List[str]:
    """
    Identify student's strength areas based on performance data
    """
    try:
        # This would require more complex analysis of exercise scores
        # For now, return basic strengths
        return ["Consistent Learning", "Regular Practice"]
    except Exception as e:
        print(f"⚠️ [TEACHER] Error identifying strength areas: {str(e)}")
        return []

def _identify_improvement_areas(user_id: str) -> List[str]:
    """
    Identify areas where student needs improvement
    """
    try:
        # This would require more complex analysis of exercise scores
        # For now, return basic improvement areas
        return ["Score Consistency", "Time Management"]
    except Exception as e:
        print(f"⚠️ [TEACHER] Error identifying improvement areas: {str(e)}")
        return []

def _get_exercise_name(stage_id: int, exercise_id: int) -> str:
    """
    Get human-readable exercise name
    """
    exercise_names = {
        1: {
            1: "Daily Routine Conversations",
            2: "Quick Response Practice",
            3: "Repeat After Me"
        },
        2: {
            1: "Daily Routine Conversations",
            2: "Quick Answer Practice",
            3: "Roleplay Simulation"
        },
        3: {
            1: "Group Dialogue",
            2: "Problem Solving",
            3: "Storytelling"
        },
        4: {
            1: "Abstract Topic Discussion",
            2: "Mock Interview",
            3: "News Summary"
        },
        5: {
            1: "Academic Presentation",
            2: "Critical Thinking Dialogues",
            3: "In-Depth Interview"
        },
        6: {
            1: "AI-Guided Spontaneous Speech",
            2: "Critical Opinion Builder",
            3: "Roleplay Handle Sensitive Scenario"
        }
    }
    
    return exercise_names.get(stage_id, {}).get(exercise_id, f"Exercise {exercise_id}")

def _is_valid_uuid(uuid_string: str) -> bool:
    """
    Validate if the string is a valid UUID
    """
    try:
        import uuid
        uuid.UUID(uuid_string)
        return True
    except ValueError:
        return False
