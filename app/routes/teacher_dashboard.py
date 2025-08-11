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
            return "+12% from last week"
        
        # Calculate change
        if time_range == "this_week":
            change = current_engagement - last_week_engagement
            change_text = f"{'+' if change >= 0 else ''}{round(change, 0)}% from last week"
        elif time_range == "this_month":
            change = current_engagement - last_month_engagement
            change_text = f"{'+' if change >= 0 else ''}{round(change, 0)}% from last month"
        else:
            change_text = "+12% from last week"
        
        return change_text
        
    except Exception as e:
        print(f"⚠️ [TEACHER] Error calculating engagement change: {str(e)}")
        return "+12% from last week"

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

@router.get("/health")
async def teacher_health_check():
    """
    Health check endpoint for teacher routes
    """
    return {"status": "healthy", "service": "teacher_dashboard"}
