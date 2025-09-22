from typing import Dict, List, Any

# In-memory cache for content hierarchy
# This will be populated on application startup to reduce DB calls
content_cache: Dict[str, List[Dict[str, Any]]] = {
    "stages": [],
    "exercises": []
}

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
