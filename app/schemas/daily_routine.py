from pydantic import BaseModel

class DailyRoutinePrompt(BaseModel):
    id: int
    phrase: str
    example: str
    keywords: list[str]

class EvaluationResult(BaseModel):
    transcript: str
    score: float
    feedback: str
