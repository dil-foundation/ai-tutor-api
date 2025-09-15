import logging
from pydantic import BaseModel, field_validator
from typing import Optional

# Configure a dedicated logger for the safety schema
logger = logging.getLogger(__name__)

class AISafetyEthicsSettings(BaseModel):
    """
    Pydantic model for AI Safety & Ethics Settings.
    Provides robust default values and validation to ensure a secure baseline.
    """
    # Content Safety & Filtering
    content_filtering: bool = True
    toxicity_detection: bool = True
    bias_detection: bool = True
    harmful_content_prevention: bool = True

    # Bias & Fairness Monitoring
    gender_bias_monitoring: bool = True
    cultural_bias_detection: bool = True
    inclusive_language: bool = True
    
    # Privacy & Data Protection
    conversation_logging: bool = True # Default to True for safety monitoring

    @field_validator('*', mode='before')
    @classmethod
    def check_boolean_fields(cls, v: Optional[bool], field) -> bool:
        """
        Ensures that boolean fields are always either True or False, never None.
        This prevents ambiguity in safety settings.
        """
        if v is None:
            logger.warning(
                f"Safety setting '{field.name}' is null in the database. "
                f"Falling back to default value: {cls.model_fields[field.name].default}"
            )
            return cls.model_fields[field.name].default
        return v

    class Config:
        from_attributes = True
