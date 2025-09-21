import time
import logging
from typing import Optional
from pydantic import ValidationError
from app.supabase_client import supabase
from app.schemas.settings import AISettings

# Configure a dedicated logger for the settings manager
logger = logging.getLogger(__name__)

# --- In-Memory Cache ---
CACHE_DURATION_SECONDS = 300  # 5 minutes
_settings_cache: Optional[AISettings] = None
_cache_timestamp: float = 0

def _get_default_settings() -> AISettings:
    """Returns a default AISettings object for fallback."""
    logger.info("Instantiating default AI settings.")
    default_settings = AISettings()
    # Log the default values being used for clear debugging
    logger.info(f"Default settings values being applied: {default_settings.model_dump_json(indent=2)}")
    return default_settings

def get_ai_settings() -> AISettings:
    """
    Fetches AI Tutor settings from the database with in-memory caching.

    This function retrieves the global AI Tutor configuration from the
    `ai_tutor_settings` table. To optimize performance and reduce database
    load, it uses a time-based in-memory cache.

    The function assumes that the first row in the `ai_tutor_settings` table
    contains the global configuration for the entire application.

    If the table is empty, the data is malformed, or a database error occurs, 
    it falls back to a pre-defined default configuration to ensure system stability.

    Returns:
        AISettings: A Pydantic model instance containing the AI settings.
    """
    global _settings_cache, _cache_timestamp
    
    current_time = time.time()
    
    # Check if a valid cache exists
    if _settings_cache and (current_time - _cache_timestamp < CACHE_DURATION_SECONDS):
        logger.debug("Cache hit. Returning cached AI settings.")
        return _settings_cache
    
    if not _settings_cache:
        logger.info("Cache miss: No settings in cache.")
    else:
        logger.info(f"Cache expired. Last updated {int(current_time - _cache_timestamp)}s ago.")

    logger.info("Fetching fresh AI settings from the database...")
    try:
        # Fetch the first row from the table, assuming it's the global setting
        # FIX: The supabase-python execute() method is synchronous and should not be awaited.
        response = supabase.from_("ai_tutor_settings").select("*").limit(1).execute()
        
        if response.data:
            settings_data = response.data[0]
            try:
                # Validate and parse the data using the Pydantic model
                _settings_cache = AISettings.model_validate(settings_data)
                _cache_timestamp = current_time
                logger.info("Successfully fetched and cached new AI settings.")
                return _settings_cache
            except ValidationError as e:
                logger.error(f"Data validation error for settings from DB: {e}. Falling back to defaults.")
                # Don't cache in case of validation error to allow for correction
                return _get_default_settings()
        else:
            # Statically assign values if the table is empty
            logger.warning("`ai_tutor_settings` table is empty. Caching and using default settings.")
            _settings_cache = _get_default_settings()
            _cache_timestamp = current_time
            return _settings_cache

    except Exception as e:
        logger.critical(f"Database error fetching AI settings: {e}. Falling back to defaults for this request.")
        # On critical error, return defaults but DO NOT cache to allow the system to recover on the next call
        return _get_default_settings()
