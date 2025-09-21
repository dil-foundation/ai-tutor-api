import os
import asyncio
from datetime import date, datetime, timedelta
from supabase import create_client, Client
from dotenv import load_dotenv
import logging
from typing import Dict, List, Optional, Tuple

# Load environment variables
load_dotenv(override=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables
supabase: Optional[Client] = None
SUPABASE_AVAILABLE = False

def initialize_supabase():
    """Initialize Supabase connection with proper error handling"""
    global supabase, SUPABASE_AVAILABLE
    
    try:
        print("🔧 [SUPABASE] Initializing Supabase connection...")
        logger.info("🔧 [SUPABASE] Initializing Supabase connection...")
        
        # Supabase configuration
        SUPABASE_URL = os.getenv("SUPABASE_URL")
        SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
        
        print(f"🔧 [SUPABASE] URL: {SUPABASE_URL}")
        logger.info(f"🔧 [SUPABASE] URL: {SUPABASE_URL}")
        
        if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
            print("❌ [SUPABASE] Missing Supabase environment variables")
            logger.error("❌ [SUPABASE] Missing Supabase environment variables")
            SUPABASE_AVAILABLE = False
            return False
        
        # Create Supabase client
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        
        # Test connection with a simple query
        try:
            # Try to access a table to verify connection
            test_response = supabase.from_("ai_tutor_settings").select("count", count="exact").limit(0).execute()
            print("✅ [SUPABASE] Successfully connected to Supabase")
            logger.info("✅ [SUPABASE] Successfully connected to Supabase")
            SUPABASE_AVAILABLE = True
            return True
        except Exception as test_error:
            print(f"⚠️ [SUPABASE] Connection created but test query failed: {test_error}")
            logger.warning(f"⚠️ [SUPABASE] Connection created but test query failed: {test_error}")
            # Still consider it available since client was created
            SUPABASE_AVAILABLE = True
            return True
            
    except Exception as e:
        print(f"❌ [SUPABASE] Failed to initialize Supabase: {e}")
        logger.error(f"❌ [SUPABASE] Failed to initialize Supabase: {e}")
        SUPABASE_AVAILABLE = False
        return False

def get_supabase_client():
    """Get Supabase client with availability check"""
    if not SUPABASE_AVAILABLE:
        logger.warning("⚠️ [SUPABASE] Supabase not available")
        return None
    return supabase

def is_supabase_available():
    """Check if Supabase is available"""
    return SUPABASE_AVAILABLE

# Initialize Supabase connection (non-blocking)
initialize_supabase()

class SupabaseProgressTracker:
    """Professional progress tracking service for AI Tutor app"""
    
    def __init__(self):
        self.client = supabase
        print("🔧 [SUPABASE] Progress Tracker initialized")
        print(f"🔧 [SUPABASE] Connected to: {SUPABASE_URL}")
        logger.info("Supabase Progress Tracker initialized")
    
    async def _calculate_streak(self, user_id: str, current_date: date) -> Tuple[int, int]:
        """
        Calculate current streak and longest streak for a user
        Returns: (current_streak, longest_streak)
        """
        try:
            print(f"🔄 [STREAK] Calculating streak for user: {user_id}")
            
            # Get daily analytics for the last 30 days to calculate streak
            thirty_days_ago = current_date - timedelta(days=30)
            
            daily_analytics = self.client.table('ai_tutor_daily_learning_analytics').select(
                'analytics_date, total_time_minutes, exercises_completed'
            ).eq('user_id', user_id).gte('analytics_date', thirty_days_ago.isoformat()).order('analytics_date', desc=False).execute()
            
            print(f"📊 [STREAK] Found {len(daily_analytics.data)} daily records")
            
            if not daily_analytics.data:
                print(f"ℹ️ [STREAK] No daily analytics found, returning 0 streak")
                return 0, 0
            
            # Create a set of active dates (where user had activity)
            active_dates = set()
            for record in daily_analytics.data:
                if record.get('total_time_minutes', 0) > 0 or record.get('exercises_completed', 0) > 0:
                    active_dates.add(record['analytics_date'])
            
            print(f"📊 [STREAK] Active dates: {sorted(active_dates)}")
            
            # Calculate current streak (consecutive days from today backwards)
            current_streak = 0
            check_date = current_date
            
            while check_date >= thirty_days_ago:
                date_str = check_date.isoformat()
                if date_str in active_dates:
                    current_streak += 1
                    check_date -= timedelta(days=1)
                else:
                    break
            
            print(f"📊 [STREAK] Current streak: {current_streak} days")
            
            # Calculate longest streak from historical data
            longest_streak = 0
            temp_streak = 0
            
            # Sort dates and check for consecutive sequences
            sorted_dates = sorted(active_dates)
            
            for i, date_str in enumerate(sorted_dates):
                current_date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                
                if i == 0:
                    temp_streak = 1
                else:
                    prev_date_obj = datetime.strptime(sorted_dates[i-1], '%Y-%m-%d').date()
                    if (current_date_obj - prev_date_obj).days == 1:
                        temp_streak += 1
                    else:
                        longest_streak = max(longest_streak, temp_streak)
                        temp_streak = 1
            
            # Check the last streak
            longest_streak = max(longest_streak, temp_streak)
            
            print(f"📊 [STREAK] Longest streak: {longest_streak} days")
            return current_streak, longest_streak
            
        except Exception as e:
            print(f"❌ [STREAK] Error calculating streak: {str(e)}")
            logger.error(f"Error calculating streak for user {user_id}: {str(e)}")
            return 0, 0
    
    async def _update_daily_analytics(self, user_id: str, time_spent_seconds: int, 
                                    score: float, urdu_used: bool, completed: bool) -> None:
        """
        Update daily learning analytics for the user
        """
        try:
            current_date_iso = date.today().isoformat()
            time_spent_minutes = int(time_spent_seconds / 60)
            
            print(f"🔄 [DAILY] Updating daily analytics for user: {user_id}, date: {current_date_iso}")
            
            # Get existing daily analytics for today
            existing = self.client.table('ai_tutor_daily_learning_analytics').select('*').eq('user_id', user_id).eq('analytics_date', current_date_iso).execute()
            
            if existing.data:
                # Update existing record
                current_record = existing.data[0]
                current_time = current_record.get('total_time_minutes', 0) + time_spent_minutes
                current_exercises = current_record.get('exercises_completed', 0) + (1 if completed else 0)
                
                # Calculate new average score
                current_avg = current_record.get('average_score', 0)
                current_count = current_record.get('exercises_completed', 0)
                new_count = current_count + 1
                new_avg = ((current_avg * current_count) + score) / new_count if new_count > 0 else score
                
                # Calculate Urdu usage percentage - REMOVED as column does not exist
                current_urdu_count = current_record.get('urdu_usage_count', 0) + (1 if urdu_used else 0)
                
                update_data = {
                    'total_time_minutes': current_time,
                    'exercises_completed': current_exercises,
                    'average_score': round(new_avg, 2),
                    'urdu_usage_count': current_urdu_count,
                    'updated_at': datetime.now().isoformat()
                }
                
                self.client.table('ai_tutor_daily_learning_analytics').update(update_data).eq('user_id', user_id).eq('analytics_date', current_date_iso).execute()
                print(f"✅ [DAILY] Updated existing daily analytics")
                
            else:
                # Create new record
                new_record = {
                    'user_id': user_id,
                    'analytics_date': current_date_iso,
                    'total_time_minutes': time_spent_minutes,
                    'exercises_completed': 1 if completed else 0,
                    'average_score': score,
                    'urdu_usage_count': 1 if urdu_used else 0,
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                }
                
                self.client.table('ai_tutor_daily_learning_analytics').insert(new_record).execute()
                print(f"✅ [DAILY] Created new daily analytics record")
                
        except Exception as e:
            print(f"❌ [DAILY] Error updating daily analytics: {str(e)}")
            logger.error(f"Error updating daily analytics for user {user_id}: {str(e)}")
    
    async def _calculate_session_metrics(self, user_id: str) -> Dict[str, float]:
        """
        Calculate session duration metrics
        Returns: average_session_duration, weekly_hours, monthly_hours
        """
        try:
            print(f"🔄 [SESSION] Calculating session metrics for user: {user_id}")
            
            # Get daily analytics for the last 30 days
            thirty_days_ago = date.today() - timedelta(days=30)
            daily_analytics = self.client.table('ai_tutor_daily_learning_analytics').select(
                'analytics_date, total_time_minutes, exercises_completed'
            ).eq('user_id', user_id).gte('analytics_date', thirty_days_ago.isoformat()).execute()
            
            if not daily_analytics.data:
                return {
                    'average_session_duration_minutes': 0.0,
                    'weekly_learning_hours': 0.0,
                    'monthly_learning_hours': 0.0
                }
            
            # Calculate average session duration
            total_days_with_activity = sum(1 for record in daily_analytics.data if record.get('total_time_minutes', 0) > 0)
            total_time_minutes = sum(record.get('total_time_minutes', 0) for record in daily_analytics.data)
            
            average_session_duration = total_time_minutes / total_days_with_activity if total_days_with_activity > 0 else 0.0
            
            # Calculate weekly hours (last 7 days)
            seven_days_ago = date.today() - timedelta(days=7)
            weekly_data = [r for r in daily_analytics.data if r['analytics_date'] >= seven_days_ago.isoformat()]
            weekly_hours = sum(r.get('total_time_minutes', 0) for r in weekly_data) / 60.0
            
            # Calculate monthly hours (last 30 days)
            monthly_hours = total_time_minutes / 60.0
            
            print(f"📊 [SESSION] Metrics calculated:")
            print(f"   - Average session: {average_session_duration:.2f} minutes")
            print(f"   - Weekly hours: {weekly_hours:.2f}")
            print(f"   - Monthly hours: {monthly_hours:.2f}")
            
            return {
                'average_session_duration_minutes': round(average_session_duration, 2),
                'weekly_learning_hours': round(weekly_hours, 2),
                'monthly_learning_hours': round(monthly_hours, 2)
            }
            
        except Exception as e:
            print(f"❌ [SESSION] Error calculating session metrics: {str(e)}")
            logger.error(f"Error calculating session metrics for user {user_id}: {str(e)}")
            return {
                'average_session_duration_minutes': 0.0,
                'weekly_learning_hours': 0.0,
                'monthly_learning_hours': 0.0
            }
    
    async def initialize_user_progress(self, user_id: str, assigned_start_stage: int = 1, english_proficiency_text: str = None) -> dict:
        """
        Initializes or updates a user's progress. This function is idempotent and can safely be
        called for new users or users with a default progress record.
        
        If an `assigned_start_stage` is provided, the user starts from that stage, 
        and all previous stages are marked as completed. Stage 0 is treated as Stage 1 for progress.
        """
        print(f"🔄 [INIT] Starting progress initialization for user: {user_id}")
        print(f"🚀 [INIT] Assigned Start Stage: {assigned_start_stage}")
        try:
            # Step 1: Prepare all the data needed for initialization
            current_date = date.today()
            current_timestamp = datetime.now().isoformat()
            
            # Treat stage 0 as stage 1 for progress setup, but store original assignment
            start_stage = assigned_start_stage if assigned_start_stage > 0 else 1
            
            completed_stages = list(range(1, start_stage))
            unlocked_stages = list(range(1, start_stage + 1))
            
            unlocked_exercises_map = {}
            for stage_id in completed_stages:
                unlocked_exercises_map[str(stage_id)] = [1, 2, 3]
            unlocked_exercises_map[str(start_stage)] = [1]

            # Step 2: Upsert the user progress summary
            progress_summary_payload = {
                "user_id": user_id,
                "current_stage": start_stage,
                "current_exercise": 1,
                "topic_id": 1,
                "unlocked_stages": unlocked_stages,
                "unlocked_exercises": unlocked_exercises_map,
                "overall_progress_percentage": (len(completed_stages) / 6) * 100,
                "total_exercises_completed": len(completed_stages) * 3,
                "english_proficiency_text": english_proficiency_text,
                "assigned_start_stage": assigned_start_stage,
                "last_activity_date": current_date.isoformat(),
                "updated_at": current_timestamp,
                "urdu_enabled": True, "total_time_spent_minutes": 0, "streak_days": 0,
                "longest_streak": 0, "average_session_duration_minutes": 0.00,
                "weekly_learning_hours": 0.00, "monthly_learning_hours": 0.00,
                "first_activity_date": current_date.isoformat(),
            }

            print(f"📝 [INIT] Upserting progress summary...")
            summary_result = self.client.table('ai_tutor_user_progress_summary').upsert(progress_summary_payload).execute()
            print(f"✅ [INIT] Progress summary upserted successfully.")

            # Step 3: Create missing stage progress records
            print("🔍 [INIT] Checking for existing stage progress records...")
            existing_stages_res = self.client.table('ai_tutor_user_stage_progress').select('stage_id').eq('user_id', user_id).execute()
            existing_stage_ids = {s['stage_id'] for s in existing_stages_res.data}
            
            stage_progress_to_create = []
            for stage_id in completed_stages:
                if stage_id not in existing_stage_ids:
                    stage_progress_to_create.append({
                        "user_id": user_id, "stage_id": stage_id, "started_at": current_timestamp,
                        "completed_at": current_timestamp, "completed": True,
                        "progress_percentage": 100.0, "exercises_completed": 3
                    })
            
            if start_stage not in existing_stage_ids:
                stage_progress_to_create.append({"user_id": user_id, "stage_id": start_stage, "started_at": current_timestamp})
            
            if stage_progress_to_create:
                print(f"📝 [INIT] Creating {len(stage_progress_to_create)} new stage progress records...")
                self.client.table('ai_tutor_user_stage_progress').insert(stage_progress_to_create).execute()
                print("✅ [INIT] Stage progress records created.")
            else:
                print("✅ [INIT] No new stage progress records needed.")

            # Step 4: Create missing learning unlock records
            print("🔍 [INIT] Checking for existing learning unlock records...")
            existing_unlocks_res = self.client.table('ai_tutor_learning_unlocks').select('stage_id, exercise_id').eq('user_id', user_id).execute()
            existing_unlocks = {(u['stage_id'], u['exercise_id']) for u in existing_unlocks_res.data}

            unlocks_to_create = []
            
            # Unlocks for all stages up to the starting one
            for stage_id in unlocked_stages:
                # Stage unlock record
                if (stage_id, None) not in existing_unlocks:
                    unlocks_to_create.append({"user_id": user_id, "stage_id": stage_id, "exercise_id": None, "is_unlocked": True, "unlock_criteria_met": True, "unlocked_at": current_timestamp, "unlocked_by_criteria": "Initial assignment"})
                
                # Exercise unlock records
                exercises_to_unlock = [1, 2, 3] if stage_id in completed_stages else [1]
                for ex_id in exercises_to_unlock:
                    if (stage_id, ex_id) not in existing_unlocks:
                        unlocks_to_create.append({"user_id": user_id, "stage_id": stage_id, "exercise_id": ex_id, "is_unlocked": True, "unlock_criteria_met": True, "unlocked_at": current_timestamp, "unlocked_by_criteria": "Initial assignment"})
                
                # Create locked records for the starting stage's other exercises
                if stage_id == start_stage:
                    for ex_id in [2, 3]:
                        if (stage_id, ex_id) not in existing_unlocks:
                             unlocks_to_create.append({"user_id": user_id, "stage_id": stage_id, "exercise_id": ex_id, "is_unlocked": False, "unlock_criteria_met": False})

            if unlocks_to_create:
                print(f"📝 [INIT] Creating {len(unlocks_to_create)} new learning unlock records...")
                self.client.table('ai_tutor_learning_unlocks').insert(unlocks_to_create).execute()
                print("✅ [INIT] Learning unlock records created.")
            else:
                print("✅ [INIT] No new learning unlock records needed.")

            print(f"🎉 [INIT] Successfully initialized progress for user: {user_id}")
            return {"success": True, "message": "User progress initialized successfully", "data": summary_result.data[0] if summary_result.data else None}
            
        except Exception as e:
            import traceback
            print(f"❌ [INIT] Error initializing user progress for {user_id}: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            logger.error(f"Error initializing user progress for {user_id}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def record_topic_attempt(self, user_id: str, stage_id: int, exercise_id: int, topic_id: int, 
                                 score: float, urdu_used: bool, time_spent_seconds: int, completed: bool) -> dict:
        """Record a topic attempt with detailed metrics"""
        print(f"🔄 [TOPIC] Recording topic attempt for user {user_id}")
        print(f"📊 [TOPIC] Details: stage={stage_id}, exercise={exercise_id}, topic={topic_id}")
        print(f"📊 [TOPIC] Metrics: score={score}, urdu_used={urdu_used}, time_spent={time_spent_seconds}s, completed={completed}")
        
        try:
            # Validate input parameters
            if not user_id or not user_id.strip():
                raise ValueError("User ID is required")
            
            if not (1 <= stage_id <= 6):
                raise ValueError(f"Invalid stage_id: {stage_id}. Must be between 1 and 6")
            
            if not (1 <= exercise_id <= 3):
                raise ValueError(f"Invalid exercise_id: {exercise_id}. Must be between 1 and 3")
            
            if not (1 <= topic_id <= 100):  # Reasonable topic range
                raise ValueError(f"Invalid topic_id: {topic_id}. Must be between 1 and 100")
            
            if not (0 <= score <= 100):
                raise ValueError(f"Invalid score: {score}. Must be between 0 and 100")
            
            if not (1 <= time_spent_seconds <= 3600):  # Max 1 hour per attempt
                print(f"⚠️ [TOPIC] Time spent {time_spent_seconds}s exceeds normal range, capping at 3600s")
                time_spent_seconds = min(time_spent_seconds, 3600)
            
            # Check if topic attempt already exists for this user and topic
            print(f"🔍 [TOPIC] Checking if topic attempt already exists for user {user_id}, topic {topic_id}...")
            existing_attempt = self.client.table('ai_tutor_user_topic_progress').select('*').eq('user_id', user_id).eq('stage_id', stage_id).eq('exercise_id', exercise_id).eq('topic_id', topic_id).execute()
            
            if existing_attempt.data:
                # Topic attempt exists - update the existing record
                existing_record = existing_attempt.data[0]
                current_attempt_num = existing_record.get('attempt_num', 1)
                new_attempt_num = current_attempt_num + 1
                
                print(f"📝 [TOPIC] Topic attempt exists. Current attempt: {current_attempt_num}, new attempt: {new_attempt_num}")
                print(f"📊 [TOPIC] Existing record: {existing_record}")
                
                # Prepare update data
                update_data = {
                    "attempt_num": new_attempt_num,
                    "score": score,
                    "urdu_used": urdu_used,
                    "completed": completed,
                    "total_time_seconds": time_spent_seconds
                }
                
                print(f"📝 [TOPIC] Updating existing topic progress record: {update_data}")
                result = self.client.table('ai_tutor_user_topic_progress').update(update_data).eq('user_id', user_id).eq('stage_id', stage_id).eq('exercise_id', exercise_id).eq('topic_id', topic_id).execute()
                print(f"✅ [TOPIC] Topic progress updated: {result.data[0] if result.data else 'No data'}")
                
            else:
                # Topic attempt doesn't exist - insert new record
                print(f"📝 [TOPIC] No existing topic attempt found. Creating new record with attempt_num=1")
                
                topic_progress = {
                    "user_id": user_id,
                    "stage_id": stage_id,
                    "exercise_id": exercise_id,
                    "topic_id": topic_id,
                    "attempt_num": 1,  # First attempt
                    "score": score,
                    "urdu_used": urdu_used,
                    "completed": completed,
                    "total_time_seconds": time_spent_seconds
                }
                
                print(f"📝 [TOPIC] Creating new topic progress record: {topic_progress}")
                result = self.client.table('ai_tutor_user_topic_progress').insert(topic_progress).execute()
                print(f"✅ [TOPIC] Topic progress created: {result.data[0] if result.data else 'No data'}")
            
            # Update daily analytics
            await self._update_daily_analytics(user_id, time_spent_seconds, score, urdu_used, completed)
            
            # Update exercise progress
            print(f"🔄 [TOPIC] Updating exercise progress...")
            await self._update_exercise_progress(user_id, stage_id, exercise_id, score, urdu_used, time_spent_seconds, topic_id)
            
            # Update user progress summary
            print(f"🔄 [TOPIC] Updating user progress summary...")
            await self._update_user_progress_summary(user_id, stage_id, exercise_id, topic_id, time_spent_seconds)
            
            print(f"✅ [TOPIC] Successfully recorded topic attempt for user {user_id}")
            logger.info(f"Successfully recorded topic attempt for user {user_id}")
            return {"success": True, "data": result.data[0] if result.data else None}
            
        except Exception as e:
            print(f"❌ [TOPIC] Error recording topic attempt for {user_id}: {str(e)}")
            logger.error(f"Error recording topic attempt for {user_id}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def _update_exercise_progress(self, user_id: str, stage_id: int, exercise_id: int, 
                                      score: float, urdu_used: bool, time_spent_seconds: int, topic_id: int = None):
        """Update exercise-level progress metrics"""
        print(f"🔄 [EXERCISE] Updating exercise progress for user {user_id}, stage {stage_id}, exercise {exercise_id}")
        try:
            # Get current exercise progress
            print(f"🔍 [EXERCISE] Fetching current exercise progress...")
            current = self.client.table('ai_tutor_user_exercise_progress').select('*').eq('user_id', user_id).eq('stage_id', stage_id).eq('exercise_id', exercise_id).execute()
            
            if not current.data:
                print(f"⚠️ [EXERCISE] No exercise progress found for user {user_id}, stage {stage_id}, exercise {exercise_id}")
                print(f"🆕 [EXERCISE] Creating new exercise progress record...")
                
                # Create new exercise progress record
                current_timestamp = datetime.now().isoformat()
                
                # Determine initial topic_id based on completion
                initial_topic_id = topic_id or 1
                # Use different thresholds for different exercises
                if exercise_id == 3:  # Problem-solving exercise
                    if score >= 60 and topic_id:
                        # If topic was completed successfully, start with next topic
                        initial_topic_id = topic_id + 1
                else:
                    if score >= 80 and topic_id:
                        # If topic was completed successfully, start with next topic
                        initial_topic_id = topic_id + 1
                
                new_exercise_data = {
                    "user_id": user_id,
                    "stage_id": stage_id,
                    "exercise_id": exercise_id,
                    "current_topic_id": initial_topic_id,
                    "attempts": 1,
                    "scores": [score],
                    "last_5_scores": [score],
                    "average_score": score,
                    "urdu_used": [urdu_used],
                    "time_spent_minutes": int(time_spent_seconds / 60),
                    "best_score": score,
                    "total_score": score,
                    "mature": score >= 60 if exercise_id == 3 else score >= 80,
                    "started_at": current_timestamp,
                    "last_attempt_at": current_timestamp
                }
                
                print(f"📝 [EXERCISE] Creating new exercise progress: {new_exercise_data}")
                create_result = self.client.table('ai_tutor_user_exercise_progress').insert(new_exercise_data).execute()
                print(f"✅ [EXERCISE] New exercise progress created: {create_result.data[0] if create_result.data else 'No data'}")
                return
            
            exercise_data = current.data[0]
            print(f"📊 [EXERCISE] Current exercise data: {exercise_data}")
            
            # Update arrays and metrics
            scores = exercise_data.get('scores', []) + [score]
            urdu_used_array = exercise_data.get('urdu_used', []) + [urdu_used]
            
            print(f"📊 [EXERCISE] Updated scores array: {scores}")
            print(f"📊 [EXERCISE] Updated urdu_used array: {urdu_used_array}")
            
            # Keep only last 5 scores for recent performance
            last_5_scores = scores[-5:] if len(scores) > 5 else scores
            print(f"📊 [EXERCISE] Last 5 scores: {last_5_scores}")
            
            # Calculate new metrics
            total_score = sum(scores)
            average_score = total_score / len(scores) if scores else 0
            best_score = max(scores) if scores else 0
            # Convert to integer for database compatibility
            time_spent_minutes = int(exercise_data.get('time_spent_minutes', 0) + (time_spent_seconds / 60))
            
            print(f"📊 [EXERCISE] Calculated metrics:")
            print(f"   - Total score: {total_score}")
            print(f"   - Average score: {average_score:.2f}")
            print(f"   - Best score: {best_score}")
            print(f"   - Time spent: {time_spent_minutes} minutes")
            
            # Check if exercise is mature (average score >= threshold)
            if exercise_id == 3:  # Problem-solving exercise
                mature = average_score >= 60  # 60% threshold for problem-solving
                print(f"📊 [EXERCISE] Exercise mature: {mature} (average >= 60)")
            else:
                mature = average_score >= 80  # 80% threshold for other exercises
                print(f"📊 [EXERCISE] Exercise mature: {mature} (average >= 80)")
            
            # Check if exercise is completed (3 consecutive scores >= threshold)
            completed = False
            if len(scores) >= 3:
                recent_scores = scores[-3:]
                # Use different thresholds for different exercises
                if exercise_id == 3:  # Problem-solving exercise
                    completed = all(s >= 60 for s in recent_scores)  # 60% threshold
                    print(f"📊 [EXERCISE] Recent 3 scores: {recent_scores}")
                    print(f"📊 [EXERCISE] Exercise completed: {completed} (3 consecutive >= 60)")
                else:
                    completed = all(s >= 80 for s in recent_scores)  # 80% threshold
                    print(f"📊 [EXERCISE] Recent 3 scores: {recent_scores}")
                    print(f"📊 [EXERCISE] Exercise completed: {completed} (3 consecutive >= 80)")
            
            # Update exercise progress
            current_timestamp = datetime.now().isoformat()
            
            update_data = {
                "attempts": len(scores),
                "scores": scores,
                "last_5_scores": last_5_scores,
                "average_score": average_score,
                "urdu_used": urdu_used_array,
                "time_spent_minutes": time_spent_minutes,
                "best_score": best_score,
                "total_score": total_score,
                "mature": mature,
                "last_attempt_at": current_timestamp
            }
            
            # Update current_topic_id based on topic completion
            current_topic_id = exercise_data.get('current_topic_id', 1)
            
            # Check if this topic was completed successfully
            # Use different thresholds for different exercises
            if exercise_id == 3:  # Problem-solving exercise
                topic_completed = score >= 60  # 60% threshold for problem-solving
            else:
                topic_completed = score >= 80  # 80% threshold for other exercises
            
            if topic_completed:
                # Increment topic_id for next topic when current topic is completed
                next_topic_id = current_topic_id + 1
                update_data["current_topic_id"] = next_topic_id
                print(f"🎉 [EXERCISE] Topic {current_topic_id} completed! Moving to topic {next_topic_id}")
            elif topic_id and topic_id > current_topic_id:
                # Update topic_id if user is working on a higher topic
                update_data["current_topic_id"] = topic_id
                print(f"📝 [EXERCISE] Updated current_topic_id to {topic_id}")
            
            # Check if exercise is completed (3 consecutive scores >= 80)
            if completed and not exercise_data.get('completed_at'):
                update_data["completed_at"] = current_timestamp
                print(f"🎉 [EXERCISE] Exercise marked as completed!")
            
            print(f"📝 [EXERCISE] Updating exercise with data: {update_data}")
            update_result = self.client.table('ai_tutor_user_exercise_progress').update(update_data).eq('user_id', user_id).eq('stage_id', stage_id).eq('exercise_id', exercise_id).execute()
            print(f"✅ [EXERCISE] Exercise progress updated successfully")
            
            logger.info(f"Updated exercise progress for user {user_id}, stage {stage_id}, exercise {exercise_id}")
            
        except Exception as e:
            print(f"❌ [EXERCISE] Error updating exercise progress: {str(e)}")
            logger.error(f"Error updating exercise progress: {str(e)}")
    
    async def _update_user_progress_summary(self, user_id: str, stage_id: int, exercise_id: int, 
                                          topic_id: int, time_spent_seconds: int):
        """Update user progress summary with latest activity"""
        print(f"🔄 [SUMMARY] Updating user progress summary for user {user_id}")
        try:
            # Get current progress summary
            print(f"🔍 [SUMMARY] Fetching current progress summary...")
            current = self.client.table('ai_tutor_user_progress_summary').select('*').eq('user_id', user_id).execute()
            
            if not current.data:
                print(f"⚠️ [SUMMARY] No progress summary found for user {user_id}")
                logger.warning(f"No progress summary found for user {user_id}")
                return
            
            summary = current.data[0]
            print(f"📊 [SUMMARY] Current summary: {summary}")
            
            # Update current position
            current_date = date.today()
            current_timestamp = datetime.now().isoformat()
            
            # Convert to integer for database compatibility
            total_time_spent_minutes = int(summary.get('total_time_spent_minutes', 0) + (time_spent_seconds / 60))
            
            update_data = {
                "current_stage": stage_id,
                "current_exercise": exercise_id,
                "topic_id": topic_id,
                "total_time_spent_minutes": total_time_spent_minutes,
                "last_activity_date": current_date.isoformat(),
                "updated_at": current_timestamp
            }
            
            print(f"📝 [SUMMARY] Updating current position: stage={stage_id}, exercise={exercise_id}, topic={topic_id}")
            
            # Calculate total exercises completed - use completed_at IS NOT NULL instead of completed column
            print(f"🔍 [SUMMARY] Calculating total exercises completed...")
            completed_exercises = self.client.table('ai_tutor_user_exercise_progress').select('*').eq('user_id', user_id).not_.is_('completed_at', 'null').execute()
            update_data["total_exercises_completed"] = len(completed_exercises.data)
            print(f"📊 [SUMMARY] Total exercises completed: {len(completed_exercises.data)}")
            
            # Calculate overall progress percentage
            total_stages = 6
            print(f"🔍 [SUMMARY] Calculating overall progress percentage...")
            completed_stages = self.client.table('ai_tutor_user_stage_progress').select('*').eq('user_id', user_id).not_.is_('completed_at', 'null').execute()
            overall_progress = (len(completed_stages.data) / total_stages) * 100
            update_data["overall_progress_percentage"] = overall_progress
            print(f"📊 [SUMMARY] Overall progress: {overall_progress:.2f}% ({len(completed_stages.data)}/{total_stages} stages)")
            
            # Calculate proper streak
            current_streak, longest_streak = await self._calculate_streak(user_id, current_date)
            update_data["streak_days"] = current_streak
            update_data["longest_streak"] = max(summary.get('longest_streak', 0), longest_streak)
            print(f"📊 [SUMMARY] Updated streak: current={current_streak}, longest={update_data['longest_streak']}")
            
            # Calculate session metrics
            session_metrics = await self._calculate_session_metrics(user_id)
            update_data.update(session_metrics)
            print(f"📊 [SUMMARY] Session metrics updated: {session_metrics}")
            
            print(f"📝 [SUMMARY] Final update data: {update_data}")
            update_result = self.client.table('ai_tutor_user_progress_summary').update(update_data).eq('user_id', user_id).execute()
            print(f"✅ [SUMMARY] User progress summary updated successfully")
            
            logger.info(f"Updated progress summary for user {user_id}")
            
        except Exception as e:
            print(f"❌ [SUMMARY] Error updating user progress summary: {str(e)}")
            logger.error(f"Error updating user progress summary: {str(e)}")
    
    async def get_user_progress(self, user_id: str) -> dict:
        """Get comprehensive user progress data"""
        print(f"🔄 [GET] Getting comprehensive user progress for user {user_id}")
        try:
            # Validate user_id
            if not user_id or not user_id.strip():
                raise ValueError("User ID is required")
            
            # Get progress summary
            print(f"🔍 [GET] Fetching progress summary...")
            summary = self.client.table('ai_tutor_user_progress_summary').select('*').eq('user_id', user_id).execute()
            print(f"📊 [GET] Progress summary: {summary.data[0] if summary.data else 'None'}")
            
            # Get stage progress
            print(f"🔍 [GET] Fetching stage progress...")
            stages = self.client.table('ai_tutor_user_stage_progress').select('*').eq('user_id', user_id).execute()
            print(f"📊 [GET] Stage progress: {len(stages.data)} stages")
            
            # Get exercise progress
            print(f"🔍 [GET] Fetching exercise progress...")
            exercises = self.client.table('ai_tutor_user_exercise_progress').select('*').eq('user_id', user_id).execute()
            print(f"📊 [GET] Exercise progress: {len(exercises.data)} exercises")
            
            # Get learning unlocks
            print(f"🔍 [GET] Fetching learning unlocks...")
            unlocks = self.client.table('ai_tutor_learning_unlocks').select('*').eq('user_id', user_id).execute()
            print(f"📊 [GET] Learning unlocks: {len(unlocks.data)} unlocks")
            
            result_data = {
                "summary": summary.data[0] if summary.data else None,
                "stages": stages.data,
                "exercises": exercises.data,
                "unlocks": unlocks.data
            }
            
            print(f"✅ [GET] Successfully retrieved user progress data")
            return {
                "success": True,
                "data": result_data
            }
            
        except Exception as e:
            print(f"❌ [GET] Error getting user progress for {user_id}: {str(e)}")
            logger.error(f"Error getting user progress for {user_id}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def get_current_topic_for_exercise(self, user_id: str, stage_id: int, exercise_id: int) -> dict:
        """Get the current topic_id for a specific exercise"""
        print(f"🔄 [TOPIC] Getting current topic for user {user_id}, stage {stage_id}, exercise {exercise_id}")
        try:
            # Validate parameters
            if not user_id or not user_id.strip():
                raise ValueError("User ID is required")
            
            if not (1 <= stage_id <= 6):
                raise ValueError(f"Invalid stage_id: {stage_id}. Must be between 1 and 6")
            
            if not (1 <= exercise_id <= 3):
                raise ValueError(f"Invalid exercise_id: {exercise_id}. Must be between 1 and 3")
            
            # Get exercise progress
            print(f"🔍 [TOPIC] Fetching exercise progress...")
            exercise_progress = self.client.table('ai_tutor_user_exercise_progress').select('*').eq('user_id', user_id).eq('stage_id', stage_id).eq('exercise_id', exercise_id).execute()
            
            if not exercise_progress.data:
                print(f"🆕 [TOPIC] No exercise progress found, starting with topic 1")
                return {"success": True, "current_topic_id": 1, "is_new_exercise": True}
            
            exercise_data = exercise_progress.data[0]
            current_topic_id = exercise_data.get('current_topic_id', 1)
            is_completed = exercise_data.get('completed_at') is not None
            
            print(f"📊 [TOPIC] Current topic_id: {current_topic_id}, Exercise completed: {is_completed}")
            
            # Check if current topic is completed and advance to next topic
            if not is_completed:
                # Get topic progress to check if current topic is completed
                topic_progress = self.client.table('ai_tutor_user_topic_progress').select('*').eq('user_id', user_id).eq('stage_id', stage_id).eq('exercise_id', exercise_id).eq('topic_id', current_topic_id).execute()
                
                if topic_progress.data:
                    topic_data = topic_progress.data[0]
                    topic_completed = topic_data.get('completed', False)
                    
                    if topic_completed:
                        # Current topic is completed, advance to next topic
                        next_topic_id = current_topic_id + 1
                        print(f"🎉 [TOPIC] Topic {current_topic_id} is completed! Advancing to topic {next_topic_id}")
                        
                        # Update the exercise progress with the new topic_id
                        update_result = self.client.table('ai_tutor_user_exercise_progress').update({
                            "current_topic_id": next_topic_id
                        }).eq('user_id', user_id).eq('stage_id', stage_id).eq('exercise_id', exercise_id).execute()
                        
                        if update_result.data:
                            print(f"✅ [TOPIC] Updated current_topic_id to {next_topic_id}")
                            current_topic_id = next_topic_id
                        else:
                            print(f"⚠️ [TOPIC] Failed to update current_topic_id, keeping {current_topic_id}")
            
            return {
                "success": True, 
                "current_topic_id": current_topic_id, 
                "is_new_exercise": False,
                "is_completed": is_completed,
                "exercise_data": exercise_data
            }
            
        except Exception as e:
            print(f"❌ [TOPIC] Error getting current topic: {str(e)}")
            logger.error(f"Error getting current topic: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def get_user_topic_progress(self, user_id: str, stage_id: int, exercise_id: int) -> dict:
        """Get user's topic progress for a specific stage and exercise"""
        print(f"🔄 [TOPIC_PROGRESS] Getting topic progress for user {user_id}")
        print(f"📊 [TOPIC_PROGRESS] Stage: {stage_id}, Exercise: {exercise_id}")
        
        try:
            # Validate parameters
            if not user_id or not user_id.strip():
                raise ValueError("User ID is required")
            
            # Query the ai_tutor_user_topic_progress table
            result = self.client.table('ai_tutor_user_topic_progress').select('*').eq('user_id', user_id).eq('stage_id', stage_id).eq('exercise_id', exercise_id).execute()
            
            print(f"📊 [TOPIC_PROGRESS] Found {len(result.data)} topic progress records")
            
            if result.data:
                print(f"📋 [TOPIC_PROGRESS] Topic progress data: {result.data}")
            else:
                print(f"ℹ️ [TOPIC_PROGRESS] No topic progress found for user {user_id}, stage {stage_id}, exercise {exercise_id}")
            
            return {
                "success": True,
                "data": result.data
            }
            
        except Exception as e:
            print(f"❌ [TOPIC_PROGRESS] Error getting topic progress: {str(e)}")
            logger.error(f"Error getting topic progress: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def check_and_unlock_content(self, user_id: str) -> dict:
        """Check if user should unlock new content based on progress"""
        print(f"🔄 [UNLOCK] Checking content unlocks for user {user_id}")
        try:
            # Validate user_id
            if not user_id or not user_id.strip():
                raise ValueError("User ID is required")
            
            # Get current exercise progress - use completed_at IS NOT NULL instead of completed column
            print(f"🔍 [UNLOCK] Fetching completed exercises...")
            current_exercise = self.client.table('ai_tutor_user_exercise_progress').select('*').eq('user_id', user_id).not_.is_('completed_at', 'null').execute()
            print(f"📊 [UNLOCK] Found {len(current_exercise.data)} completed exercises")
            
            unlocked_content = []
            current_timestamp = datetime.now().isoformat()
            
            for exercise in current_exercise.data:
                stage_id = exercise['stage_id']
                exercise_id = exercise['exercise_id']
                print(f"🔍 [UNLOCK] Processing completed exercise: stage {stage_id}, exercise {exercise_id}")
                
                # Check if next exercise should be unlocked
                if exercise_id < 3:  # Not the last exercise in stage
                    next_exercise_id = exercise_id + 1
                    print(f"🔍 [UNLOCK] Checking if exercise {next_exercise_id} should be unlocked...")
                    
                    # Check if next exercise is already unlocked
                    existing_unlock = self.client.table('ai_tutor_learning_unlocks').select('*').eq('user_id', user_id).eq('stage_id', stage_id).eq('exercise_id', next_exercise_id).execute()
                    
                    if not existing_unlock.data or not existing_unlock.data[0]['is_unlocked']:
                        print(f"🔓 [UNLOCK] Unlocking exercise {next_exercise_id} in stage {stage_id}")
                        # Since initialization creates these rows, we should always UPDATE.
                        unlock_data = {
                            "is_unlocked": True,
                            "unlock_criteria_met": True,
                            "unlocked_at": current_timestamp,
                            "unlocked_by_criteria": f"Completed exercise {exercise_id} in stage {stage_id}"
                        }
                        
                        unlock_result = self.client.table('ai_tutor_learning_unlocks').update(unlock_data).match({
                            'user_id': user_id, 
                            'stage_id': stage_id, 
                            'exercise_id': next_exercise_id
                        }).execute()

                        print(f"✅ [UNLOCK] Exercise {next_exercise_id} unlocked successfully")
                        unlocked_content.append(f"Stage {stage_id}, Exercise {next_exercise_id}")
                    else:
                        print(f"ℹ️ [UNLOCK] Exercise {next_exercise_id} already unlocked")
                
                # Check if next stage should be unlocked (if all exercises in current stage are completed)
                if exercise_id == 3:  # Last exercise in stage
                    print(f"🔍 [UNLOCK] Checking if stage {stage_id + 1} should be unlocked...")
                    all_exercises_completed = self.client.table('ai_tutor_user_exercise_progress').select('exercise_id').eq('user_id', user_id).eq('stage_id', stage_id).not_.is_('completed_at', 'null').execute()
                    
                    if len(all_exercises_completed.data) == 3:  # All exercises completed
                        next_stage_id = stage_id + 1
                        
                        if next_stage_id <= 6:  # Valid stage
                            print(f"🔓 [UNLOCK] Unlocking stage {next_stage_id}")

                            # Explicitly check if the stage unlock record exists
                            existing_stage_unlock = self.client.table('ai_tutor_learning_unlocks').select('id').is_('exercise_id', 'null').eq('user_id', user_id).eq('stage_id', next_stage_id).execute()

                            stage_unlock_payload = {
                                "is_unlocked": True,
                                "unlock_criteria_met": True,
                                "unlocked_at": current_timestamp,
                                "unlocked_by_criteria": f"Completed all exercises in stage {stage_id}"
                            }
                            
                            if existing_stage_unlock.data:
                                # Row exists, so UPDATE it
                                print(f"🔓 [UNLOCK] Updating existing record to unlock stage {next_stage_id}")
                                self.client.table('ai_tutor_learning_unlocks').update(stage_unlock_payload).eq('user_id', user_id).eq('stage_id', next_stage_id).is_('exercise_id', 'null').execute()
                            else:
                                # Row does not exist, so INSERT it
                                print(f"🔓 [UNLOCK] Inserting new record to unlock stage {next_stage_id}")
                                stage_insert_payload = stage_unlock_payload.copy()
                                stage_insert_payload['user_id'] = user_id
                                stage_insert_payload['stage_id'] = next_stage_id
                                self.client.table('ai_tutor_learning_unlocks').insert(stage_insert_payload).execute()
                            
                            unlocked_content.append(f"Stage {next_stage_id}")
                        else:
                            print(f"ℹ️ [UNLOCK] Stage {next_stage_id} is beyond valid range (max 6)")
                    else:
                        print(f"ℹ️ [UNLOCK] Not all exercises completed in stage {stage_id} ({len(all_exercises_completed.data)}/3)")
            
            print(f"📊 [UNLOCK] Total unlocked content: {unlocked_content}")
            return {"success": True, "unlocked_content": unlocked_content}
            
        except Exception as e:
            print(f"❌ [UNLOCK] Error checking content unlocks for {user_id}: {str(e)}")
            logger.error(f"Error checking content unlocks for {user_id}: {str(e)}")
            return {"success": False, "error": str(e)}

# Global instance
progress_tracker = SupabaseProgressTracker() 