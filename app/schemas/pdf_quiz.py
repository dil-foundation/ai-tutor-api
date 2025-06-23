# app/schemas/pdf_quiz.py

from pydantic import BaseModel
from typing import List, Optional, Literal

class QuizItem(BaseModel):
    question: str
    options: List[str]
    answer: Optional[str] = None
    type: Literal[
        "single",
        "multiple",
        "true_or_false",
        "fill_in_the_blank",
        "short_answer",
        "essay",
        "matching",
        "sorting",
        "matrix_sort"
    ] = "single"

class QuizResponse(BaseModel):
    title: Optional[str] = None
    questions: List[QuizItem]

class PDFUrlRequest(BaseModel):
    url: str