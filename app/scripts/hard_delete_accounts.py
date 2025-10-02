#!/usr/bin/env python3
"""
Hard Account Deletion Script
Permanently deletes accounts that have been soft-deleted for 30+ days

This script should be run as a cron job daily to clean up expired accounts.
Usage: python hard_delete_accounts.py [--dry-run] [--days=30]
"""

import os
import sys
import argparse
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
import asyncio

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.supabase_client import supabase
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('hard_deletion.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class HardDeletionManager:
    """Manages hard deletion of expired soft-deleted accounts"""
    
    def __init__(self, dry_run: bool = False, expiry_days: int = 30):
        self.dry_run = dry_run
        self.expiry_days = expiry_days
        self.client = supabase
        
        logger.info(f"🔧 [HARD_DELETE] Initialized with dry_run={dry_run}, expiry_days={expiry_days}")
    
    async def get_expired_accounts(self) -> List[Dict[str, Any]]:
        """Get accounts that have been soft-deleted for more than expiry_days"""
        try:
            # Calculate the cutoff date
            cutoff_date = datetime.utcnow() - timedelta(days=self.expiry_days)
            cutoff_iso = cutoff_date.isoformat()
            
            logger.info(f"🔍 [HARD_DELETE] Looking for accounts deleted before: {cutoff_iso}")
            
            # Query soft-deleted accounts older than cutoff date
            result = self.client.table('profiles').select(
                'id, email, deleted_at, deletion_reason'
            ).eq('is_deleted', True).lt('deleted_at', cutoff_iso).execute()
            
            expired_accounts = result.data or []
            logger.info(f"📊 [HARD_DELETE] Found {len(expired_accounts)} expired accounts")
            
            return expired_accounts
            
        except Exception as e:
            logger.error(f"❌ [HARD_DELETE] Error fetching expired accounts: {str(e)}")
            return []
    
    async def hard_delete_user_data(self, user_id: str, user_email: str) -> bool:
        """Permanently delete all user data from all tables"""
        try:
            logger.info(f"🗑️ [HARD_DELETE] Starting hard deletion for user: {user_email}")
            
            if self.dry_run:
                logger.info(f"🔍 [DRY_RUN] Would delete all data for user: {user_email}")
                return True
            
            # List of tables to clean up (in order of dependencies)
            tables_to_clean = [
                'ai_tutor_user_topic_progress',
                'ai_tutor_user_exercise_progress', 
                'ai_tutor_user_stage_progress',
                'ai_tutor_learning_unlocks',
                'ai_tutor_learning_milestones',
                'ai_tutor_daily_learning_analytics',
                'ai_tutor_weekly_progress_summaries',
                'ai_tutor_user_progress_summary',
                'account_deletion_logs',
                'profiles'  # Delete profile last
            ]
            
            deleted_counts = {}
            
            # Delete from each table
            for table_name in tables_to_clean:
                try:
                    logger.info(f"🗑️ [HARD_DELETE] Deleting from table: {table_name}")
                    
                    # Delete records for this user
                    delete_result = self.client.table(table_name).delete().eq('user_id', user_id).execute()
                    
                    deleted_count = len(delete_result.data) if delete_result.data else 0
                    deleted_counts[table_name] = deleted_count
                    
                    logger.info(f"✅ [HARD_DELETE] Deleted {deleted_count} records from {table_name}")
                    
                except Exception as table_error:
                    logger.error(f"❌ [HARD_DELETE] Error deleting from {table_name}: {str(table_error)}")
                    # Continue with other tables even if one fails
                    deleted_counts[table_name] = 0
            
            # Delete from Supabase Auth (this will cascade to related auth tables)
            try:
                logger.info(f"🗑️ [HARD_DELETE] Deleting from Supabase Auth: {user_email}")
                auth_delete_result = self.client.auth.admin.delete_user(user_id)
                logger.info(f"✅ [HARD_DELETE] Deleted from Supabase Auth: {user_email}")
            except Exception as auth_error:
                logger.error(f"❌ [HARD_DELETE] Error deleting from auth: {str(auth_error)}")
            
            # Log the hard deletion
            try:
                self.client.table('account_deletion_logs').update({
                    'status': 'hard_deleted',
                    'hard_deletion_completed_at': datetime.utcnow().isoformat(),
                    'updated_at': datetime.utcnow().isoformat()
                }).eq('user_id', user_id).execute()
                
                logger.info(f"✅ [HARD_DELETE] Updated deletion log for: {user_email}")
            except Exception as log_error:
                logger.error(f"❌ [HARD_DELETE] Error updating deletion log: {str(log_error)}")
            
            # Summary
            total_deleted = sum(deleted_counts.values())
            logger.info(f"🎉 [HARD_DELETE] Hard deletion completed for {user_email}")
            logger.info(f"📊 [HARD_DELETE] Total records deleted: {total_deleted}")
            logger.info(f"📊 [HARD_DELETE] Breakdown: {deleted_counts}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ [HARD_DELETE] Hard deletion failed for {user_email}: {str(e)}")
            return False
    
    async def run_hard_deletion(self) -> Dict[str, Any]:
        """Run the hard deletion process"""
        start_time = datetime.utcnow()
        logger.info(f"🚀 [HARD_DELETE] Starting hard deletion process at {start_time}")
        
        try:
            # Get expired accounts
            expired_accounts = await self.get_expired_accounts()
            
            if not expired_accounts:
                logger.info("ℹ️ [HARD_DELETE] No expired accounts found")
                return {
                    "success": True,
                    "processed": 0,
                    "deleted": 0,
                    "failed": 0,
                    "message": "No expired accounts found"
                }
            
            processed = 0
            deleted = 0
            failed = 0
            
            # Process each expired account
            for account in expired_accounts:
                user_id = account['id']
                user_email = account['email']
                deleted_at = account['deleted_at']
                
                logger.info(f"🔄 [HARD_DELETE] Processing account: {user_email} (deleted: {deleted_at})")
                
                processed += 1
                
                # Perform hard deletion
                success = await self.hard_delete_user_data(user_id, user_email)
                
                if success:
                    deleted += 1
                    logger.info(f"✅ [HARD_DELETE] Successfully deleted: {user_email}")
                else:
                    failed += 1
                    logger.error(f"❌ [HARD_DELETE] Failed to delete: {user_email}")
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            logger.info(f"🎉 [HARD_DELETE] Hard deletion process completed")
            logger.info(f"📊 [HARD_DELETE] Summary:")
            logger.info(f"   - Processed: {processed}")
            logger.info(f"   - Successfully deleted: {deleted}")
            logger.info(f"   - Failed: {failed}")
            logger.info(f"   - Duration: {duration:.2f} seconds")
            
            return {
                "success": True,
                "processed": processed,
                "deleted": deleted,
                "failed": failed,
                "duration_seconds": duration,
                "message": f"Hard deletion completed. Processed {processed} accounts, deleted {deleted}, failed {failed}"
            }
            
        except Exception as e:
            logger.error(f"❌ [HARD_DELETE] Hard deletion process failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "Hard deletion process failed"
            }

async def main():
    """Main function to run the hard deletion script"""
    parser = argparse.ArgumentParser(description='Hard delete expired soft-deleted accounts')
    parser.add_argument('--dry-run', action='store_true', help='Run in dry-run mode (no actual deletion)')
    parser.add_argument('--days', type=int, default=30, help='Number of days after soft deletion to hard delete (default: 30)')
    
    args = parser.parse_args()
    
    logger.info(f"🚀 [MAIN] Starting hard deletion script")
    logger.info(f"🔧 [MAIN] Configuration: dry_run={args.dry_run}, days={args.days}")
    
    # Create deletion manager
    deletion_manager = HardDeletionManager(dry_run=args.dry_run, expiry_days=args.days)
    
    # Run hard deletion
    result = await deletion_manager.run_hard_deletion()
    
    if result["success"]:
        logger.info(f"✅ [MAIN] Script completed successfully: {result['message']}")
        sys.exit(0)
    else:
        logger.error(f"❌ [MAIN] Script failed: {result['message']}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
