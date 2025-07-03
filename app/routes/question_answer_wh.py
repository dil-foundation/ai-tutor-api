# Stage 2 - Exercise 2 (Questions & Answers Practice - Responding to WH-questions)

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
import json
import os
from io import BytesIO
from app.services.tts import synthesize_speech_with_elevenlabs
from app.services.stt_english import transcribe_english_audio
from app.services.feedback_wh_questions import evaluate_wh_response
from app.schemas.wh_response import WHResponseEvaluation

router = APIRouter()

PROMPT_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'question_answer_wh.json')


def get_question_item(q_id: int):
    with open(PROMPT_FILE, 'r', encoding='utf-8') as f:
        questions = json.load(f)
    return next((item for item in questions if item["id"] == q_id), None)

@router.get(
    "/wh-question/audio/{q_id}",
    summary="Get audio for the WH-question prompt",
    description="""
Returns the synthesized audio for the WH-question identified by `q_id`.

This is used in Stage 2 - Exercise 2 (Questions & Answers Practice), where the AI tutor asks a WH-question
(e.g., "Where do you live?") and the learner listens before responding with a spoken answer.
"""
)
async def get_wh_question_audio(q_id: int):
    item = get_question_item(q_id)
    if not item:
        raise HTTPException(status_code=404, detail="Question not found")

    return await synthesize_speech_with_elevenlabs(item["question"])


@router.post(
    "/wh-question/evaluate/{q_id}",
    summary="Evaluate the learner's spoken response to the WH-question",
    description="""
Receives the learner's spoken response as an audio file and evaluates it against the WH-question prompt identified by `q_id`.

The evaluation is performed using GPT and includes:
- Relevance to the question
- Grammar and fluency
- Proper use of tense
- Optional keyword alignment

Returns the transcript, score, grammar suggestions, and improvement feedback.

This is part of Stage 2 - Exercise 2 (Questions & Answers Practice).
"""
)
async def evaluate_wh_answer(q_id: int, file: UploadFile = File(...)):
    item = get_question_item(q_id)
    if not item:
        raise HTTPException(status_code=404, detail="Question not found")

    audio_bytes = await file.read()
    transcript = transcribe_english_audio(audio_bytes)

    feedback_result = evaluate_wh_response(
        transcript,
        expected_answers=item["expected_answers"],
        keywords=item["keywords"],
        tense=item["tense"]
    )

    return WHResponseEvaluation(
        transcript=transcript,
        score=feedback_result["score"],
        grammar_errors=feedback_result["grammar_errors"],
        feedback=feedback_result["feedback"]
    )
