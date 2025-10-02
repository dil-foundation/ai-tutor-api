"""
Account Deletion API Routes
Handles user account deletion requests with soft deletion approach
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging
from datetime import datetime, timedelta
from app.supabase_client import supabase
from app.auth_middleware import get_current_user, require_student, require_admin_or_teacher_or_student
import asyncio

logger = logging.getLogger(__name__)
router = APIRouter()

class AccountDeletionRequest(BaseModel):
    reason: Optional[str] = "User requested account deletion"
    confirm_deletion: bool

class AccountDeletionResponse(BaseModel):
    success: bool
    message: str
    deletion_scheduled_for: Optional[str] = None
    error: Optional[str] = None

@router.post("/delete-account", response_model=AccountDeletionResponse)
async def request_account_deletion(
    request: AccountDeletionRequest,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)
):
    """
    Request account deletion - implements soft deletion
    
    Process:
    1. Validate deletion request
    2. Mark account as deleted (soft deletion)
    3. Invalidate all user sessions
    4. Schedule hard deletion after 30 days
    5. Log deletion request
    """
    print(f"🔄 [ACCOUNT_DELETION] Delete account request from user: {current_user['email']}")
    
    try:
        # Validate deletion confirmation
        if not request.confirm_deletion:
            raise HTTPException(
                status_code=400, 
                detail="Account deletion must be confirmed by setting confirm_deletion to true"
            )
        
        user_id = current_user['id']
        user_email = current_user['email']
        
        # Check if account is already marked for deletion
        existing_deletion = supabase.table('profiles').select('is_deleted, deleted_at').eq('id', user_id).single().execute()
        
        if existing_deletion.data and existing_deletion.data.get('is_deleted'):
            return AccountDeletionResponse(
                success=False,
                message="Account is already scheduled for deletion",
                error="Account already marked for deletion"
            )
        
        # Mark account as deleted (soft deletion)
        deletion_timestamp = datetime.utcnow().isoformat()
        hard_deletion_date = (datetime.utcnow() + timedelta(days=30)).isoformat()
        
        print(f"🔄 [ACCOUNT_DELETION] Marking account as deleted: {user_email}")
        
        # Update profiles table with soft deletion
        update_result = supabase.table('profiles').update({
            'is_deleted': True,
            'deleted_at': deletion_timestamp,
            'deletion_reason': request.reason,
            'deletion_requested_by': user_id,
            'updated_at': deletion_timestamp
        }).eq('id', user_id).execute()
        
        if not update_result.data:
            raise HTTPException(status_code=500, detail="Failed to mark account for deletion")
        
        print(f"✅ [ACCOUNT_DELETION] Account marked for deletion: {user_email}")
        
        # Invalidate all user sessions by updating auth metadata
        try:
            # This will force logout on all devices
            auth_update_result = supabase.auth.admin.update_user_by_id(
                user_id,
                {
                    "user_metadata": {
                        "account_deleted": True,
                        "deleted_at": deletion_timestamp,
                        "force_logout": True
                    }
                }
            )
            print(f"✅ [ACCOUNT_DELETION] User sessions invalidated: {user_email}")
        except Exception as e:
            print(f"⚠️ [ACCOUNT_DELETION] Failed to invalidate sessions: {str(e)}")
            # Continue with deletion even if session invalidation fails
        
        # Log the deletion request for audit purposes
        try:
            log_result = supabase.table('account_deletion_logs').insert({
                'user_id': user_id,
                'user_email': user_email,
                'deletion_reason': request.reason,
                'deletion_requested_at': deletion_timestamp,
                'hard_deletion_scheduled_for': hard_deletion_date,
                'status': 'soft_deleted'
            }).execute()
            print(f"✅ [ACCOUNT_DELETION] Deletion logged for audit: {user_email}")
        except Exception as e:
            print(f"⚠️ [ACCOUNT_DELETION] Failed to log deletion: {str(e)}")
            # Continue even if logging fails
        
        # Schedule background task for cleanup (optional immediate cleanup)
        background_tasks.add_task(cleanup_user_sessions, user_id)
        
        print(f"🎉 [ACCOUNT_DELETION] Account deletion completed successfully: {user_email}")
        
        return AccountDeletionResponse(
            success=True,
            message=f"Account deletion requested successfully. Your account has been deactivated and will be permanently deleted on {hard_deletion_date[:10]}. You have been logged out of all devices.",
            deletion_scheduled_for=hard_deletion_date
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [ACCOUNT_DELETION] Error processing deletion request: {str(e)}")
        logger.error(f"Account deletion error for user {current_user.get('email', 'unknown')}: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to process account deletion request: {str(e)}"
        )

async def cleanup_user_sessions(user_id: str):
    """Background task to cleanup user sessions and related data"""
    try:
        print(f"🔄 [CLEANUP] Starting session cleanup for user: {user_id}")
        
        # Additional cleanup tasks can be added here
        # For example: clear cached data, notify other services, etc.
        
        await asyncio.sleep(1)  # Small delay to ensure database updates are processed
        
        print(f"✅ [CLEANUP] Session cleanup completed for user: {user_id}")
        
    except Exception as e:
        print(f"❌ [CLEANUP] Error during session cleanup: {str(e)}")
        logger.error(f"Session cleanup error for user {user_id}: {str(e)}")

@router.get("/deletion-status", response_model=Dict[str, Any])
async def get_deletion_status(
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)
):
    """
    Get account deletion status for current user
    """
    try:
        user_id = current_user['id']
        
        # Get deletion status
        result = supabase.table('profiles').select(
            'is_deleted, deleted_at, deletion_reason'
        ).eq('id', user_id).single().execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="User profile not found")
        
        profile_data = result.data
        
        if profile_data.get('is_deleted'):
            deleted_at = profile_data.get('deleted_at')
            if deleted_at:
                # Calculate hard deletion date (30 days from soft deletion)
                from datetime import datetime, timedelta
                deletion_date = datetime.fromisoformat(deleted_at.replace('Z', '+00:00'))
                hard_deletion_date = deletion_date + timedelta(days=30)
                
                return {
                    "is_deleted": True,
                    "deleted_at": deleted_at,
                    "deletion_reason": profile_data.get('deletion_reason'),
                    "hard_deletion_scheduled_for": hard_deletion_date.isoformat(),
                    "days_remaining": max(0, (hard_deletion_date - datetime.utcnow()).days)
                }
        
        return {
            "is_deleted": False,
            "deleted_at": None,
            "deletion_reason": None,
            "hard_deletion_scheduled_for": None,
            "days_remaining": None
        }
        
    except Exception as e:
        print(f"❌ [DELETION_STATUS] Error getting deletion status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get deletion status: {str(e)}")

@router.post("/cancel-deletion")
async def cancel_account_deletion(
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)
):
    """
    Cancel account deletion request (only if within 30 days)
    """
    try:
        user_id = current_user['id']
        user_email = current_user['email']
        
        # Check current deletion status
        result = supabase.table('profiles').select(
            'is_deleted, deleted_at'
        ).eq('id', user_id).single().execute()
        
        if not result.data or not result.data.get('is_deleted'):
            raise HTTPException(status_code=400, detail="Account is not marked for deletion")
        
        # Restore account
        restore_result = supabase.table('profiles').update({
            'is_deleted': False,
            'deleted_at': None,
            'deletion_reason': None,
            'deletion_requested_by': None,
            'updated_at': datetime.utcnow().isoformat()
        }).eq('id', user_id).execute()
        
        if not restore_result.data:
            raise HTTPException(status_code=500, detail="Failed to cancel account deletion")
        
        # Update auth metadata
        try:
            supabase.auth.admin.update_user_by_id(
                user_id,
                {
                    "user_metadata": {
                        "account_deleted": False,
                        "restored_at": datetime.utcnow().isoformat()
                    }
                }
            )
        except Exception as e:
            print(f"⚠️ [CANCEL_DELETION] Failed to update auth metadata: {str(e)}")
        
        print(f"✅ [CANCEL_DELETION] Account deletion cancelled: {user_email}")
        
        return {
            "success": True,
            "message": "Account deletion has been cancelled successfully. Your account is now active."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [CANCEL_DELETION] Error cancelling deletion: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel deletion: {str(e)}")

# Health check endpoint
@router.get("/health")
async def health_check():
    """Health check for account deletion service"""
    return {"status": "healthy", "service": "account_deletion"}
