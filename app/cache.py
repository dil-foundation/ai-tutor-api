from typing import Dict, List, Any
import json
import asyncio

# Try to import Redis, but don't fail if it's not available
try:
    from app.redis_client import redis_client
    REDIS_AVAILABLE = True
except ImportError:
    print("⚠️ [CACHE] Redis not available - using in-memory fallback")
    REDIS_AVAILABLE = False
    redis_client = None

# In-memory cache for content hierarchy
# This will be populated on application startup to reduce DB calls
content_cache: Dict[str, List[Dict[str, Any]]] = {
    "stages": [],
    "exercises": []
}

# In-memory cache for API responses (fallback when Redis is not available)
memory_cache: Dict[str, Any] = {}

class CacheManager:
    """Cache manager with Redis backend and in-memory fallback"""
    
    async def get(self, key: str) -> Any:
        """Get cached value by key"""
        if REDIS_AVAILABLE:
            try:
                value = redis_client.get(key)
                if value:
                    return json.loads(value)
                return None
            except Exception as e:
                print(f"⚠️ [CACHE] Redis error, falling back to memory: {str(e)}")
                return memory_cache.get(key)
        else:
            return memory_cache.get(key)
    
    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set cached value with TTL in seconds"""
        if REDIS_AVAILABLE:
            try:
                redis_client.setex(key, ttl, json.dumps(value))
                return True
            except Exception as e:
                print(f"⚠️ [CACHE] Redis error, using memory fallback: {str(e)}")
                memory_cache[key] = value
                return True
        else:
            memory_cache[key] = value
            return True
    
    async def delete(self, key: str) -> bool:
        """Delete cached value"""
        if REDIS_AVAILABLE:
            try:
                redis_client.delete(key)
                return True
            except Exception as e:
                print(f"⚠️ [CACHE] Redis error: {str(e)}")
                return False
        else:
            memory_cache.pop(key, None)
            return True

# Global cache manager instance
cache_manager = CacheManager()

async def load_content_cache(progress_tracker):
    """
    Loads all stages and exercises from the database into the in-memory cache.
    This should be called once on application startup.
    """
    print("🔄 [CACHE] Initializing content cache...")
    try:
        stages = await progress_tracker.get_all_stages_from_db()
        exercises = await progress_tracker.get_all_exercises_from_db()
        
        if stages:
            content_cache["stages"] = stages
            print(f"✅ [CACHE] Loaded {len(stages)} stages into cache.")
        else:
            print("⚠️ [CACHE] No stages found to load into cache.")

        if exercises:
            content_cache["exercises"] = exercises
            print(f"✅ [CACHE] Loaded {len(exercises)} exercises into cache.")
        else:
            print("⚠️ [CACHE] No exercises found to load into cache.")
            
    except Exception as e:
        print(f"❌ [CACHE] Error loading content cache: {str(e)}")

def get_stage_by_id(stage_id: int) -> Dict[str, Any]:
    """Retrieves a stage from the cache by its ID."""
    for stage in content_cache["stages"]:
        if stage.get("stage_number") == stage_id:
            return stage
    return {}

def get_exercise_by_ids(stage_id: int, exercise_id: int) -> Dict[str, Any]:
    """Retrieves an exercise from the cache by its stage and exercise ID."""
    for exercise in content_cache["exercises"]:
        if exercise.get("stage_number") == stage_id and exercise.get("exercise_number") == exercise_id:
            return exercise
    return {}

def get_all_stages_from_cache() -> List[Dict[str, Any]]:
    """Retrieves all stages from the cache."""
    return content_cache["stages"]
