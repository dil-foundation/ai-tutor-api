# app/schemas/pdf_quiz.py

from pydantic import BaseModel
from typing import List, Optional

class QuizItem(BaseModel):
    question: str
    options: List[str]
    answer: Optional[str] = None

class QuizResponse(BaseModel):
    title: Optional[str] = None
    questions: List[QuizItem]

class PDFUrlRequest(BaseModel):
    url: str