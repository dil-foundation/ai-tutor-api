from pydantic import BaseModel


class UserRegisterInput(BaseModel):
    name: str
    password: str
    writing_sample: str

class StageResult(BaseModel):
    name: str
    assigned_stage: str

