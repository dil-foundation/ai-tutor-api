from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
import os
import base64
from io import BytesIO
from typing import Dict, Any
from app.services.tts import synthesize_speech, synthesize_speech_exercises
from app.services.stt import transcribe_audio_bytes_eng_only
from app.services.feedback import evaluate_response_ex2_stage1
from app.supabase_client import progress_tracker
from app.auth_middleware import get_current_user, require_student,require_admin_or_teacher_or_student
router = APIRouter()

PROMPTS_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'quick_response_prompts.json')

class AudioEvaluationRequest(BaseModel):
    audio_base64: str
    prompt_id: int
    filename: str
    user_id: str
    time_spent_seconds: int
    urdu_used: bool

def get_prompt_by_id(prompt_id: int):
    print(f"🔍 [PROMPT] Looking for prompt with ID: {prompt_id}")
    try:
        with open(PROMPTS_FILE, 'r', encoding='utf-8') as f:
            prompts = json.load(f)
            print(f"📖 [PROMPT] Loaded {len(prompts)} prompts from file")
            for prompt in prompts:
                if prompt['id'] == prompt_id:
                    print(f"✅ [PROMPT] Found prompt: {prompt['question']}")
                    return prompt  # Return the full prompt object
            print(f"❌ [PROMPT] Prompt with ID {prompt_id} not found")
            return None
    except Exception as e:
        print(f"❌ [PROMPT] Error reading prompts file: {str(e)}")
        return None


async def check_exercise_completion(user_id: str) -> dict:
    """Check if user has completed the full Quick Response exercise (Stage 1, Exercise 2)"""
    print(f"🔍 [COMPLETION] Checking exercise completion for user: {user_id}")
    
    try:
        # Get total prompts count
        total_prompts = 0
        try:
            with open(PROMPTS_FILE, 'r', encoding='utf-8') as f:
                prompts = json.load(f)
                total_prompts = len(prompts)
                print(f"📊 [COMPLETION] Total prompts available: {total_prompts}")
        except Exception as e:
            print(f"❌ [COMPLETION] Error reading prompts file: {str(e)}")
            total_prompts = 25  # Default fallback based on data file
        
        # Get user's progress for Stage 1 Exercise 2
        progress_result = await progress_tracker.get_user_topic_progress(
            user_id=user_id,
            stage_id=1,
            exercise_id=2
        )
        
        if not progress_result["success"]:
            print(f"❌ [COMPLETION] Failed to get progress: {progress_result.get('error')}")
            return {
                "exercise_completed": False,
                "progress_percentage": 0,
                "completed_topics": 0,
                "total_topics": total_prompts,
                "current_topic_id": 1,
                "error": progress_result.get("error", "Failed to get progress")
            }
        
        # Get current topic information
        current_topic_result = await progress_tracker.get_current_topic_for_exercise(
            user_id=user_id,
            stage_id=1,
            exercise_id=2
        )
        
        if not current_topic_result["success"]:
            print(f"❌ [COMPLETION] Failed to get current topic: {current_topic_result.get('error')}")
            return {
                "exercise_completed": False,
                "progress_percentage": 0,
                "completed_topics": 0,
                "total_topics": total_prompts,
                "current_topic_id": 1,
                "error": current_topic_result.get("error", "Failed to get current topic")
            }
        
        # Extract progress data
        topic_progress = progress_result.get("data", [])
        current_topic_id = current_topic_result.get("current_topic_id", 1)
        is_exercise_completed = current_topic_result.get("is_completed", False)
        
        # Calculate completion metrics
        completed_topics = len(topic_progress) if topic_progress else 0
        progress_percentage = (completed_topics / total_prompts) * 100 if total_prompts > 0 else 0
        
        # Determine if exercise is truly completed
        # Exercise is completed ONLY when ALL topics are completed
        exercise_completed = completed_topics >= total_prompts and completed_topics > 0
        
        print(f"📊 [COMPLETION] Completion status calculated:")
        print(f"   - Total prompts: {total_prompts}")
        print(f"   - Completed topics: {completed_topics}")
        print(f"   - Current topic ID: {current_topic_id}")
        print(f"   - Progress percentage: {progress_percentage:.1f}%")
        print(f"   - Exercise completed: {exercise_completed}")
        
        # Additional logging for completion logic
        if completed_topics >= total_prompts:
            print(f"🎉 [COMPLETION] All {total_prompts} prompts completed! Exercise is finished!")
        elif completed_topics > 0:
            print(f"📈 [COMPLETION] {completed_topics}/{total_prompts} prompts completed. Exercise in progress...")
        else:
            print(f"🆕 [COMPLETION] No prompts completed yet. Exercise just started.")
        
        return {
            "exercise_completed": exercise_completed,
            "progress_percentage": round(progress_percentage, 1),
            "completed_topics": completed_topics,
            "total_topics": total_prompts,
            "current_topic_id": current_topic_id,
            "stage_id": 1,
            "exercise_id": 2,
            "exercise_name": "Quick Response Prompts",
            "stage_name": "Stage 1 – A1 Beginner",
            "completion_date": topic_progress[-1].get("created_at") if topic_progress and exercise_completed else None
        }
        
    except Exception as e:
        print(f"❌ [COMPLETION] Error checking exercise completion: {str(e)}")
        return {
            "exercise_completed": False,
            "progress_percentage": 0,
            "completed_topics": 0,
            "total_topics": 8,
            "current_topic_id": 1,
            "error": f"Failed to check completion status: {str(e)}"
        }


