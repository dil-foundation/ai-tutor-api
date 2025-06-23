from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
import json
import os
from io import BytesIO
from app.services.tts import synthesize_speech
from app.services.stt_english import transcribe_english_audio
from app.services.evaluator import evaluate_response

router = APIRouter()

# Updated path to the correct JSON file
PROMPTS_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'quick_response_prompts.json')

def get_question_by_id(prompt_id: int):
    with open(PROMPTS_FILE, 'r', encoding='utf-8') as f:
        prompts = json.load(f)
        for item in prompts:
            if item['id'] == prompt_id:
                return item['question']
    return None

@router.get(
    "/quick-response/question-audio/{prompt_id}",
    summary="Get question as audio (Stage 2 - Quick Response)",
    description="""
Returns a synthesized speech version of the question corresponding to the given `prompt_id`.
This is used in Stage 2 - Exercise 2: Quick Response, where the learner listens and responds quickly in English.
""",
    tags=["Stage 1 - Exercise 2 (Quick Response)"]
)
async def quick_response_audio(prompt_id: int):
    question = get_question_by_id(prompt_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    audio_content = synthesize_speech(question)
    audio_stream = BytesIO(audio_content)
    audio_stream.seek(0)

    return StreamingResponse(
        content=audio_stream,
        media_type="audio/wav",
        headers={"Content-Disposition": 'inline; filename="question.wav"'}
    )


@router.get(
    "/quick-response/expected-answer/{prompt_id}",
    summary="Get expected answer for a question prompt",
    description="""
Fetches the correct (expected) answer for the given `prompt_id` from the predefined dataset.
Used for evaluating user responses in the Quick Response exercise.
""",
    tags=["Stage 1 - Exercise 2 (Quick Response)"]
)
async def get_expected_answer(prompt_id: int):
    with open(PROMPTS_FILE, 'r', encoding='utf-8') as f:
        prompts = json.load(f)
        for item in prompts:
            if item['id'] == prompt_id:
                return {"expected_answer": item['expected_answer']}
    raise HTTPException(status_code=404, detail="Expected answer not found")

@router.post(
    "/quick-response/evaluate/{prompt_id}",
    summary="Evaluate user's spoken response to a quick question",
    description="""
Uploads the user's audio response to a quick question prompt (by ID), transcribes it to text,
and evaluates the quality and accuracy against the expected answer using GPT.

Part of Stage 2 - Exercise 2: Quick Response (AI-assisted speaking evaluation).
""",
    tags=["Stage 1 - Exercise 2 (Quick Response)"]
)
async def evaluate_quick_response(
    prompt_id: int,
    file: UploadFile = File(...),
):
    # Load the prompt (question + expected answer)
    with open(PROMPTS_FILE, 'r', encoding='utf-8') as f:
        prompts = json.load(f)
        prompt_data = next((item for item in prompts if item['id'] == prompt_id), None)

    if not prompt_data:
        raise HTTPException(status_code=404, detail="Prompt not found")

    question = prompt_data['question']
    expected_answer = prompt_data['expected_answer']

    print("question: ",question)
    print("answer: ",expected_answer)

    # Read user audio and transcribe
    audio_bytes = await file.read()
    user_transcript = transcribe_english_audio(audio_bytes)

    # Evaluate using GPT
    evaluation = evaluate_response(question, expected_answer, user_transcript)

    return {
        "transcript": user_transcript,
        "evaluation": evaluation
    }
