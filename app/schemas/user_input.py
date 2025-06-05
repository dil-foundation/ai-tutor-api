from pydantic import BaseModel, EmailStr
from datetime import date


class UserRegisterInput(BaseModel):
    name: str
    password: str
    writing_sample: str

class StageResult(BaseModel):
    name: str
    assigned_stage: str


class SpeakResponse(BaseModel):
    urdu_text: str
    english_translation: str
    english_audio_base64: str 

class FeedbackRequest(BaseModel):
    expected_text: str

class FeedbackResponse(BaseModel):
    user_text: str
    pronunciation_score: float
    fluency_feedback: str

class WordPressUserRegistration(BaseModel):
    username: str
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    date_of_birth: date
    english_assessment_text: str

