import asyncio
import time
import functools
from typing import Dict, Any, Optional
import httpx
from concurrent.futures import ThreadPoolExecutor
import threading
import json
import hashlib

class PerformanceOptimizer:
    """
    Performance optimization utility for AI Tutor backend
    Provides caching, connection pooling, and monitoring
    """
    
    def __init__(self):
        self.cache: Dict[str, Any] = {}
        self.tts_cache: Dict[str, bytes] = {}
        self.translation_cache: Dict[str, str] = {}
        self.http_client: Optional[httpx.AsyncClient] = None
        self.thread_pool = ThreadPoolExecutor(max_workers=4)
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "total_requests": 0
        }
        
    def get_cache_key(self, func_name: str, *args, **kwargs) -> str:
        """Generate a cache key for function calls"""
        # Create a hash of the function name and arguments
        key_data = {
            "func": func_name,
            "args": args,
            "kwargs": kwargs
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def cache_result(self, key: str, result: Any, ttl: int = 3600):
        """Cache a result with TTL"""
        self.cache[key] = {
            "result": result,
            "timestamp": time.time(),
            "ttl": ttl
        }
    
    def get_cached_result(self, key: str) -> Optional[Any]:
        """Get cached result if valid"""
        if key in self.cache:
            cached = self.cache[key]
            if time.time() - cached["timestamp"] < cached["ttl"]:
                self.cache_stats["hits"] += 1
                return cached["result"]
            else:
                # Expired, remove from cache
                del self.cache[key]
        
        self.cache_stats["misses"] += 1
        return None
    
    def get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with connection pooling"""
        if self.http_client is None:
            self.http_client = httpx.AsyncClient(
                timeout=30.0,
                limits=httpx.Limits(max_keepalive_connections=20, max_connections=100)
            )
        return self.http_client
    
    async def close_resources(self):
        """Clean up resources"""
        if self.http_client:
            await self.http_client.aclose()
        self.thread_pool.shutdown(wait=True)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        total = self.cache_stats["hits"] + self.cache_stats["misses"]
        hit_rate = (self.cache_stats["hits"] / total * 100) if total > 0 else 0
        
        return {
            "cache_hits": self.cache_stats["hits"],
            "cache_misses": self.cache_stats["misses"],
            "hit_rate_percent": round(hit_rate, 2),
            "cache_size": len(self.cache),
            "tts_cache_size": len(self.tts_cache),
            "translation_cache_size": len(self.translation_cache)
        }

# Global optimizer instance
optimizer = PerformanceOptimizer()

def cached_function(ttl: int = 3600):
    """Decorator for caching function results"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = optimizer.get_cache_key(func.__name__, *args, **kwargs)
            
            # Check cache first
            cached_result = optimizer.get_cached_result(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Cache result
            optimizer.cache_result(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator

class AsyncTaskManager:
    """Manages parallel task execution"""
    
    def __init__(self):
        self.thread_pool = ThreadPoolExecutor(max_workers=4)
    
    async def run_in_thread(self, func, *args, **kwargs):
        """Run a function in thread pool"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.thread_pool, func, *args, **kwargs)
    
    async def run_parallel(self, tasks):
        """Run multiple tasks in parallel"""
        return await asyncio.gather(*tasks, return_exceptions=True)

# Global task manager
task_manager = AsyncTaskManager()

class PerformanceMonitor:
    """Monitor and log performance metrics"""
    
    def __init__(self):
        self.metrics = {}
        self.start_times = {}
    
    def start_timer(self, operation: str):
        """Start timing an operation"""
        self.start_times[operation] = time.time()
    
    def end_timer(self, operation: str) -> float:
        """End timing and return duration"""
        if operation in self.start_times:
            duration = time.time() - self.start_times[operation]
            if operation not in self.metrics:
                self.metrics[operation] = []
            self.metrics[operation].append(duration)
            del self.start_times[operation]
            return duration
        return 0.0
    
    def get_average_time(self, operation: str) -> float:
        """Get average time for an operation"""
        if operation in self.metrics and self.metrics[operation]:
            return sum(self.metrics[operation]) / len(self.metrics[operation])
        return 0.0
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        summary = {}
        for operation, times in self.metrics.items():
            if times:
                summary[operation] = {
                    "avg_time": sum(times) / len(times),
                    "min_time": min(times),
                    "max_time": max(times),
                    "count": len(times)
                }
        return summary

# Global performance monitor
performance_monitor = PerformanceMonitor() 