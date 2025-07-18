import os
import asyncio
from datetime import date, datetime
from supabase import create_client, Client
from dotenv import load_dotenv
import logging

# Load environment variables
# load_dotenv(override=True)
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

print("SUPABASE_URL: ",SUPABASE_URL)

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    logger.error("Missing Supabase environment variables")
    raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")

# Create Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

class SupabaseProgressTracker:
    """Professional progress tracking service for AI Tutor app"""
    
    def __init__(self):
        self.client = supabase
        print("🔧 [SUPABASE] Progress Tracker initialized")
        print(f"🔧 [SUPABASE] Connected to: {SUPABASE_URL}")
        logger.info("Supabase Progress Tracker initialized")
    
    async def initialize_user_progress(self, user_id: str) -> dict:
        """Initialize user progress when they first start using the app"""
        print(f"🔄 [INIT] Starting progress initialization for user: {user_id}")
        try:
            print(f"🔍 [INIT] Checking if user progress already exists...")
            
            # Check if user progress already exists
            existing = self.client.table('ai_tutor_user_progress_summary').select('*').eq('user_id', user_id).execute()
            print(f"📊 [INIT] Existing progress check result: {len(existing.data)} records found")
            
            if existing.data:
                print(f"✅ [INIT] User progress already exists for: {user_id}")
                print(f"📋 [INIT] Existing data: {existing.data[0]}")
                logger.info(f"User progress already exists for: {user_id}")
                return {"success": True, "message": "User progress already initialized", "data": existing.data[0]}
            
            print(f"🆕 [INIT] No existing progress found, creating new user progress...")
            
            # Initialize user progress summary
            current_date = date.today()
            
            progress_summary = {
                "user_id": user_id,
                "current_stage": 1,
                "current_exercise": 1,
                "topic_id": 1,
                "urdu_enabled": True,
                "unlocked_stages": [1],
                "unlocked_exercises": {"1": [1]},
                "overall_progress_percentage": 0.00,
                "total_time_spent_minutes": 0,
                "total_exercises_completed": 0,
                "streak_days": 0,
                "longest_streak": 0,
                "average_session_duration_minutes": 0.00,
                "weekly_learning_hours": 0.00,
                "monthly_learning_hours": 0.00,
                "first_activity_date": current_date.isoformat(),
                "last_activity_date": current_date.isoformat()
            }
            
            print(f"📝 [INIT] Creating progress summary: {progress_summary}")
            result = self.client.table('ai_tutor_user_progress_summary').insert(progress_summary).execute()
            print(f"✅ [INIT] Progress summary created: {result.data[0] if result.data else 'No data'}")
            
            # Initialize stage progress for stage 1
            current_timestamp = datetime.now().isoformat()
            
            stage_progress = {
                "user_id": user_id,
                "stage_id": 1,
                "started_at": current_timestamp
            }
            
            print(f"📝 [INIT] Creating stage progress: {stage_progress}")
            stage_result = self.client.table('ai_tutor_user_stage_progress').insert(stage_progress).execute()
            print(f"✅ [INIT] Stage progress created: {stage_result.data[0] if stage_result.data else 'No data'}")
            
            # Initialize exercise progress for stage 1 exercises
            exercise_progress_data = [
                {"user_id": user_id, "stage_id": 1, "exercise_id": 1, "started_at": current_timestamp},
                {"user_id": user_id, "stage_id": 1, "exercise_id": 2, "started_at": current_timestamp},
                {"user_id": user_id, "stage_id": 1, "exercise_id": 3, "started_at": current_timestamp}
            ]
            
            print(f"📝 [INIT] Creating exercise progress for {len(exercise_progress_data)} exercises")
            exercise_result = self.client.table('ai_tutor_user_exercise_progress').insert(exercise_progress_data).execute()
            print(f"✅ [INIT] Exercise progress created: {len(exercise_result.data) if exercise_result.data else 0} records")
            
            # Initialize learning unlocks
            unlock_data = [
                {"user_id": user_id, "stage_id": 1, "exercise_id": None, "is_unlocked": True, "unlock_criteria_met": True},
                {"user_id": user_id, "stage_id": 1, "exercise_id": 1, "is_unlocked": True, "unlock_criteria_met": True},
                {"user_id": user_id, "stage_id": 1, "exercise_id": 2, "is_unlocked": False, "unlock_criteria_met": False},
                {"user_id": user_id, "stage_id": 1, "exercise_id": 3, "is_unlocked": False, "unlock_criteria_met": False}
            ]
            
            print(f"📝 [INIT] Creating learning unlocks: {len(unlock_data)} unlock records")
            unlock_result = self.client.table('ai_tutor_learning_unlocks').insert(unlock_data).execute()
            print(f"✅ [INIT] Learning unlocks created: {len(unlock_result.data) if unlock_result.data else 0} records")
            
            print(f"🎉 [INIT] Successfully initialized progress for user: {user_id}")
            logger.info(f"Successfully initialized progress for user: {user_id}")
            return {"success": True, "message": "User progress initialized successfully", "data": result.data[0] if result.data else None}
            
        except Exception as e:
            print(f"❌ [INIT] Error initializing user progress for {user_id}: {str(e)}")
            logger.error(f"Error initializing user progress for {user_id}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def record_topic_attempt(self, user_id: str, stage_id: int, exercise_id: int, topic_id: int, 
                                 score: float, urdu_used: bool, time_spent_seconds: int, completed: bool) -> dict:
        """Record a topic attempt with detailed metrics"""
        print(f"🔄 [TOPIC] Recording topic attempt for user {user_id}")
        print(f"📊 [TOPIC] Details: stage={stage_id}, exercise={exercise_id}, topic={topic_id}")
        print(f"📊 [TOPIC] Metrics: score={score}, urdu_used={urdu_used}, time_spent={time_spent_seconds}s, completed={completed}")
        
        try:
            # Get next attempt number
            print(f"🔍 [TOPIC] Getting attempt number for topic {topic_id}...")
            attempts = self.client.table('ai_tutor_user_topic_progress').select('attempt_num').eq('user_id', user_id).eq('stage_id', stage_id).eq('exercise_id', exercise_id).eq('topic_id', topic_id).execute()
            
            attempt_num = len(attempts.data) + 1
            print(f"📝 [TOPIC] Attempt number: {attempt_num} (previous attempts: {len(attempts.data)})")
            
            # Record topic progress
            topic_progress = {
                "user_id": user_id,
                "stage_id": stage_id,
                "exercise_id": exercise_id,
                "topic_id": topic_id,
                "attempt_num": attempt_num,
                "score": score,
                "urdu_used": urdu_used,
                "completed": completed,
                "total_time_seconds": time_spent_seconds
            }
            
            print(f"📝 [TOPIC] Creating topic progress record: {topic_progress}")
            result = self.client.table('ai_tutor_user_topic_progress').insert(topic_progress).execute()
            print(f"✅ [TOPIC] Topic progress recorded: {result.data[0] if result.data else 'No data'}")
            
            # Update exercise progress
            print(f"🔄 [TOPIC] Updating exercise progress...")
            await self._update_exercise_progress(user_id, stage_id, exercise_id, score, urdu_used, time_spent_seconds)
            
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
                                      score: float, urdu_used: bool, time_spent_seconds: int):
        """Update exercise-level progress metrics"""
        print(f"🔄 [EXERCISE] Updating exercise progress for user {user_id}, stage {stage_id}, exercise {exercise_id}")
        try:
            # Get current exercise progress
            print(f"🔍 [EXERCISE] Fetching current exercise progress...")
            current = self.client.table('ai_tutor_user_exercise_progress').select('*').eq('user_id', user_id).eq('stage_id', stage_id).eq('exercise_id', exercise_id).execute()
            
            if not current.data:
                print(f"⚠️ [EXERCISE] No exercise progress found for user {user_id}, stage {stage_id}, exercise {exercise_id}")
                logger.warning(f"No exercise progress found for user {user_id}, stage {stage_id}, exercise {exercise_id}")
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
            time_spent_minutes = exercise_data.get('time_spent_minutes', 0) + (time_spent_seconds / 60)
            
            print(f"📊 [EXERCISE] Calculated metrics:")
            print(f"   - Total score: {total_score}")
            print(f"   - Average score: {average_score:.2f}")
            print(f"   - Best score: {best_score}")
            print(f"   - Time spent: {time_spent_minutes:.2f} minutes")
            
            # Check if exercise is mature (average score >= 80)
            mature = average_score >= 80
            print(f"📊 [EXERCISE] Exercise mature: {mature} (average >= 80)")
            
            # Check if exercise is completed (3 consecutive scores >= 80)
            completed = False
            if len(scores) >= 3:
                recent_scores = scores[-3:]
                completed = all(s >= 80 for s in recent_scores)
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
                "mature": mature,
                "total_score": total_score,
                "best_score": best_score,
                "time_spent_minutes": time_spent_minutes,
                "last_attempt_at": current_timestamp
            }
            
            if completed and not exercise_data.get('completed'):
                update_data["completed"] = True
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
            current_date = date.today().isoformat()
            current_timestamp = datetime.now().isoformat()
            
            update_data = {
                "current_stage": stage_id,
                "current_exercise": exercise_id,
                "topic_id": topic_id,
                "total_time_spent_minutes": summary.get('total_time_spent_minutes', 0) + (time_spent_seconds / 60),
                "last_activity_date": current_date,
                "updated_at": current_timestamp
            }
            
            print(f"📝 [SUMMARY] Updating current position: stage={stage_id}, exercise={exercise_id}, topic={topic_id}")
            
            # Calculate total exercises completed
            print(f"🔍 [SUMMARY] Calculating total exercises completed...")
            completed_exercises = self.client.table('ai_tutor_user_exercise_progress').select('*').eq('user_id', user_id).eq('completed', True).execute()
            update_data["total_exercises_completed"] = len(completed_exercises.data)
            print(f"📊 [SUMMARY] Total exercises completed: {len(completed_exercises.data)}")
            
            # Calculate overall progress percentage
            total_stages = 6
            print(f"🔍 [SUMMARY] Calculating overall progress percentage...")
            completed_stages = self.client.table('ai_tutor_user_stage_progress').select('*').eq('user_id', user_id).eq('completed', True).execute()
            overall_progress = (len(completed_stages.data) / total_stages) * 100
            update_data["overall_progress_percentage"] = overall_progress
            print(f"📊 [SUMMARY] Overall progress: {overall_progress:.2f}% ({len(completed_stages.data)}/{total_stages} stages)")
            
            # Update streak (simplified - you might want more sophisticated streak logic)
            # For now, just increment if user is active today
            update_data["streak_days"] = summary.get('streak_days', 0) + 1
            print(f"📊 [SUMMARY] Updated streak: {update_data['streak_days']} days")
            
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
    
    async def check_and_unlock_content(self, user_id: str) -> dict:
        """Check if user should unlock new content based on progress"""
        print(f"🔄 [UNLOCK] Checking content unlocks for user {user_id}")
        try:
            # Get current exercise progress
            print(f"🔍 [UNLOCK] Fetching completed exercises...")
            current_exercise = self.client.table('ai_tutor_user_exercise_progress').select('*').eq('user_id', user_id).eq('completed', True).execute()
            print(f"📊 [UNLOCK] Found {len(current_exercise.data)} completed exercises")
            
            unlocked_content = []
            
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
                        # Unlock next exercise
                        current_timestamp = datetime.now().isoformat()
                        
                        unlock_data = {
                            "user_id": user_id,
                            "stage_id": stage_id,
                            "exercise_id": next_exercise_id,
                            "is_unlocked": True,
                            "unlock_criteria_met": True,
                            "unlocked_at": current_timestamp,
                            "unlocked_by_criteria": f"Completed exercise {exercise_id} in stage {stage_id}"
                        }
                        
                        unlock_result = self.client.table('ai_tutor_learning_unlocks').upsert(unlock_data).execute()
                        print(f"✅ [UNLOCK] Exercise {next_exercise_id} unlocked successfully")
                        unlocked_content.append(f"Stage {stage_id}, Exercise {next_exercise_id}")
                    else:
                        print(f"ℹ️ [UNLOCK] Exercise {next_exercise_id} already unlocked")
                
                # Check if next stage should be unlocked (if all exercises in current stage are completed)
                if exercise_id == 3:  # Last exercise in stage
                    print(f"🔍 [UNLOCK] Checking if stage {stage_id + 1} should be unlocked...")
                    all_exercises_completed = self.client.table('ai_tutor_user_exercise_progress').select('*').eq('user_id', user_id).eq('stage_id', stage_id).eq('completed', True).execute()
                    
                    if len(all_exercises_completed.data) == 3:  # All exercises completed
                        next_stage_id = stage_id + 1
                        
                        if next_stage_id <= 6:  # Valid stage
                            print(f"🔓 [UNLOCK] Unlocking stage {next_stage_id}")
                            # Unlock next stage
                            stage_unlock_data = {
                                "user_id": user_id,
                                "stage_id": next_stage_id,
                                "exercise_id": None,
                                "is_unlocked": True,
                                "unlock_criteria_met": True,
                                "unlocked_at": current_timestamp,
                                "unlocked_by_criteria": f"Completed all exercises in stage {stage_id}"
                            }
                            
                            stage_unlock_result = self.client.table('ai_tutor_learning_unlocks').upsert(stage_unlock_data).execute()
                            print(f"✅ [UNLOCK] Stage {next_stage_id} unlocked successfully")
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