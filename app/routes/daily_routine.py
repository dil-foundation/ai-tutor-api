from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
import json
import os
from io import BytesIO
from app.services.tts import synthesize_speech
from app.services.tts import synthesize_speech_with_elevenlabs
from app.services.stt import transcribe_audio_bytes
from app.services.stt_english import transcribe_english_audio
from app.services.feedback_stage_2 import generate_feedback
from app.schemas.daily_routine import EvaluationResult

router = APIRouter()

PROMPTS_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'daily_routine_prompts.json')

def get_prompt(phrase_id: int):
    with open(PROMPTS_FILE, 'r', encoding='utf-8') as f:
        prompts = json.load(f)
    return next((item for item in prompts if item["id"] == phrase_id), None)


@router.get(
    "/daily-routine/question-audio/{phrase_id}",
    summary="Get audio for the daily routine phrase",
    description="""
Returns the synthesized audio for the daily routine phrase identified by the given `phrase_id`.

This is used in Stage 2 - Exercise 1 (Daily Routine Narration) where the learner listens to a phrase 
and responds by narrating their own routine using voice.
"""
)
async def get_question_audio(phrase_id: int):
    prompt = get_prompt(phrase_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    # audio_bytes = synthesize_speech(prompt["phrase"])

    # return StreamingResponse(BytesIO(audio_bytes), media_type="audio/wav")
    
    return await synthesize_speech_with_elevenlabs(prompt["phrase"])


@router.get(
    "/daily-routine/example/{phrase_id}",
    summary="Get example response with audio reference",
    description="""
Returns the example response text and a URL to the corresponding audio for the given `phrase_id`.

Used to guide the learner with a model answer in both text and speech formats.
"""
)
async def get_example_text_and_audio(phrase_id: int):
    prompt = get_prompt(phrase_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    example_text = prompt["example"]
    audio_bytes = synthesize_speech(example_text)

    return {
        "example_text": example_text,
        "example_audio": f"/daily-routine/example-audio/{phrase_id}"  # frontend will fetch this stream
    }


@router.get(
    "/daily-routine/example-audio/{phrase_id}",
    summary="Get audio for the example response",
    description="""
Streams the synthesized audio version of the example response for the specified `phrase_id`.

This is intended to help learners understand proper pronunciation and sentence flow.
"""
)
async def get_example_audio(phrase_id: int):
    prompt = get_prompt(phrase_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    # audio_bytes = synthesize_speech(prompt["example"])
    # return StreamingResponse(BytesIO(audio_bytes), media_type="audio/wav")
    
    return await synthesize_speech_with_elevenlabs(prompt["example"])


@router.post(
    "/daily-routine/evaluate/{phrase_id}",
    summary="Evaluate user's spoken narration for a daily routine phrase",
    description="""
Accepts the user's audio response for the specified `phrase_id`, transcribes it using speech-to-text (STT),
and evaluates the spoken narration based on relevance, keyword usage, and fluency.

Returns a score out of 100 and one-line professional feedback using GPT.

This is part of Stage 2 - Exercise 1 (Daily Routine Narration), helping learners improve structured speech.
"""
)
async def evaluate_user_response(phrase_id: int, file: UploadFile = File(...)):
    prompt = get_prompt(phrase_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    audio_bytes = await file.read()
    transcript = transcribe_english_audio(audio_bytes)

    feedback = generate_feedback(transcript, prompt["example"], prompt["keywords"])

    return EvaluationResult(
        transcript=transcript,
        score=feedback["score"],
        feedback=feedback["feedback"]
    )
