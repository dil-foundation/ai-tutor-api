# app/routes/user.py

from fastapi import APIRouter
from app.schemas.user_input import UserRegisterInput, StageResult
from app.services.cefr_evaluator import evaluate_cefr_level

router = APIRouter()

@router.post("/register", response_model=StageResult)
async def register_user(user_input: UserRegisterInput):
    stage = evaluate_cefr_level(user_input.writing_sample)
    return StageResult(name=user_input.name, assigned_stage=stage)

