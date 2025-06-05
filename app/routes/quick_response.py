from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
import json
import os
from io import BytesIO
from app.services.tts import synthesize_speech
from app.services.stt_english import transcribe_english_audio
from app.services.evaluator import evaluate_response

router = APIRouter()

# Path to the JSON data file
PROMPTS_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'quick_response_prompts.json')

def get_question_by_id(phrase_id: int):
    with open(PROMPTS_FILE, 'r', encoding='utf-8') as f:
        prompts = json.load(f)
        for item in prompts:
            if item['id'] == phrase_id:
                return item['question']
    return None

@router.get(
    "/quick-response/question-audio/{phrase_id}",
    summary="Stage 1 - Exercise 2: Play Question Audio",
    description="Quick Response Prompts - Question Listening: Returns the audio version of a simple question based on the provided phrase ID."
)
async def quick_response_audio(phrase_id: int):
    question = get_question_by_id(phrase_id)
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
    "/quick-response/expected-answer/{phrase_id}",
    summary="Stage 1 - Exercise 2: Get Expected Answer",
    description="Quick Response Prompts - Question Listening: Returns the suggested or expected answer sentence based on the phrase ID. Used to compare user responses in the evaluation step."
)
async def get_expected_answer(phrase_id: int):
    with open(PROMPTS_FILE, 'r', encoding='utf-8') as f:
        prompts = json.load(f)
        for item in prompts:
            if item['id'] == phrase_id:
                return {"expected_answer": item['expected_answer']}
    raise HTTPException(status_code=404, detail="Expected answer not found")

@router.post(
    "/quick-response/evaluate/{phrase_id}",
    summary="Stage 1 - Exercise 2: Evaluate User Response",
    description="Quick Response Prompts - Question Listening: Accepts a user's spoken response as audio and evaluates it based on the expected answer. Returns transcript and scores including grammar, fluency, relevance, and overall feedback."
)
async def evaluate_quick_response(
    phrase_id: int,
    file: UploadFile = File(...),
):
    with open(PROMPTS_FILE, 'r', encoding='utf-8') as f:
        prompts = json.load(f)
        prompt_data = next((item for item in prompts if item['id'] == phrase_id), None)

    if not prompt_data:
        raise HTTPException(status_code=404, detail="Prompt not found")

    question = prompt_data['question']
    expected_answer = prompt_data['expected_answer']

    print("question:", question)
    print("answer:", expected_answer)

    audio_bytes = await file.read()
    user_transcript = transcribe_english_audio(audio_bytes)

    evaluation = evaluate_response(question, expected_answer, user_transcript)

    return {
        "transcript": user_transcript,
        "evaluation": evaluation
    }
