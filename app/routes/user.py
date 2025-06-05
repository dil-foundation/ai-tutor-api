# app/routes/user.py

from fastapi import APIRouter
from app.schemas.user_input import UserRegisterInput, StageResult
from app.services.cefr_evaluator import evaluate_cefr_level

router = APIRouter()

@router.post(
    "/register",
    response_model=StageResult,
    summary="User Registration with CEFR Stage Assignment",
    description=(
        "Assigns a CEFR English proficiency stage (A0 to C2) to a new user during app registration.\n\n"
        "The user submits a short English writing sample (2–3 sentences). This sample is evaluated using GPT-4 "
        "to determine the most appropriate CEFR level:\n\n"
        "- **A0**: No understanding or broken grammar (nonsensical text).\n"
        "- **A1 to C2**: Increasing levels of proficiency based on clarity, vocabulary, and grammar.\n\n"
        "Returns the assigned CEFR stage and user name."
    )
)
async def register_user(user_input: UserRegisterInput):
    stage = evaluate_cefr_level(user_input.writing_sample)
    return StageResult(name=user_input.name, assigned_stage=stage)

