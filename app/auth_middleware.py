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
                user_data = {
                    "id": result.user.id,
                    "email": result.user.email,
                    "role": result.user.user_metadata.get("role", "student"),
                    "first_name": result.user.user_metadata.get("first_name", ""),
                    "last_name": result.user.user_metadata.get("last_name", ""),
                    "grade": result.user.user_metadata.get("grade", "")
                }
                logger.info(f"Token verified for user: {user_data['email']}")
                return user_data
            else:
                logger.error("Invalid token: No user found")
                raise HTTPException(status_code=401, detail="Invalid token")
                
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

def require_role(required_role: str):
    """
    Decorator to require specific user role
    
    Args:
        required_role: Required role (e.g., "student", "teacher", "admin")
    """
    def role_checker(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        if user.get("role") != required_role:
            raise HTTPException(status_code=403, detail=f"Role '{required_role}' required")
        return user
    return role_checker

# Role-specific dependencies
require_student = require_role("student")
require_teacher = require_role("teacher")
require_admin = require_role("admin") 