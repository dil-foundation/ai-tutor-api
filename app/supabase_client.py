import os
import asyncio
from datetime import date, datetime, timedelta
from supabase.client import create_client, Client
from dotenv import load_dotenv
import logging
from typing import Dict, List, Optional, Tuple

# Load environment variables
load_dotenv(override=True)

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
    
    async def get_all_stages(self) -> List[Dict]:
        """Fetches all stages from the content hierarchy."""
        try:
            print("🔄 [CONTENT] Fetching all stages...")
            result = self.client.rpc('get_all_stages_with_counts').execute()
            if result.data:
                print(f"✅ [CONTENT] Found {len(result.data)} stages.")
                return result.data
            return []
        except Exception as e:
            print(f"❌ [CONTENT] Error fetching stages: {str(e)}")
            logger.error(f"Error fetching stages: {str(e)}")
            return []

    async def get_exercises_for_stage(self, stage_number: int) -> List[Dict]:
        """Fetches all exercises for a given stage from the content hierarchy."""
        try:
            print(f"🔄 [CONTENT] Fetching exercises for stage {stage_number}...")
            result = self.client.rpc('get_exercises_for_stage_with_counts', {'stage_num': stage_number}).execute()
            if result.data:
                print(f"✅ [CONTENT] Found {len(result.data)} exercises for stage {stage_number}.")
                return result.data
            return []
        except Exception as e:
            print(f"❌ [CONTENT] Error fetching exercises for stage {stage_number}: {str(e)}")
            logger.error(f"Error fetching exercises for stage {stage_number}: {str(e)}")
            return []
    
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
        Returns: total_time_spent_minutes, average_session_duration, weekly_hours, monthly_hours
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
                    'total_time_spent_minutes': 0,
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
            print(f"   - Total time (minutes): {total_time_minutes}")
            print(f"   - Average session: {average_session_duration:.2f} minutes")
            print(f"   - Weekly hours: {weekly_hours:.2f}")
            print(f"   - Monthly hours: {monthly_hours:.2f}")
                
            return {
                'total_time_spent_minutes': total_time_minutes,
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

    async def _calculate_total_learning_time(self, user_id: str) -> int:
        """Calculates the user's all-time total learning time from daily analytics."""
        try:
            print(f"🔄 [SESSION] Calculating ALL-TIME learning time for user: {user_id}")
            # Get all daily analytics records for the user
            analytics_result = self.client.table('ai_tutor_daily_learning_analytics').select(
                'total_time_minutes'
            ).eq('user_id', user_id).execute()
            
            if not analytics_result.data:
                return 0
                
            # Sum up the total time spent
            total_time = sum(record.get('total_time_minutes', 0) for record in analytics_result.data)
            print(f"📊 [SESSION] All-time learning time: {total_time} minutes")
            return total_time
            
        except Exception as e:
            print(f"❌ [SESSION] Error calculating all-time learning time: {str(e)}")
            logger.error(f"Error calculating all-time learning time for {user_id}: {str(e)}")
            return 0
    
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
            # Step 1: Fetch dynamic curriculum structure
            print("🔄 [INIT] Fetching dynamic curriculum structure...")
            all_stages = await self.get_all_stages()
            if not all_stages:
                raise ValueError("Could not fetch curriculum stages from the database.")
            
            total_stages_count = len(all_stages)
            print(f"📚 [INIT] Found {total_stages_count} stages in the curriculum.")

            # Step 2: Prepare all the data needed for initialization
            current_date = date.today()
            current_timestamp = datetime.now().isoformat()
            
            # Treat stage 0 as stage 1 for progress setup, but store original assignment
            start_stage = assigned_start_stage
            
            completed_stages = list(range(0, start_stage))
            unlocked_stages = list(range(0, start_stage + 1))
            
            unlocked_exercises_map = {}
            total_exercises_completed = 0
            for stage_num in completed_stages:
                exercises = await self.get_exercises_for_stage(stage_num)
                unlocked_exercises_map[str(stage_num)] = [e['exercise_number'] for e in exercises]
                total_exercises_completed += len(exercises)
            
            start_stage_exercises = await self.get_exercises_for_stage(start_stage)
            if start_stage_exercises:
                unlocked_exercises_map[str(start_stage)] = [start_stage_exercises[0]['exercise_number']]
            else:
                unlocked_exercises_map[str(start_stage)] = []

            # Step 3: Upsert the user progress summary
            progress_summary_payload = {
                "user_id": user_id,
                "current_stage": start_stage,
                "current_exercise": 1,
                "topic_id": 1,
                "unlocked_stages": unlocked_stages,
                "unlocked_exercises": unlocked_exercises_map,
                "overall_progress_percentage": (len(completed_stages) / total_stages_count) * 100 if total_stages_count > 0 else 0,
                "total_exercises_completed": total_exercises_completed,
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

            # Step 4: Create/Update stage progress records
            print("🔍 [INIT] Checking for existing stage progress records...")
            existing_stages_res = self.client.table('ai_tutor_user_stage_progress').select('*').eq('user_id', user_id).execute()
            existing_stages = {s['stage_id']: s for s in existing_stages_res.data}
            
            stage_progress_to_create = []
            stage_progress_to_update = []
            
            # Handle completed stages (previous stages that should be marked as completed)
            for stage_id in completed_stages:
                exercises_in_stage = await self.get_exercises_for_stage(stage_id)
                
                if stage_id not in existing_stages:
                    # Create new stage progress record as completed
                    stage_progress_to_create.append({
                        "user_id": user_id, "stage_id": stage_id, "started_at": current_timestamp,
                        "completed_at": current_timestamp, "completed": True,
                        "progress_percentage": 100.0, "exercises_completed": len(exercises_in_stage)
                    })
                    print(f"📝 [INIT] Will create completed stage progress for stage {stage_id}")
                else:
                    # Update existing stage progress record to mark as completed
                    existing_stage = existing_stages[stage_id]
                    if not existing_stage.get('completed', False):
                        stage_progress_to_update.append({
                            "stage_id": stage_id,
                            "completed": True,
                            "completed_at": current_timestamp,
                            "progress_percentage": 100.0,
                            "exercises_completed": len(exercises_in_stage)
                        })
                        print(f"📝 [INIT] Will update stage {stage_id} to completed")
            
            # Handle current stage (starting stage)
            if start_stage not in existing_stages:
                stage_progress_to_create.append({"user_id": user_id, "stage_id": start_stage, "started_at": current_timestamp})
                print(f"📝 [INIT] Will create stage progress for starting stage {start_stage}")
            
            # Execute stage progress operations
            if stage_progress_to_create:
                print(f"📝 [INIT] Creating {len(stage_progress_to_create)} new stage progress records...")
                self.client.table('ai_tutor_user_stage_progress').insert(stage_progress_to_create).execute()
                print("✅ [INIT] Stage progress records created.")
            
            if stage_progress_to_update:
                print(f"📝 [INIT] Updating {len(stage_progress_to_update)} existing stage progress records...")
                for update_data in stage_progress_to_update:
                    self.client.table('ai_tutor_user_stage_progress').update({
                        "completed": update_data["completed"],
                        "completed_at": update_data["completed_at"],
                        "progress_percentage": update_data["progress_percentage"],
                        "exercises_completed": update_data["exercises_completed"]
                    }).eq('user_id', user_id).eq('stage_id', update_data["stage_id"]).execute()
                print("✅ [INIT] Stage progress records updated.")
            
            if not stage_progress_to_create and not stage_progress_to_update:
                print("✅ [INIT] No stage progress records needed.")

            # Step 5: Create exercise progress records for completed stages
            print("🔍 [INIT] Creating exercise progress records for completed stages...")
            existing_exercises_res = self.client.table('ai_tutor_user_exercise_progress').select('stage_id, exercise_id').eq('user_id', user_id).execute()
            existing_exercises = {(e['stage_id'], e['exercise_id']) for e in existing_exercises_res.data}
            
            exercise_progress_to_create = []
            for stage_id in completed_stages:
                exercises_in_stage = await self.get_exercises_for_stage(stage_id)
                for exercise in exercises_in_stage:
                    exercise_id = exercise['exercise_number']
                    if (stage_id, exercise_id) not in existing_exercises:
                        exercise_progress_to_create.append({
                            "user_id": user_id,
                            "stage_id": stage_id,
                            "exercise_id": exercise_id,
                            "started_at": current_timestamp,
                            "completed_at": current_timestamp,
                            "attempts": 1,
                            "scores": [100.0],  # Perfect score for auto-completed exercises
                            "last_5_scores": [100.0],
                            "average_score": 100.0,
                            "urdu_used": [False],
                            "mature": True,
                            "total_score": 100.0,
                            "best_score": 100.0,
                            "time_spent_minutes": 0,
                            "current_topic_id": 1
                        })
                        print(f"📝 [INIT] Will create completed exercise progress for stage {stage_id}, exercise {exercise_id}")
            
            if exercise_progress_to_create:
                print(f"📝 [INIT] Creating {len(exercise_progress_to_create)} exercise progress records...")
                self.client.table('ai_tutor_user_exercise_progress').insert(exercise_progress_to_create).execute()
                print("✅ [INIT] Exercise progress records created.")
            else:
                print("✅ [INIT] No exercise progress records needed.")

            # Step 6: Create topic progress records for completed stages
            print("🔍 [INIT] Creating topic progress records for completed stages...")
            existing_topics_res = self.client.table('ai_tutor_user_topic_progress').select('stage_id, exercise_id, topic_id').eq('user_id', user_id).execute()
            existing_topics = {(t['stage_id'], t['exercise_id'], t['topic_id']) for t in existing_topics_res.data}
            
            topic_progress_to_create = []
            for stage_id in completed_stages:
                exercises_in_stage = await self.get_exercises_for_stage(stage_id)
                for exercise in exercises_in_stage:
                    exercise_id = exercise['exercise_number']
                    # Get topics for this exercise
                    topics_result = await self.get_topics_for_exercise(stage_id, exercise_id)
                    if topics_result["success"]:
                        topics = topics_result["data"]
                        for topic in topics:
                            topic_id = topic['topic_id']
                            if (stage_id, exercise_id, topic_id) not in existing_topics:
                                topic_progress_to_create.append({
                                    "user_id": user_id,
                                    "stage_id": stage_id,
                                    "exercise_id": exercise_id,
                                    "topic_id": topic_id,
                                    "attempt_num": 1,
                                    "score": 100.0,  # Perfect score for auto-completed topics
                                    "urdu_used": False,
                                    "completed": True,
                                    "total_time_seconds": 0
                                })
                                print(f"📝 [INIT] Will create completed topic progress for stage {stage_id}, exercise {exercise_id}, topic {topic_id}")
            
            if topic_progress_to_create:
                print(f"📝 [INIT] Creating {len(topic_progress_to_create)} topic progress records...")
                self.client.table('ai_tutor_user_topic_progress').insert(topic_progress_to_create).execute()
                print("✅ [INIT] Topic progress records created.")
            else:
                print("✅ [INIT] No topic progress records needed.")

            # Step 7: Create/Update learning unlock records
            print("🔍 [INIT] Checking for existing learning unlock records...")
            existing_unlocks_res = self.client.table('ai_tutor_learning_unlocks').select('*').eq('user_id', user_id).execute()
            existing_unlocks = {(u['stage_id'], u['exercise_id']): u for u in existing_unlocks_res.data}

            unlocks_to_create = []
            unlocks_to_update = []
            
            # First, determine which stages should be unlocked vs locked
            all_stages = await self.get_all_stages()
            all_stage_numbers = [s['stage_number'] for s in all_stages]
            
            # Process each stage
            for stage_id in all_stage_numbers:
                should_be_unlocked = stage_id in unlocked_stages
                
                # Stage unlock record
                stage_unlock_key = (stage_id, None)
                if stage_unlock_key in existing_unlocks:
                    existing_unlock = existing_unlocks[stage_unlock_key]
                    if existing_unlock['is_unlocked'] != should_be_unlocked:
                        unlocks_to_update.append({
                            "stage_id": stage_id,
                            "exercise_id": None,
                            "is_unlocked": should_be_unlocked,
                            "unlock_criteria_met": should_be_unlocked,
                            "unlocked_at": current_timestamp if should_be_unlocked else None,
                            "unlocked_by_criteria": "Initial assignment" if should_be_unlocked else None
                        })
                        print(f"📝 [INIT] Will update stage {stage_id} unlock to: {should_be_unlocked}")
                else:
                    unlocks_to_create.append({
                        "user_id": user_id, 
                        "stage_id": stage_id, 
                        "exercise_id": None, 
                        "is_unlocked": should_be_unlocked, 
                        "unlock_criteria_met": should_be_unlocked, 
                        "unlocked_at": current_timestamp if should_be_unlocked else None, 
                        "unlocked_by_criteria": "Initial assignment" if should_be_unlocked else None
                    })
                    print(f"📝 [INIT] Will create stage {stage_id} unlock: {should_be_unlocked}")
                
                # Exercise unlock records for this stage
                exercises_in_stage = await self.get_exercises_for_stage(stage_id)
                for exercise in exercises_in_stage:
                    exercise_id = exercise['exercise_number']
                    exercise_unlock_key = (stage_id, exercise_id)
                    
                    # Determine if this exercise should be unlocked
                    exercise_should_be_unlocked = False
                    if stage_id in completed_stages:
                        # All exercises unlocked in completed stages
                        exercise_should_be_unlocked = True
                    elif stage_id == start_stage and exercise_id == 1:
                        # Only first exercise unlocked in starting stage
                        exercise_should_be_unlocked = True
                    
                    if exercise_unlock_key in existing_unlocks:
                        existing_unlock = existing_unlocks[exercise_unlock_key]
                        if existing_unlock['is_unlocked'] != exercise_should_be_unlocked:
                            unlocks_to_update.append({
                                "stage_id": stage_id,
                                "exercise_id": exercise_id,
                                "is_unlocked": exercise_should_be_unlocked,
                                "unlock_criteria_met": exercise_should_be_unlocked,
                                "unlocked_at": current_timestamp if exercise_should_be_unlocked else None,
                                "unlocked_by_criteria": "Initial assignment" if exercise_should_be_unlocked else None
                            })
                            print(f"📝 [INIT] Will update stage {stage_id}, exercise {exercise_id} unlock to: {exercise_should_be_unlocked}")
                    else:
                        unlocks_to_create.append({
                            "user_id": user_id,
                            "stage_id": stage_id,
                            "exercise_id": exercise_id,
                            "is_unlocked": exercise_should_be_unlocked,
                            "unlock_criteria_met": exercise_should_be_unlocked,
                            "unlocked_at": current_timestamp if exercise_should_be_unlocked else None,
                            "unlocked_by_criteria": "Initial assignment" if exercise_should_be_unlocked else None
                        })
                        print(f"📝 [INIT] Will create stage {stage_id}, exercise {exercise_id} unlock: {exercise_should_be_unlocked}")

            # Execute unlock operations
            if unlocks_to_create:
                print(f"📝 [INIT] Creating {len(unlocks_to_create)} new learning unlock records...")
                self.client.table('ai_tutor_learning_unlocks').insert(unlocks_to_create).execute()
                print("✅ [INIT] Learning unlock records created.")
            
            if unlocks_to_update:
                print(f"📝 [INIT] Updating {len(unlocks_to_update)} existing learning unlock records...")
                for update_data in unlocks_to_update:
                    self.client.table('ai_tutor_learning_unlocks').update({
                        "is_unlocked": update_data["is_unlocked"],
                        "unlock_criteria_met": update_data["unlock_criteria_met"],
                        "unlocked_at": update_data["unlocked_at"],
                        "unlocked_by_criteria": update_data["unlocked_by_criteria"]
                    }).eq('user_id', user_id).eq('stage_id', update_data["stage_id"]).eq('exercise_id', update_data["exercise_id"]).execute()
                print("✅ [INIT] Learning unlock records updated.")
            
            if not unlocks_to_create and not unlocks_to_update:
                print("✅ [INIT] No learning unlock records needed.")

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
            
            if not (0 <= stage_id <= 6):
                raise ValueError(f"Invalid stage_id: {stage_id}. Must be between 0 and 6")
            
            if not (1 <= exercise_id <= 5) and stage_id == 0: # Stage 0 has 5 lessons
                 raise ValueError(f"Invalid exercise_id for Stage 0: {exercise_id}. Must be between 1 and 5")
            elif not (1 <= exercise_id <= 3) and stage_id > 0:
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
            await self._update_exercise_progress(user_id, stage_id, exercise_id, score, urdu_used, time_spent_seconds, topic_id, completed)
            
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
                                      score: float, urdu_used: bool, time_spent_seconds: int, 
                                      topic_id: int, completed: bool):
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
                
                # The topic_id passed to this function IS the topic_number.
                # No need to query the database for it again.
                topic_number = topic_id if topic_id is not None else 1
                
                # Determine initial topic_id based on completion
                next_topic_id = topic_number
                # Use different thresholds for different exercises
                if exercise_id == 3:  # Problem-solving exercise
                    if score >= 60:
                        # If topic was completed successfully, start with next topic
                        next_topic_id = topic_number + 1
                else:
                    if score >= 80:
                        # If topic was completed successfully, start with next topic
                        next_topic_id = topic_number + 1
                
                new_exercise_data = {
                    "user_id": user_id,
                    "stage_id": stage_id,
                    "exercise_id": exercise_id,
                    "current_topic_id": next_topic_id,
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
            
            # --- BEGIN FIX: Correct Exercise Completion Logic ---
            # An exercise is complete only when ALL of its topics are marked as complete.
            # The old logic of using 3 consecutive high scores was incorrect.
            # This is now passed directly as the 'completed' parameter.
            # If completed is True, it means the exercise is marked as completed.
            # If completed is False, it means the exercise is not completed.
            # The logic below is no longer needed as completion is handled by the 'completed' parameter.
            # --- END FIX ---
            
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
            
            # The topic_id passed in is the topic_number, so we use it directly.
            topic_number = topic_id if topic_id is not None else 1
            
            # Check if this topic was completed successfully
            # This is now passed directly as the 'completed' parameter
            topic_completed = completed
            
            if topic_completed and topic_number >= current_topic_id:
                # Increment topic_id for next topic when current topic is completed
                next_topic_id = topic_number + 1
                update_data["current_topic_id"] = next_topic_id
                print(f"🎉 [EXERCISE] Topic {topic_number} completed! Moving to topic {next_topic_id}")
            elif topic_id and topic_number > current_topic_id:
                # Update topic_id if user is working on a higher topic
                update_data["current_topic_id"] = topic_number
                print(f"📝 [EXERCISE] Updated current_topic_id to {topic_number}")
            
            # Check if exercise is completed (based on the new logic)
            # This is now passed directly as the 'completed' parameter
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
            summary_res = self.client.table('ai_tutor_user_progress_summary').select('*').eq('user_id', user_id).execute()
            summary = summary_res.data[0] if summary_res.data else {}
            print(f"📊 [GET] Initial progress summary from DB: {summary}")

            # Always calculate fresh statistics to ensure data is up-to-date
            print(f"🔄 [GET] Recalculating latest statistics for user {user_id}...")
            current_date = date.today()
            
            # Calculate all-time total learning time from the source of truth
            total_time = await self._calculate_total_learning_time(user_id)
            summary['total_time_spent_minutes'] = total_time

            # Calculate streak
            current_streak, longest_streak = await self._calculate_streak(user_id, current_date)
            summary['streak_days'] = current_streak
            summary['longest_streak'] = max(summary.get('longest_streak', 0), longest_streak)
            
            # Calculate session metrics (30-day window)
            session_metrics = await self._calculate_session_metrics(user_id)
            summary.update(session_metrics)
            
            # --- BEGIN FIX: Recalculate current_stage from exercise completion data ---
            print(f"🔄 [GET] Recalculating current stage from exercise completion data for user {user_id}...")
            try:
                # Get all exercises for this user with a completion date
                user_exercises_res = self.client.table('ai_tutor_user_exercise_progress').select('stage_id, exercise_id, completed_at').eq('user_id', user_id).not_.is_('completed_at', 'null').execute()
                
                if user_exercises_res.data:
                    completed_exercises = user_exercises_res.data
                    
                    # Group completed exercises by stage
                    completed_by_stage = {}
                    for ex in completed_exercises:
                        stage_id = ex['stage_id']
                        if stage_id not in completed_by_stage:
                            completed_by_stage[stage_id] = set()
                        completed_by_stage[stage_id].add(ex['exercise_id'])
                        
                    # Get all stage definitions with exercise counts
                    all_stages_defs = await self.get_all_stages()
                    if all_stages_defs:
                        highest_completed_stage = -1
                        sorted_stages = sorted(all_stages_defs, key=lambda s: s['stage_number'])
                        
                        for stage_def in sorted_stages:
                            stage_num = stage_def['stage_number']
                            total_exercises_in_stage = stage_def.get('exercise_count', 0)
                            
                            if total_exercises_in_stage > 0:
                                completed_in_stage = len(completed_by_stage.get(stage_num, set()))
                                if completed_in_stage >= total_exercises_in_stage:
                                    # This stage is complete
                                    highest_completed_stage = max(highest_completed_stage, stage_num)
                        
                        # Current stage is the one after the highest completed one
                        recalculated_current_stage = highest_completed_stage + 1
                        
                        # Cap at max stage number
                        max_stage_num = sorted_stages[-1]['stage_number']
                        recalculated_current_stage = min(recalculated_current_stage, max_stage_num)

                        print(f"📊 [GET] Recalculated current stage is: {recalculated_current_stage}. DB summary value was: {summary.get('current_stage')}")
                        summary['current_stage'] = recalculated_current_stage
            except Exception as e:
                print(f"❌ [GET] Error recalculating current stage: {str(e)}. Using value from summary.")
            # --- END FIX ---
            
            print(f"📊 [GET] Final updated summary with fresh stats: {summary}")
            
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
                "summary": summary,
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
    
    async def get_topics_for_exercise(self, stage_id: int, exercise_id: int) -> dict:
        """Get all topics for a specific exercise"""
        print(f"🔍 [TOPICS] Getting topics for stage {stage_id}, exercise {exercise_id}")
        try:
            # This is a simplified implementation - you may need to adjust based on your database structure
            # For now, we'll return a basic structure
            return {
                "success": True,
                "data": [
                    {"topic_id": i} for i in range(1, 11)  # Assuming 10 topics per exercise
                ]
            }
        except Exception as e:
            print(f"❌ [TOPICS] Error getting topics: {str(e)}")
            return {"success": False, "error": str(e)}

    async def get_current_topic_for_exercise(self, user_id: str, stage_id: int, exercise_id: int) -> dict:
        """Get the current topic_id for a specific exercise"""
        print(f"🔄 [TOPIC] Getting current topic for user {user_id}, stage {stage_id}, exercise {exercise_id}")
        try:
            # Validate parameters
            if not user_id or not user_id.strip():
                raise ValueError("User ID is required")
            
            if not (0 <= stage_id <= 6):
                raise ValueError(f"Invalid stage_id: {stage_id}. Must be between 0 and 6")
            
            if not (1 <= exercise_id <= 5) and stage_id == 0: # Stage 0 has 5 lessons
                 raise ValueError(f"Invalid exercise_id for Stage 0: {exercise_id}. Must be between 1 and 5")
            elif not (1 <= exercise_id <= 3) and stage_id > 0:
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
            
            print(f"📊 [TOPIC] Current topic_id from DB: {current_topic_id}, Exercise completed: {is_completed}")

            # --- BEGIN FIX: Prevent out-of-bounds topic loading ---
            # Get the total number of topics for this exercise to prevent advancing beyond the last topic.
            try:
                topics_res = self.client.rpc('get_topics_for_exercise_full', {'stage_num': stage_id, 'exercise_num': exercise_id}).execute()
                total_topics = len(topics_res.data) if topics_res.data else 0
                print(f"📊 [TOPIC] Found {total_topics} total topics for this exercise.")

                if total_topics > 0 and current_topic_id > total_topics:
                    print(f"⚠️ [TOPIC] Correcting out-of-bounds topic ID. Was {current_topic_id}, now {total_topics}.")
                    current_topic_id = total_topics
                    # Update the database to fix the invalid state permanently
                    self.client.table('ai_tutor_user_exercise_progress').update(
                        {"current_topic_id": current_topic_id}
                    ).eq('user_id', user_id).eq('stage_id', stage_id).eq('exercise_id', exercise_id).execute()
            except Exception as e:
                print(f"❌ [TOPIC] Error getting total topics count: {str(e)}")
                total_topics = 0
            # --- END FIX ---
            
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
                        
                        # --- BEGIN FIX: Add safety check before advancing ---
                        if total_topics > 0 and next_topic_id > total_topics:
                            print(f"🎉 [TOPIC] User has completed the final topic ({current_topic_id}). Not advancing topic ID.")
                            # Do not increment the topic ID further. The exercise completion logic will handle marking the exercise as done.
                        else:
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
                        # --- END FIX ---
            
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

    async def _mark_stage_as_completed(self, user_id: str, stage_id: int):
        """Marks a stage as completed in the user_stage_progress table."""
        try:
            print(f"🔄 [STAGE_COMPLETE] Marking stage {stage_id} as complete for user {user_id}")
            current_timestamp = datetime.now().isoformat()
            
            exercises_in_stage = await self.get_exercises_for_stage(stage_id)
            
            stage_progress_payload = {
                "completed": True,
                "completed_at": current_timestamp,
                "progress_percentage": 100.0,
                "exercises_completed": len(exercises_in_stage)
            }
            
            self.client.table('ai_tutor_user_stage_progress').update(stage_progress_payload).eq('user_id', user_id).eq('stage_id', stage_id).execute()
            print(f"✅ [STAGE_COMPLETE] Stage {stage_id} marked as complete.")
        except Exception as e:
            print(f"❌ [STAGE_COMPLETE] Error marking stage {stage_id} as complete: {str(e)}")
            logger.error(f"Error marking stage {stage_id} as complete for user {user_id}: {str(e)}")
    
    async def complete_lesson(self, user_id: str, stage_id: int, exercise_id: int) -> dict:
        """
        Records the completion of a Stage 0 lesson by marking all its topics as complete.
        """
        print(f"🔄 [LESSON] Recording completion for user {user_id}, Stage {stage_id}, Lesson {exercise_id}")
        if stage_id != 0:
            return {"success": False, "error": "This function is only for Stage 0 lessons."}

        try:
            # Fetch all topics for the specified lesson (exercise)
            topics_result = self.client.rpc('get_topics_for_exercise_full', {'stage_num': stage_id, 'exercise_num': exercise_id}).execute()
            if not topics_result.data:
                logger.warning(f"No topics found for Stage {stage_id}, Exercise {exercise_id}. Cannot record completion.")
                return {"success": True, "message": "No topics found for this lesson, nothing to complete."}
            
            topics = topics_result.data
            print(f"📚 [LESSON] Found {len(topics)} topics to mark as complete for Lesson {exercise_id}.")

            # Create a list of tasks to run concurrently
            tasks = []
            for topic in topics:
                tasks.append(
                    self.record_topic_attempt(
                        user_id=user_id,
                        stage_id=stage_id,
                        exercise_id=exercise_id,
                        topic_id=topic['topic_number'],
                        score=100.0,
                        urdu_used=False,
                        time_spent_seconds=1, # Default value for instant completion
                        completed=True
                    )
                )

            # Run all topic recordings concurrently
            await asyncio.gather(*tasks)

            print(f"✅ [LESSON] Successfully recorded completion for Lesson {exercise_id} for user {user_id}")
            return {"success": True, "message": f"Lesson {exercise_id} completed."}

        except Exception as e:
            import traceback
            print(f"❌ [LESSON] Error completing lesson for {user_id}: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            logger.error(f"Error completing lesson for {user_id}: {str(e)}")
            return {"success": False, "error": str(e)}

    async def get_user_topic_progress_all(self, user_id: str) -> dict:
        """Get all topic progress for a user."""
        print(f"🔄 [TOPIC_PROGRESS] Getting all topic progress for user {user_id}")
        try:
            if not user_id or not user_id.strip():
                raise ValueError("User ID is required")
            
            result = self.client.table('ai_tutor_user_topic_progress').select('stage_id, exercise_id, topic_id, completed').eq('user_id', user_id).execute()
            
            print(f"📊 [TOPIC_PROGRESS] Found {len(result.data)} total topic records for user.")
            return {"success": True, "data": result.data}
            
        except Exception as e:
            print(f"❌ [TOPIC_PROGRESS] Error getting all topic progress: {str(e)}")
            logger.error(f"Error getting all topic progress for user {user_id}: {str(e)}")
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
            completed_exercises_res = self.client.table('ai_tutor_user_exercise_progress').select('*').eq('user_id', user_id).not_.is_('completed_at', 'null').execute()
            print(f"📊 [UNLOCK] Found {len(completed_exercises_res.data)} completed exercises")
            
            unlocked_content = []
            current_timestamp = datetime.now().isoformat()
            
            # Group completed exercises by stage for efficient processing
            completed_by_stage = {}
            for exercise in completed_exercises_res.data:
                stage_id = exercise['stage_id']
                if stage_id not in completed_by_stage:
                    completed_by_stage[stage_id] = []
                completed_by_stage[stage_id].append(exercise['exercise_id'])
            
            all_stages_list = await self.get_all_stages()
            if not all_stages_list:
                print("⚠️ [UNLOCK] Could not fetch stage list for unlocking logic.")
                return {"success": False, "error": "Could not fetch stages."}

            max_stage_num = max(s['stage_number'] for s in all_stages_list)

            for stage_id, completed_ids in completed_by_stage.items():
                print(f"🔍 [UNLOCK] Processing stage {stage_id} with completed exercises: {completed_ids}")
                
                all_exercises_in_stage = await self.get_exercises_for_stage(stage_id)
                if not all_exercises_in_stage:
                    continue

                all_exercise_nums = sorted([e['exercise_number'] for e in all_exercises_in_stage])
                
                # Check if all exercises in the current stage are completed
                if set(all_exercise_nums).issubset(set(completed_ids)):
                    # Mark the current stage as completed
                    await self._mark_stage_as_completed(user_id, stage_id)

                    # Unlock the next stage if it's not the final stage
                    if stage_id < max_stage_num:
                        next_stage_id = stage_id + 1
                        print(f"✅ [UNLOCK] All exercises in stage {stage_id} completed. Unlocking stage {next_stage_id}.")
                        
                        # Unlock the next stage itself
                        await self.unlock_stage_for_user(user_id, next_stage_id, f"Completed all exercises in stage {stage_id}", unlocked_content)
                        
                        # Unlock the first exercise of the next stage
                        await self.unlock_first_exercise_of_stage(user_id, next_stage_id, unlocked_content)

                        # --- BEGIN FIX: Update user's current stage AND unlocked stages list in the summary table ---
                        print(f"🔄 [UNLOCK] Updating user's summary: current stage to {next_stage_id} and adding to unlocked list.")
                        try:
                            # Fetch current summary to get unlocked_stages list
                            summary_res = self.client.table('ai_tutor_user_progress_summary').select('unlocked_stages').eq('user_id', user_id).single().execute()
                            
                            current_unlocked = summary_res.data.get('unlocked_stages', []) if summary_res.data else []
                            
                            # Add new stage if not already present
                            if next_stage_id not in current_unlocked:
                                current_unlocked.append(next_stage_id)
                            
                            self.client.table('ai_tutor_user_progress_summary').update({
                                'current_stage': next_stage_id,
                                'unlocked_stages': current_unlocked
                            }).eq('user_id', user_id).execute()
                            print(f"✅ [UNLOCK] Successfully updated summary for user {user_id}")
                        except Exception as e:
                            print(f"❌ [UNLOCK] Failed to update summary for user {user_id}: {str(e)}")
                            logger.error(f"Failed to update summary for user {user_id}: {str(e)}")
                        # --- END FIX ---

                # Unlock the next exercise WITHIN the current stage if applicable
                last_completed = max(completed_ids) if completed_ids else 0
                if last_completed in all_exercise_nums:
                    last_completed_index = all_exercise_nums.index(last_completed)
                    if last_completed_index < len(all_exercise_nums) - 1:
                        next_exercise_id = all_exercise_nums[last_completed_index + 1]
                        
                        existing_unlock = self.client.table('ai_tutor_learning_unlocks').select('is_unlocked').eq('user_id', user_id).eq('stage_id', stage_id).eq('exercise_id', next_exercise_id).execute()
                        
                        if not existing_unlock.data or not existing_unlock.data[0]['is_unlocked']:
                            print(f"🔓 [UNLOCK] Unlocking exercise {next_exercise_id} in stage {stage_id}")
                            unlock_data = {
                                "user_id": user_id,
                                "stage_id": stage_id,
                                "exercise_id": next_exercise_id,
                                "is_unlocked": True, "unlock_criteria_met": True, "unlocked_at": current_timestamp,
                                "unlocked_by_criteria": f"Completed exercise {last_completed} in stage {stage_id}"
                            }
                            # Use upsert to handle potential race conditions or existing locked rows
                            self.client.table('ai_tutor_learning_unlocks').upsert(unlock_data).execute()
                            unlocked_content.append(f"Stage {stage_id}, Exercise {next_exercise_id}")
            
            print(f"📊 [UNLOCK] Total unlocked content: {unlocked_content}")
            return {"success": True, "unlocked_content": list(set(unlocked_content))}
            
        except Exception as e:
            print(f"❌ [UNLOCK] Error checking content unlocks for {user_id}: {str(e)}")
            logger.error(f"Error checking content unlocks for {user_id}: {str(e)}")
            return {"success": False, "error": str(e)}

    async def get_all_stages_from_db(self) -> List[Dict]:
        """Fetches all stages from the content hierarchy for caching."""
        try:
            print("🔄 [DB CACHE] Fetching all stages for cache...")
            result = self.client.rpc('get_all_stages_with_counts').execute()
            if result.data:
                print(f"✅ [DB CACHE] Found {len(result.data)} stages.")
                return result.data
            return []
        except Exception as e:
            print(f"❌ [DB CACHE] Error fetching stages for cache: {str(e)}")
            logger.error(f"Error fetching stages for cache: {str(e)}")
            return []

    async def get_all_exercises_from_db(self) -> List[Dict]:
        """Fetches all exercises from the content hierarchy for caching."""
        try:
            print("🔄 [DB CACHE] Fetching all exercises for cache...")
            result = self.client.rpc('get_all_exercises_with_details').execute()
            if result.data:
                print(f"✅ [DB CACHE] Found {len(result.data)} exercises.")
                return result.data
            return []
        except Exception as e:
            print(f"❌ [DB CACHE] Error fetching exercises for cache: {str(e)}")
            logger.error(f"Error fetching exercises for cache: {str(e)}")
            return []

    async def unlock_stage_for_user(self, user_id: str, stage_id: int, unlock_reason: str, unlocked_content: List[str]):
        """Unlocks a specific stage for a user."""
        print(f"🔓 [UNLOCK] Unlocking stage {stage_id} for user {user_id} due to {unlock_reason}")
        try:
            existing_unlock = self.client.table('ai_tutor_learning_unlocks').select('is_unlocked').eq('user_id', user_id).eq('stage_id', stage_id).is_('exercise_id', None).execute()
            if not existing_unlock.data or not existing_unlock.data[0]['is_unlocked']:
                unlock_data = {
                    "user_id": user_id,
                    "stage_id": stage_id,
                    "exercise_id": None,
                    "is_unlocked": True, "unlock_criteria_met": True, "unlocked_at": datetime.now().isoformat(),
                    "unlocked_by_criteria": unlock_reason
                }
                self.client.table('ai_tutor_learning_unlocks').upsert(unlock_data).execute()
                unlocked_content.append(f"Stage {stage_id}")
                print(f"✅ [UNLOCK] Stage {stage_id} unlocked.")
            else:
                print(f"⚠️ [UNLOCK] Stage {stage_id} already unlocked.")
        except Exception as e:
            print(f"❌ [UNLOCK] Error unlocking stage {stage_id} for user {user_id}: {str(e)}")
            logger.error(f"Error unlocking stage {stage_id} for user {user_id}: {str(e)}")

    async def unlock_first_exercise_of_stage(self, user_id: str, stage_id: int, unlocked_content: List[str]):
        """Unlocks the first exercise of a specific stage for a user."""
        print(f"🔓 [UNLOCK] Unlocking first exercise of stage {stage_id} for user {user_id}")
        try:
            all_exercises_in_stage = await self.get_exercises_for_stage(stage_id)
            if not all_exercises_in_stage:
                print(f"⚠️ [UNLOCK] No exercises found for stage {stage_id} to unlock first exercise.")
                return

            first_exercise_id = sorted([e['exercise_number'] for e in all_exercises_in_stage])[0]
            existing_unlock = self.client.table('ai_tutor_learning_unlocks').select('is_unlocked').eq('user_id', user_id).eq('stage_id', stage_id).eq('exercise_id', first_exercise_id).execute()
            if not existing_unlock.data or not existing_unlock.data[0]['is_unlocked']:
                unlock_data = {
                    "user_id": user_id,
                    "stage_id": stage_id,
                    "exercise_id": first_exercise_id,
                    "is_unlocked": True, "unlock_criteria_met": True, "unlocked_at": datetime.now().isoformat(),
                    "unlocked_by_criteria": f"Unlocked stage {stage_id}"
                }
                self.client.table('ai_tutor_learning_unlocks').upsert(unlock_data).execute()
                unlocked_content.append(f"Stage {stage_id}, Exercise {first_exercise_id}")
                print(f"✅ [UNLOCK] First exercise of stage {stage_id} unlocked.")
            else:
                print(f"⚠️ [UNLOCK] First exercise of stage {stage_id} already unlocked.")
        except Exception as e:
            print(f"❌ [UNLOCK] Error unlocking first exercise of stage {stage_id} for user {user_id}: {str(e)}")
            logger.error(f"Error unlocking first exercise of stage {stage_id} for user {user_id}: {str(e)}")

# Global instance
progress_tracker = SupabaseProgressTracker() 