import logging
from pydantic import BaseModel, field_validator
from typing import Optional

# Configure a dedicated logger for settings schema
logger = logging.getLogger(__name__)

class AISettings(BaseModel):
    """
    Pydantic model for AI Tutor Settings.
    Provides default values and validation for a stable base configuration.
    """
    personality_type: str = "Encouraging & Supportive"
    response_style: str = "Conversational"
    max_response_length: int = 150
    repetition_threshold: int = 3
    error_correction_style: str = "Gentle & Encouraging"
    cultural_sensitivity: bool = True
    age_appropriate: bool = True
    professional_context: bool = False
    custom_prompts: Optional[str] = None

    @field_validator('personality_type', 'response_style', 'error_correction_style', mode='before')
    @classmethod
    def validate_text_fields(cls, v: Optional[str], field) -> str:
        """Ensures that critical text fields are never empty, falling back to default if needed."""
        if not v or not v.strip():
            default_value = cls.model_fields[field.field_name].default
            logger.warning(
                f"Validation Warning: Received empty value for '{field.field_name}'. "
                f"Falling back to default: '{default_value}'."
            )
            return default_value
        return v

    class Config:
        orm_mode = True
        from_attributes = True
