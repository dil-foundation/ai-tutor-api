from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from io import BytesIO
from app.services.dialogue_manager import get_prompt_by_id, get_next_prompt_id
from app.services.tts import synthesize_speech_with_elevenlabs_exercises
from app.services.stt_english import transcribe_english_audio
from app.services.dialogue_evaluator import evaluate_dialogue_with_gpt

router = APIRouter()

@router.get(
    "/dialogue/{dialogue_id}/prompt-audio",
    summary="Stage 1 - Exercise 3: Play Predefined Dialogue as audio",
    description=(
        "Listen and Reply - Functional Dialogue: Plays a predefined AI dialogue prompt audio for functional conversation practice. "
        "User listens to the dialogue and replies verbally. Each dialogue is identified by a unique dialogue ID."
    )
)
async def get_dialogue_prompt_audio(dialogue_id: int):
    prompt_data = get_prompt_by_id(dialogue_id)
    if not prompt_data:
        raise HTTPException(status_code=404, detail="Dialogue prompt not found")

    return synthesize_speech_with_elevenlabs_exercises(prompt_data['ai_prompt']) 

@router.post(
    "/dialogue/{dialogue_id}/evaluate",
    summary="Evaluate user's response for Listen and Reply exercise",
    description="""
This endpoint is part of Stage 1 - Exercise 3 (Listen and Reply – Functional Dialogue).
It accepts the user's spoken reply to a specific dialogue (by dialogue ID), transcribes the audio, 
and evaluates the response using GPT-based logic.

The evaluation provides feedback on:
- Fluency
- Keyword relevance
- Conversational appropriateness

The response also includes the ID of the next dialogue in the sequence.
""",
    tags=["Stage 1 - Exercise 3 (Listen and Reply – Functional Dialogue)"]
)
async def evaluate_dialogue_response(dialogue_id: int, file: UploadFile = File(...)):
    prompt_data = get_prompt_by_id(dialogue_id)
    if not prompt_data:
        raise HTTPException(status_code=404, detail="Dialogue not found")

    audio_bytes = await file.read()
    user_transcript = transcribe_english_audio(audio_bytes)

    # Use GPT for feedback and scoring
    evaluation = evaluate_dialogue_with_gpt(
    ai_prompt=prompt_data['ai_prompt'],
    expected_keywords=", ".join(prompt_data.get('expected_keywords', [])),
    user_response=user_transcript
)

    # Fetch next prompt id if available
    next_prompt_id = get_next_prompt_id(dialogue_id)

    return {
        "transcript": user_transcript,
        "evaluation": evaluation,
        "next_prompt_id": next_prompt_id
    }