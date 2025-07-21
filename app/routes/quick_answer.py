from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import json
import os
from app.services.tts import synthesize_speech_exercises
from app.services.stt import transcribe_audio_bytes_eng_only
from app.services.feedback import evaluate_response_ex2_stage2
from app.supabase_client import SupabaseProgressTracker
import base64

router = APIRouter(tags=["quick-answer"])

# Load question data
def load_questions():
    try:
        with open("app/data/question_answer_chat_practice.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ [QUICK_ANSWER] Error loading questions: {e}")
        return []

class AudioEvaluationRequest(BaseModel):
    audio_base64: str
    question_id: int
    filename: str
    user_id: str
    time_spent_seconds: int
    urdu_used: bool

class QuestionResponse(BaseModel):
    id: int
    question: str
    question_urdu: str
    expected_answers: List[str]
    expected_answers_urdu: List[str]
    keywords: List[str]
    keywords_urdu: List[str]
    category: str
    difficulty: str
    tense: str
    sentence_structure: str

@router.get("/quick-answer-questions")
async def get_all_questions():
    """Get all quick answer questions"""
    try:
        questions = load_questions()
        print(f"✅ [QUICK_ANSWER] Loaded {len(questions)} questions")
        return {"questions": questions}
    except Exception as e:
        print(f"❌ [QUICK_ANSWER] Error getting questions: {e}")
        raise HTTPException(status_code=500, detail="Failed to load questions")

