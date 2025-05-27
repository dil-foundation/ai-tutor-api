from pydantic import BaseModel

class VoiceInput(BaseModel):
    audio_base64: str  # base64 encoded audio file (Urdu speech)

class UserRegisterInput(BaseModel):
    name: str
    password: str
    writing_sample: str

class StageResult(BaseModel):
    name: str
    assigned_stage: str

