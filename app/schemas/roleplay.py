from pydantic import BaseModel
from typing import List

class RoleplayStartRequest(BaseModel):
    scenario_id: int

class RoleplayUserReply(BaseModel):
    session_id: str
    user_input: str

class RoleplayResponse(BaseModel):
    ai_response: str
    session_id: str
    done: bool

class RoleplayEvaluationResponse(BaseModel):
    score: str
    feedback: str
    suggestions: List[str]
    remarks: str