@router.get("/quick-answer-questions/{question_id}")
async def get_question_by_id(question_id: int):
    """Get a specific question by ID"""
    try:
        questions = load_questions()
        question = next((q for q in questions if q["id"] == question_id), None)
        
        if not question:
            print(f"❌ [QUICK_ANSWER] Question {question_id} not found")
            raise HTTPException(status_code=404, detail="Question not found")
        
        print(f"✅ [QUICK_ANSWER] Found question {question_id}: {question['question']}")
        return question
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [QUICK_ANSWER] Error getting question {question_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get question")

@router.post("/quick-answer/{question_id}")
async def generate_question_audio(question_id: int):
    """Generate TTS audio for a specific question"""
    try:
        questions = load_questions()
        question = next((q for q in questions if q["id"] == question_id), None)
        
        if not question:
            print(f"❌ [QUICK_ANSWER] Question {question_id} not found for TTS")
            raise HTTPException(status_code=404, detail="Question not found")
        
        print(f"🔄 [QUICK_ANSWER] Generating TTS for question {question_id}")
        
        # Generate TTS audio for the question
        audio_base64 = await synthesize_speech_exercises(question["question"])
        
        if not audio_base64:
            print(f"❌ [QUICK_ANSWER] Failed to generate TTS for question {question_id}")
            raise HTTPException(status_code=500, detail="Failed to generate audio")
        
        print(f"✅ [QUICK_ANSWER] TTS generated successfully for question {question_id}")
        return {"audio_base64": audio_base64}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [QUICK_ANSWER] Error generating TTS for question {question_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate audio")

@router.post("/evaluate-quick-answer")
async def evaluate_quick_answer_audio(request: AudioEvaluationRequest):
    """Evaluate audio response for quick answer exercise"""
    try:
        print(f"🔄 [QUICK_ANSWER] Starting evaluation for question {request.question_id}")
        
        # Load question data
        questions = load_questions()
        question = next((q for q in questions if q["id"] == request.question_id), None)
        
        if not question:
            print(f"❌ [QUICK_ANSWER] Question {request.question_id} not found for evaluation")
            raise HTTPException(status_code=404, detail="Question not found")
        
        # Decode audio
        try:
            audio_data = base64.b64decode(request.audio_base64)
            print(f"✅ [QUICK_ANSWER] Audio decoded successfully, size: {len(audio_data)} bytes")
        except Exception as e:
            print(f"❌ [QUICK_ANSWER] Failed to decode audio: {e}")
            raise HTTPException(status_code=400, detail="Invalid audio data")
        
        # Check if audio is too short
        if len(audio_data) < 1000:  # Less than 1KB
            print(f"⚠️ [QUICK_ANSWER] Audio too short: {len(audio_data)} bytes")
            return {
                "success": False,
                "question": question["question"],
                "expected_answers": question["expected_answers"],
                "error": "audio_too_short",
                "message": "Audio recording is too short. Please speak more clearly.",
                "progress_recorded": False
            }
        
        # Transcribe audio
        print(f"🔄 [QUICK_ANSWER] Transcribing audio...")
        transcription_result = transcribe_audio_bytes_eng_only(audio_data)
        
        user_text = transcription_result.get("text", "").strip()
        print(f"✅ [QUICK_ANSWER] Transcription successful: '{user_text}'")
        
        if not user_text or len(user_text) < 3:
            print(f"⚠️ [QUICK_ANSWER] Transcribed text too short: '{user_text}'")
            return {
                "success": False,
                "question": question["question"],
                "expected_answers": question["expected_answers"],
                "error": "no_speech_detected",
                "message": "No clear speech detected. Please speak more clearly.",
                "progress_recorded": False
            }
        
        # Evaluate response
        print(f"🔄 [QUICK_ANSWER] Evaluating response...")
        evaluation = evaluate_response_ex2_stage2(
            expected_answers=question["expected_answers"],
            user_response=user_text,
            question=question["question"],
            question_urdu=question["question_urdu"]
        )
        
        print(f"✅ [QUICK_ANSWER] Evaluation completed: {evaluation}")
        
        # Initialize progress tracker
        progress_tracker = SupabaseProgressTracker()
        
        # Record progress
        try:
            print(f"🔄 [QUICK_ANSWER] Recording progress for user {request.user_id}")
            progress_result = await progress_tracker.record_topic_attempt(
                user_id=request.user_id,
                stage_id=2,  # Stage 2
                exercise_id=2,  # Exercise 2 (Quick Answer)
                topic_id=request.question_id,
                score=evaluation.get("score", 0),
                urdu_used=request.urdu_used,
                time_spent_seconds=request.time_spent_seconds,
                completed=evaluation.get("completed", False)
            )
            
            if progress_result.get("success"):
                print(f"✅ [QUICK_ANSWER] Progress recorded successfully")
                
                # Check for unlocked content
                unlock_result = await progress_tracker.check_and_unlock_content(request.user_id)
                unlocked_content = unlock_result.get("unlocked_content", []) if unlock_result.get("success") else []
                
                return {
                    "success": True,
                    "question": question["question"],
                    "expected_answers": question["expected_answers"],
                    "user_text": user_text,
                    "evaluation": evaluation,
                    "progress_recorded": True,
                    "unlocked_content": unlocked_content,
                    "answer_accuracy": evaluation.get("answer_accuracy", 0),
                    "grammar_score": evaluation.get("grammar_score", 0),
                    "fluency_score": evaluation.get("fluency_score", 0)
                }
            else:
                print(f"⚠️ [QUICK_ANSWER] Progress recording failed: {progress_result.get('error')}")
                return {
                    "success": True,
                    "question": question["question"],
                    "expected_answers": question["expected_answers"],
                    "user_text": user_text,
                    "evaluation": evaluation,
                    "progress_recorded": False,
                    "answer_accuracy": evaluation.get("answer_accuracy", 0),
                    "grammar_score": evaluation.get("grammar_score", 0),
                    "fluency_score": evaluation.get("fluency_score", 0)
                }
                
        except Exception as e:
            print(f"❌ [QUICK_ANSWER] Error recording progress: {e}")
            return {
                "success": True,
                "question": question["question"],
                "expected_answers": question["expected_answers"],
                "user_text": user_text,
                "evaluation": evaluation,
                "progress_recorded": False,
                "answer_accuracy": evaluation.get("answer_accuracy", 0),
                "grammar_score": evaluation.get("grammar_score", 0),
                "fluency_score": evaluation.get("fluency_score", 0)
            }
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [QUICK_ANSWER] Unexpected error in evaluation: {e}")
        raise HTTPException(status_code=500, detail="Failed to evaluate response") 