import time
import logging
from typing import Optional
from pydantic import ValidationError
from app.supabase_client import supabase
from app.schemas.safety import AISafetyEthicsSettings

# Configure a dedicated logger for the safety manager
logger = logging.getLogger(__name__)

# --- In-Memory Cache ---
CACHE_DURATION_SECONDS = 300  # 5 minutes
_safety_settings_cache: Optional[AISafetyEthicsSettings] = None
_safety_cache_timestamp: float = 0

def _get_default_safety_settings() -> AISafetyEthicsSettings:
    """Returns a default AISafetyEthicsSettings object for a secure fallback."""
    logger.info("Instantiating default AI safety & ethics settings.")
    default_settings = AISafetyEthicsSettings()
    logger.info(f"Default safety settings being applied: {default_settings.model_dump_json(indent=2)}")
    return default_settings

async def get_ai_safety_settings() -> AISafetyEthicsSettings:
    """
    Fetches AI Safety & Ethics settings from the database with caching.

    Retrieves the global safety configuration from the `ai_safety_ethics_settings`
    table. Uses a time-based in-memory cache to optimize performance.

    Assumes the first row contains the global configuration. Falls back to
    secure defaults if the table is empty or if an error occurs.
    """
    current_time = time.time()
    
    # 1. Check cache validity
    if _safety_settings_cache and (current_time - _safety_cache_timestamp) < CACHE_DURATION_SECONDS:
        logger.debug("Returning cached AI safety settings.")
        return _safety_settings_cache

    # 2. Cache is invalid or empty, fetch from database
    reason = "expired" if _safety_settings_cache else "No settings in cache"
    logger.info(f"Cache miss for safety settings: {reason}.")
    logger.info("Fetching fresh AI safety settings from the database...")
    try:
        # The supabase-python execute() method is synchronous
        response = supabase.from_("ai_safety_ethics_settings").select("*").limit(1).execute()
        
        if response.data:
            settings_data = response.data[0]
            try:
                # Validate data against the Pydantic model
                new_settings = AISafetyEthicsSettings.model_validate(settings_data)
                globals()['_safety_settings_cache'] = new_settings
                globals()['_safety_cache_timestamp'] = current_time
                logger.info("Successfully fetched and cached new AI safety settings.")
                return new_settings
            except ValidationError as e:
                logger.error(f"Data validation error for AI safety settings: {e}. Falling back to defaults.")
                return _get_default_safety_settings()
        else:
            # Handle empty table: use and cache defaults
            logger.warning("`ai_safety_ethics_settings` table is empty. Caching and using default settings.")
            default_settings = _get_default_safety_settings()
            globals()['_safety_settings_cache'] = default_settings
            globals()['_safety_cache_timestamp'] = current_time
            return default_settings

    except Exception as e:
        logger.critical(f"Database error fetching AI safety settings: {e}. Falling back to defaults for this request.")
        return _get_default_safety_settings()