@router.get("/prompts")
async def get_all_prompts(current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)):
    """Get all available prompts for Quick Response exercise"""
    print("🔄 [API] GET /prompts endpoint called")
    try:
        print(f"📁 [API] Reading prompts file from: {PROMPTS_FILE}")
        with open(PROMPTS_FILE, 'r', encoding='utf-8') as f:
            prompts = json.load(f)
        print(f"✅ [API] Successfully loaded {len(prompts)} prompts")
        return {"prompts": prompts}
    except Exception as e:
        print(f"❌ [API] Error in get_all_prompts: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to load prompts: {str(e)}")

@router.get("/prompts/{prompt_id}")
async def get_prompt(prompt_id: int, current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)):
    """Get a specific prompt by ID"""
    print(f"🔄 [API] GET /prompts/{prompt_id} endpoint called")
    try:
        prompt_data = get_prompt_by_id(prompt_id)
        if not prompt_data:
            print(f"❌ [API] Prompt {prompt_id} not found")
            raise HTTPException(status_code=404, detail="Prompt not found")
        print(f"✅ [API] Returning prompt: {prompt_data['question']}")
        return {
            "id": prompt_data['id'], 
            "question": prompt_data['question'],
            "question_urdu": prompt_data['question_urdu'],
            "expected_answers": prompt_data['expected_answers'],
            "expected_answers_urdu": prompt_data['expected_answers_urdu'],
            "category": prompt_data['category'],
            "difficulty": prompt_data['difficulty']
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [API] Error in get_prompt: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post(
    "/quick-response/{prompt_id}",
    summary="Convert prompt question to audio for Quick Response Exercise",
    description="""
This endpoint is part of Stage 1 - Exercise 2 (Quick Response). 
It takes a prompt ID from a predefined list, converts the corresponding question into speech (TTS),
and returns the generated audio file as the response.
""",
    tags=["Stage 1 - Exercise 2 (Quick Response)"]
)
async def quick_response(prompt_id: int, current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)):
    print(f"🔄 [API] POST /quick-response/{prompt_id} endpoint called")
    try:
        prompt_data = get_prompt_by_id(prompt_id)
        if not prompt_data:
            print(f"❌ [API] Prompt {prompt_id} not found")
            raise HTTPException(status_code=404, detail="Prompt not found")

        question_text = prompt_data['question']
        print(f"🎤 [API] Converting question to speech: '{question_text}'")
        audio_content = await synthesize_speech_exercises(question_text)
        print(f"✅ [API] Audio content generated, size: {len(audio_content)} bytes")
        
        # Convert to base64 for React Native compatibility
        audio_base64 = base64.b64encode(audio_content).decode('utf-8')
        print(f"✅ [API] Audio converted to base64, length: {len(audio_base64)}")
        
        # Return base64 string directly
        return {"audio_base64": audio_base64}
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [API] Error in quick_response: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post(
    "/evaluate-quick-response",
    summary="Evaluate user's audio recording against expected answers",
    description="""
This endpoint evaluates the user's recorded audio against the expected answers for quick response prompts.
It performs speech-to-text conversion and provides feedback on the response quality.
Also records progress tracking data in Supabase database.
""",
    tags=["Stage 1 - Exercise 2 (Quick Response)"]
)
async def evaluate_quick_response(
    request: AudioEvaluationRequest,
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)
):
    print(f"🔄 [API] POST /evaluate-quick-response endpoint called")
    print(f"📝 [API] Request details: prompt_id={request.prompt_id}, filename={request.filename}")
    print(f"📊 [API] Audio data length: {len(request.audio_base64)} characters")
    print(f"👤 [API] User ID: {request.user_id}")
    print(f"⏱️ [API] Time spent: {request.time_spent_seconds} seconds")
    print(f"🌐 [API] Urdu used: {request.urdu_used}")
    
    # Validate user_id and ensure user can only access their own data
    if not request.user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    
    if request.user_id != current_user['id']:
        raise HTTPException(status_code=403, detail="You can only access your own data")
    
    try:
        # Get the expected prompt data
        prompt_data = get_prompt_by_id(request.prompt_id)
        if not prompt_data:
            print(f"❌ [API] Prompt {request.prompt_id} not found")
            raise HTTPException(status_code=404, detail="Prompt not found")

        expected_answers = prompt_data['expected_answers']
        expected_answers_urdu = prompt_data['expected_answers_urdu']
        print(f"✅ [API] Expected answers: {expected_answers}")

        # Decode base64 audio
        try:
            print("🔄 [API] Decoding base64 audio...")
            audio_bytes = base64.b64decode(request.audio_base64)
            print(f"✅ [API] Audio decoded, size: {len(audio_bytes)} bytes")
        except Exception as e:
            print(f"❌ [API] Error decoding base64 audio: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid audio data")

        # Check if audio is too short (silence detection)
        if len(audio_bytes) < 1000:  # Less than 1KB indicates very short/silent audio
            print(f"⚠️ [API] Audio too short ({len(audio_bytes)} bytes), likely silent")
            return {
                "success": False,
                "error": "no_speech_detected",
                "message": "No speech detected. Please try again.",
                "expected_answers": expected_answers
            }

        # Transcribe the audio
        try:
            print("🔄 [API] Transcribing audio...")
            transcription_result = transcribe_audio_bytes_eng_only(audio_bytes)
            user_text = transcription_result.get("text", "").strip()
            print(f"✅ [API] Transcription result: '{user_text}'")
            
            # Check if transcription is empty or too short
            if not user_text or len(user_text) < 2:
                print(f"⚠️ [API] Transcription too short or empty: '{user_text}'")
                return {
                    "success": False,
                    "error": "no_speech_detected",
                    "message": "No clear speech detected. Please speak more clearly.",
                    "expected_answers": expected_answers
                }

        except Exception as e:
            print(f"❌ [API] Error transcribing audio: {str(e)}")
            return {
                "success": False,
                "error": "transcription_failed",
                "message": "Failed to process audio. Please try again.",
                "expected_answers": expected_answers
            }

        # Evaluate the response
        try:
            print(f"🔄 [API] Evaluating response: '{user_text}' vs expected answers")
            evaluation = evaluate_response_ex2_stage1(expected_answers, user_text)
            print(f"✅ [API] Evaluation completed: {evaluation}")
            
            # Extract evaluation details for progress tracking
            score = evaluation.get("score", 0)
            is_correct = evaluation.get("is_correct", False)
            completed = evaluation.get("completed", False)
            
            print(f"📊 [API] Evaluation details: score={score}, is_correct={is_correct}, completed={completed}")
            
            # Validate evaluation data
            if not isinstance(score, (int, float)) or score < 0 or score > 100:
                print(f"⚠️ [API] Invalid score value: {score}, using default")
                score = 50
                is_correct = False
                completed = False
            
            # Record progress in Supabase database
            progress_recorded = False
            unlocked_content = []
            
            if request.user_id and request.user_id.strip():
                print(f"🔄 [API] Recording progress for user: {request.user_id}")
                try:
                    # Validate time spent (should be reasonable)
                    time_spent = max(1, min(request.time_spent_seconds, 300))  # Between 1-300 seconds
                    if time_spent != request.time_spent_seconds:
                        print(f"⚠️ [API] Adjusted time spent from {request.time_spent_seconds} to {time_spent} seconds")
                    
                    # Record the topic attempt
                    progress_result = await progress_tracker.record_topic_attempt(
                        user_id=request.user_id,
                        stage_id=1,  # Stage 1
                        exercise_id=2,  # Exercise 2 (Quick Response)
                        topic_id=request.prompt_id,
                        score=float(score),
                        urdu_used=request.urdu_used,
                        time_spent_seconds=time_spent,
                        completed=completed
                    )
                    
                    if progress_result["success"]:
                        print(f"✅ [API] Progress recorded successfully")
                        progress_recorded = True
                        
                        # Check for unlocked content
                        unlock_result = await progress_tracker.check_and_unlock_content(request.user_id)
                        if unlock_result["success"]:
                            unlocked_content = unlock_result.get("unlocked_content", [])
                            if unlocked_content:
                                print(f"🎉 [API] Unlocked content: {unlocked_content}")
                    else:
                        print(f"❌ [API] Failed to record progress: {progress_result.get('error')}")
                        
                except Exception as e:
                    print(f"❌ [API] Error recording progress: {str(e)}")
                    print(f"❌ [API] Progress tracking error details: {type(e).__name__}: {str(e)}")
                    # Don't fail the entire request if progress tracking fails
            else:
                print(f"⚠️ [API] No valid user ID provided, skipping progress tracking")
            
            # Check if the exercise is completed
            exercise_completion_status = await check_exercise_completion(request.user_id)
            print(f"📊 [API] Exercise completion status: {exercise_completion_status}")

            return {
                "success": True,
                "expected_answers": expected_answers,
                "expected_answers_urdu": expected_answers_urdu,
                "user_text": user_text,
                "evaluation": evaluation,
                "progress_recorded": progress_recorded,
                "unlocked_content": unlocked_content,
                "exercise_completion_status": exercise_completion_status
            }

        except Exception as e:
            print(f"❌ [API] Error evaluating response: {str(e)}")
            return {
                "success": False,
                "error": "evaluation_failed",
                "message": "Failed to evaluate response. Please try again.",
                "expected_answers": expected_answers,
                "user_text": user_text
            }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [API] Unexpected error in evaluate_quick_response: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}") 