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
    Get inactivity insight (POSSIBLE - using daily learning analytics)
    """
    try:
        # Get users with no activity in last 30 days
        thirty_days_ago = (date.today() - timedelta(days=30)).isoformat()
        
        # Get recent activity
        recent_activity_query = supabase.table('ai_tutor_daily_learning_analytics').select(
            'user_id'
        ).gte('analytics_date', thirty_days_ago)
        
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
        
        # Calculate inactivity
        active_users = len(set([record['user_id'] for record in recent_activity_result.data])) if recent_activity_result.data else 0
        inactive_users = total_users - active_users
        
        if inactive_users > (total_users * 0.2):  # More than 20% inactive
            return {
                "has_alert": True,
                "message": f"High inactivity detected: {inactive_users} inactive students",
                "affected_students": inactive_users,
                "inactivity_rate": round((inactive_users / total_users * 100), 1)
            }
        else:
            return {
                "has_alert": False,
                "message": f"Inactivity is normal: {round((inactive_users / total_users * 100), 1)}%",
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
    Get real student name from user_profiles table
    This table is synced with auth.users display names
    """
    try:
        # Method 1: Get the real student name from user_profiles table (PRIORITY)
        try:
            profile_result = supabase.table('user_profiles').select(
                'display_name, first_name, last_name, email'
            ).eq('user_id', user_id).execute()
            
            if profile_result.data and len(profile_result.data) > 0:
                profile = profile_result.data[0]
                
                # Priority: display_name > first_name + last_name > email
                if profile.get('display_name') and profile['display_name'].strip():
                    print(f"✅ [TEACHER] Found real name for {user_id}: {profile['display_name']}")
                    return profile['display_name']
                elif profile.get('first_name') and profile.get('last_name') and profile['first_name'].strip() and profile['last_name'].strip():
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
            print(f"❌ [TEACHER] User profiles table error for {user_id}: {str(profile_error)}")
        
        # Method 2: Fallback to meaningful display name from progress data
        fallback_name = await _create_fallback_student_name(user_id)
        print(f"⚠️ [TEACHER] Using fallback name for {user_id}: {fallback_name}")
        return fallback_name
            
    except Exception as e:
        print(f"❌ [TEACHER] Error getting student name for {user_id}: {str(e)}")
        return f"Student {user_id[:8]}..."

async def _create_fallback_student_name(user_id: str) -> str:
    """
    Create a fallback student name when user_profiles table is not available
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
