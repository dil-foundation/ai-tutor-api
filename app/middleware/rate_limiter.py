"""
Rate Limiting Middleware for Messaging System

This module provides rate limiting functionality to prevent spam and abuse
in the messaging system. It uses Redis for distributed rate limiting.
"""

import time
import asyncio
from typing import Dict, Optional, Callable
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
import redis.asyncio as redis
import json
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class RateLimiter:
    """Rate limiter using Redis for distributed rate limiting"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        
        # Rate limit configurations
        self.limits = {
            'message_send': {'requests': 10, 'window': 60},  # 10 messages per minute
            'conversation_create': {'requests': 5, 'window': 300},  # 5 conversations per 5 minutes
            'file_upload': {'requests': 3, 'window': 60},  # 3 files per minute
            'websocket_connect': {'requests': 10, 'window': 60},  # 10 connections per minute
            'api_general': {'requests': 100, 'window': 60},  # 100 API calls per minute
        }
    
    async def is_rate_limited(self, key: str, limit_type: str) -> tuple[bool, Dict]:
        """
        Check if request is rate limited
        
        Args:
            key: Unique identifier (usually user_id or IP)
            limit_type: Type of rate limit to apply
            
        Returns:
            tuple: (is_limited, rate_limit_info)
        """
        if limit_type not in self.limits:
            return False, {}
        
        limit_config = self.limits[limit_type]
        current_time = int(time.time())
        window_start = current_time - limit_config['window']
        
        # Create Redis key
        redis_key = f"rate_limit:{limit_type}:{key}"
        
        try:
            # Get current requests in window
            async with self.redis.pipeline() as pipe:
                # Remove old entries
                await pipe.zremrangebyscore(redis_key, 0, window_start)
                # Add current request
                await pipe.zadd(redis_key, {str(current_time): current_time})
                # Set expiry
                await pipe.expire(redis_key, limit_config['window'])
                # Get count
                await pipe.zcard(redis_key)
                results = await pipe.execute()
            
            current_count = results[3]  # zcard result
            is_limited = current_count > limit_config['requests']
            
            rate_limit_info = {
                'limit_type': limit_type,
                'current_count': current_count,
                'limit': limit_config['requests'],
                'window': limit_config['window'],
                'reset_time': current_time + limit_config['window'],
                'remaining': max(0, limit_config['requests'] - current_count)
            }
            
            return is_limited, rate_limit_info
            
        except Exception as e:
            logger.error(f"Rate limiting error: {str(e)}")
            # On Redis error, allow request but log
            return False, {}
    
    async def get_rate_limit_info(self, key: str, limit_type: str) -> Dict:
        """Get current rate limit information without incrementing"""
        if limit_type not in self.limits:
            return {}
        
        limit_config = self.limits[limit_type]
        current_time = int(time.time())
        window_start = current_time - limit_config['window']
        
        redis_key = f"rate_limit:{limit_type}:{key}"
        
        try:
            async with self.redis.pipeline() as pipe:
                await pipe.zremrangebyscore(redis_key, 0, window_start)
                await pipe.zcard(redis_key)
                results = await pipe.execute()
            
            current_count = results[1]  # zcard result
            
            return {
                'limit_type': limit_type,
                'current_count': current_count,
                'limit': limit_config['requests'],
                'window': limit_config['window'],
                'reset_time': current_time + limit_config['window'],
                'remaining': max(0, limit_config['requests'] - current_count)
            }
            
        except Exception as e:
            logger.error(f"Rate limit info error: {str(e)}")
            return {}

class RateLimitMiddleware:
    """FastAPI middleware for rate limiting"""
    
    def __init__(self, redis_client: redis.Redis):
        self.rate_limiter = RateLimiter(redis_client)
    
    async def __call__(self, request: Request, call_next: Callable):
        """Process request with rate limiting"""
        
        # Get client identifier (user_id or IP)
        client_id = await self._get_client_id(request)
        
        # Determine rate limit type based on endpoint
        limit_type = self._get_limit_type(request)
        
        if limit_type:
            # Check rate limit
            is_limited, rate_limit_info = await self.rate_limiter.is_rate_limited(
                client_id, limit_type
            )
            
            if is_limited:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        'error': 'Rate limit exceeded',
                        'message': f'Too many {limit_type} requests',
                        'rate_limit_info': rate_limit_info,
                        'retry_after': rate_limit_info.get('reset_time', 0) - int(time.time())
                    },
                    headers={
                        'X-RateLimit-Limit': str(rate_limit_info.get('limit', 0)),
                        'X-RateLimit-Remaining': str(rate_limit_info.get('remaining', 0)),
                        'X-RateLimit-Reset': str(rate_limit_info.get('reset_time', 0)),
                        'Retry-After': str(rate_limit_info.get('reset_time', 0) - int(time.time()))
                    }
                )
            
            # Add rate limit headers to response
            response = await call_next(request)
            response.headers['X-RateLimit-Limit'] = str(rate_limit_info.get('limit', 0))
            response.headers['X-RateLimit-Remaining'] = str(rate_limit_info.get('remaining', 0))
            response.headers['X-RateLimit-Reset'] = str(rate_limit_info.get('reset_time', 0))
            return response
        
        return await call_next(request)
    
    async def _get_client_id(self, request: Request) -> str:
        """Get unique client identifier"""
        # Try to get user_id from token first
        try:
            # Extract token from query params or headers
            token = request.query_params.get('token') or request.headers.get('authorization', '').replace('Bearer ', '')
            if token:
                # In a real implementation, you'd decode the JWT to get user_id
                # For now, we'll use a hash of the token
                import hashlib
                return hashlib.md5(token.encode()).hexdigest()
        except Exception:
            pass
        
        # Fallback to IP address
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        return request.client.host if request.client else 'unknown'
    
    def _get_limit_type(self, request: Request) -> Optional[str]:
        """Determine rate limit type based on request path and method"""
        path = request.url.path
        method = request.method
        
        # Message sending
        if path.endswith('/messages') and method == 'POST':
            return 'message_send'
        
        # Conversation creation
        if path.endswith('/conversations') and method == 'POST':
            return 'conversation_create'
        
        # File upload
        if path.endswith('/upload') and method == 'POST':
            return 'file_upload'
        
        # WebSocket connections
        if path.startswith('/ws/') and method == 'GET':
            return 'websocket_connect'
        
        # General API calls
        if path.startswith('/api/'):
            return 'api_general'
        
        return None

class WebSocketRateLimiter:
    """Rate limiter specifically for WebSocket connections"""
    
    def __init__(self, redis_client: redis.Redis):
        self.rate_limiter = RateLimiter(redis_client)
        self.connection_limits = {
            'max_connections_per_user': 5,
            'max_messages_per_minute': 60,
            'max_typing_events_per_minute': 30
        }
    
    async def check_connection_limit(self, user_id: str) -> tuple[bool, Dict]:
        """Check if user can establish new WebSocket connection"""
        return await self.rate_limiter.is_rate_limited(user_id, 'websocket_connect')
    
    async def check_message_limit(self, user_id: str) -> tuple[bool, Dict]:
        """Check if user can send message via WebSocket"""
        return await self.rate_limiter.is_rate_limited(user_id, 'message_send')
    
    async def check_typing_limit(self, user_id: str) -> tuple[bool, Dict]:
        """Check if user can send typing indicator"""
        return await self.rate_limiter.is_rate_limited(f"{user_id}:typing", 'api_general')

class RateLimitConfig:
    """Configuration for rate limiting"""
    
    def __init__(self):
        # Default limits
        self.default_limits = {
            'message_send': {'requests': 10, 'window': 60},
            'conversation_create': {'requests': 5, 'window': 300},
            'file_upload': {'requests': 3, 'window': 60},
            'websocket_connect': {'requests': 10, 'window': 60},
            'api_general': {'requests': 100, 'window': 60},
        }
        
        # User role specific limits
        self.role_limits = {
            'admin': {
                'message_send': {'requests': 50, 'window': 60},
                'conversation_create': {'requests': 20, 'window': 300},
                'file_upload': {'requests': 10, 'window': 60},
            },
            'moderator': {
                'message_send': {'requests': 30, 'window': 60},
                'conversation_create': {'requests': 10, 'window': 300},
                'file_upload': {'requests': 5, 'window': 60},
            },
            'teacher': {
                'message_send': {'requests': 20, 'window': 60},
                'conversation_create': {'requests': 8, 'window': 300},
                'file_upload': {'requests': 4, 'window': 60},
            },
            'student': {
                'message_send': {'requests': 10, 'window': 60},
                'conversation_create': {'requests': 5, 'window': 300},
                'file_upload': {'requests': 3, 'window': 60},
            }
        }
    
    def get_limits_for_user(self, user_role: str = 'student') -> Dict:
        """Get rate limits for specific user role"""
        limits = self.default_limits.copy()
        
        if user_role in self.role_limits:
            limits.update(self.role_limits[user_role])
        
        return limits

# Utility functions for rate limiting

async def check_rate_limit(redis_client: redis.Redis, key: str, limit_type: str) -> tuple[bool, Dict]:
    """Utility function to check rate limit"""
    rate_limiter = RateLimiter(redis_client)
    return await rate_limiter.is_rate_limited(key, limit_type)

async def get_rate_limit_info(redis_client: redis.Redis, key: str, limit_type: str) -> Dict:
    """Utility function to get rate limit information"""
    rate_limiter = RateLimiter(redis_client)
    return await rate_limiter.get_rate_limit_info(key, limit_type)

def create_rate_limit_response(rate_limit_info: Dict) -> JSONResponse:
    """Create standardized rate limit response"""
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            'error': 'Rate limit exceeded',
            'message': f'Too many {rate_limit_info.get("limit_type", "requests")}',
            'rate_limit_info': rate_limit_info,
            'retry_after': rate_limit_info.get('reset_time', 0) - int(time.time())
        },
        headers={
            'X-RateLimit-Limit': str(rate_limit_info.get('limit', 0)),
            'X-RateLimit-Remaining': str(rate_limit_info.get('remaining', 0)),
            'X-RateLimit-Reset': str(rate_limit_info.get('reset_time', 0)),
            'Retry-After': str(rate_limit_info.get('reset_time', 0) - int(time.time()))
        }
    ) 