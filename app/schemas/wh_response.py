# Stage 2 - Exercise 2 (Questions & Answers Practice - Responding to WH-questions)

from pydantic import BaseModel
from typing import List


class WHResponseEvaluation(BaseModel):
    transcript: str
    score: float
    grammar_errors: List[str]
    feedback: str

