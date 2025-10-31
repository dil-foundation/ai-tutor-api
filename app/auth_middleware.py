"""
Authentication Middleware for AI Tutor Backend

This module provides authentication and authorization middleware for the FastAPI application.
It validates JWT tokens from Supabase and ensures proper user authentication.
"""

import os
import jwt
import logging
from typing import Optional, Dict, Any
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Configure logging
logger = logging.getLogger(__name__)

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    logger.error("Missing Supabase environment variables")
    raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")

# Create Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Security scheme
security = HTTPBearer()

class AuthMiddleware:
    """Authentication middleware for validating JWT tokens and user sessions"""
    
    def __init__(self):
        self.supabase = supabase
        logger.info("AuthMiddleware initialized")
    
    async def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify JWT token and return user information
        
        Args:
            token: JWT token from request header
            
        Returns:
            Dict containing user information if token is valid
            
        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            logger.info("Verifying JWT token")
            
            # Verify token with Supabase
            result = self.supabase.auth.get_user(token)
            
            if result.user:
                user_id = result.user.id
                user_email = result.user.email
                user_metadata = result.user.user_metadata or {}

                # 🚫 BLOCK DELETED ACCOUNTS from JWT metadata - Simpler and Faster
                if user_metadata.get("account_deleted", False):
                    logger.warning(f"Access denied - account is deleted (from JWT): {user_email}")
                    raise HTTPException(
                        status_code=403, 
                        detail="Account has been deleted. Please contact support if you believe this is an error."
                    )
                
                # We can now trust the JWT and a separate profile query isn't needed for this check.
                # We still query the profile to get the most up-to-date role, grade, etc.
                try:
                    profile_response = self.supabase.table('profiles').select('role, grade, first_name, last_name').eq('id', user_id).single().execute()
                    
                    if profile_response.data:
                        profile = profile_response.data
                        # Normalize role to handle case sensitivity
                        raw_role = profile.get("role", "student")
                        
                        user_data = {
                            "id": user_id,
                            "email": user_email,
                            "role": raw_role,  # Keep original for display, normalization happens in checks
                            "first_name": profile.get("first_name", ""),
                            "last_name": profile.get("last_name", ""),
                            "grade": profile.get("grade", ""),
                            "is_deleted": False,  # Fixed: should be False if not deleted
                            "deleted_at": user_metadata.get("deleted_at")
                        }
                    else:
                        # Fallback to user metadata if no profile found
                        raw_role = user_metadata.get("role", "student")
                        
                        user_data = {
                            "id": user_id,
                            "email": user_email,
                            "role": raw_role,  # Keep original for display
                            "first_name": user_metadata.get("first_name", ""),
                            "last_name": user_metadata.get("last_name", ""),
                            "grade": user_metadata.get("grade", ""),
                            "is_deleted": user_metadata.get("account_deleted", False),
                            "deleted_at": user_metadata.get("deleted_at")
                        }
                        
                except HTTPException:
                    # Re-raise the exception to ensure it's not caught by the general catch-all
                    raise
                except Exception as profile_error:
                    logger.warning(f"Error checking profile for {user_email}: {str(profile_error)}")
                    # Fallback to user metadata if profile check fails
                    raw_role = user_metadata.get("role", "student")
                    
                    user_data = {
                        "id": user_id,
                        "email": user_email,
                        "role": raw_role,  # Keep original for display
                        "first_name": user_metadata.get("first_name", ""),
                        "last_name": user_metadata.get("last_name", ""),
                        "grade": user_metadata.get("grade", ""),
                        "is_deleted": user_metadata.get("account_deleted", False),
                        "deleted_at": user_metadata.get("deleted_at")
                    }
                
                logger.info(f"Token verified for user: {user_data['email']}")
                return user_data
            else:
                logger.error("Invalid token: No user found")
                raise HTTPException(status_code=401, detail="Invalid token")
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Token verification failed: {str(e)}")
            raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    async def get_current_user(self, credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
        """
        Dependency function to get current authenticated user
        
        Args:
            credentials: HTTP authorization credentials from request header
            
        Returns:
            Dict containing user information
            
        Raises:
            HTTPException: If authentication fails
        """
        try:
            token = credentials.credentials
            user_data = await self.verify_token(token)
            return user_data
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            raise HTTPException(status_code=401, detail="Authentication required")
    
    async def require_auth(self, request: Request) -> Dict[str, Any]:
        """
        Middleware function to require authentication for routes
        
        Args:
            request: FastAPI request object
            
        Returns:
            Dict containing user information
            
        Raises:
            HTTPException: If authentication fails
        """
        try:
            # Get authorization header
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                raise HTTPException(status_code=401, detail="Authorization header required")
            
            # Extract token
            if not auth_header.startswith("Bearer "):
                raise HTTPException(status_code=401, detail="Bearer token required")
            
            token = auth_header.split(" ")[1]
            user_data = await self.verify_token(token)
            return user_data
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Authentication middleware error: {str(e)}")
            raise HTTPException(status_code=401, detail="Authentication failed")

# Global instance
auth_middleware = AuthMiddleware()

# Dependency functions for use in routes
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Dependency function to get current authenticated user"""
    return await auth_middleware.get_current_user(credentials)

async def require_auth(request: Request) -> Dict[str, Any]:
    """Dependency function to require authentication"""
    return await auth_middleware.require_auth(request)

def _normalize_role(role: str) -> str:
    """Normalize role string to handle case sensitivity and variations"""
    if not role:
        return ""
    return role.lower().strip()

def _has_admin_privileges(role: str) -> bool:
    """Check if role has admin privileges (admin or super_user)"""
    normalized_role = _normalize_role(role)
    return normalized_role in ["admin", "super_user", "superuser"]

def _has_teacher_privileges(role: str) -> bool:
    """Check if role has teacher privileges (teacher, admin, or super_user)"""
    normalized_role = _normalize_role(role)
    return normalized_role in ["teacher", "admin", "super_user", "superuser"]

def require_role(required_role: str):
    """
    Decorator to require specific user role
    
    Args:
        required_role: Required role (e.g., "student", "teacher", "admin")
    """
    def role_checker(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        user_role = _normalize_role(user.get("role", ""))
        required_role_normalized = _normalize_role(required_role)
        
        # Special handling: super_user should have access to admin and teacher roles
        if required_role_normalized == "admin" and _has_admin_privileges(user.get("role", "")):
            return user
        if required_role_normalized == "teacher" and _has_teacher_privileges(user.get("role", "")):
            return user
        
        if user_role != required_role_normalized:
            raise HTTPException(status_code=403, detail=f"Role '{required_role}' required. Current role: {user.get('role')}")
        return user
    return role_checker

def require_any_role(allowed_roles: list):
    """
    Decorator to require any of the specified user roles
    
    Args:
        allowed_roles: List of allowed roles (e.g., ["admin", "teacher"])
    """
    def role_checker(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        user_role = _normalize_role(user.get("role", ""))
        allowed_roles_normalized = [_normalize_role(role) for role in allowed_roles]
        
        # Special handling: super_user should have access to admin and teacher endpoints
        if "admin" in allowed_roles_normalized and _has_admin_privileges(user.get("role", "")):
            return user
        if "teacher" in allowed_roles_normalized and _has_teacher_privileges(user.get("role", "")):
            return user
        
        if user_role not in allowed_roles_normalized:
            raise HTTPException(
                status_code=403, 
                detail=f"One of the following roles required: {', '.join(allowed_roles)}. Current role: {user.get('role')}"
            )
        return user
    return role_checker

# Role-specific dependencies
require_student = require_role("student")
require_teacher = require_role("teacher")
require_admin = require_role("admin")  # super_user will have access via _has_admin_privileges check
require_super_user = require_role("super_user")

# Helper function to check if user has admin privileges (including super_user)
def has_admin_access(user: Dict[str, Any]) -> bool:
    """Check if user has admin-level access (admin or super_user)"""
    return _has_admin_privileges(user.get("role", ""))

# Helper function to check if user has teacher privileges (including admin and super_user)
def has_teacher_access(user: Dict[str, Any]) -> bool:
    """Check if user has teacher-level access (teacher, admin, or super_user)"""
    return _has_teacher_privileges(user.get("role", ""))

# Admin or teacher access - super_user included automatically
require_admin_or_teacher = require_any_role(["admin", "teacher", "super_user"]) 

# Admin, teacher, student, or super_user access
require_admin_or_teacher_or_student = require_any_role(["admin", "teacher", "student", "super_user"])