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
from app.services.feedback import evaluate_response_ex3_stage1
from app.supabase_client import progress_tracker
from app.auth_middleware import get_current_user, require_student
router = APIRouter()

DIALOGUE_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'functional_dialogue.json')

class AudioEvaluationRequest(BaseModel):
    audio_base64: str
    dialogue_id: int
    filename: str
    user_id: str
    time_spent_seconds: int
    urdu_used: bool

def get_dialogue_by_id(dialogue_id: int):
    print(f"🔍 [DIALOGUE] Looking for dialogue with ID: {dialogue_id}")
    try:
        with open(DIALOGUE_FILE, 'r', encoding='utf-8') as f:
            dialogues = json.load(f)
            print(f"📖 [DIALOGUE] Loaded {len(dialogues)} dialogues from file")
            for dialogue in dialogues:
                if dialogue['id'] == dialogue_id:
                    print(f"✅ [DIALOGUE] Found dialogue: {dialogue['ai_prompt']}")
                    return dialogue  # Return the full dialogue object
            print(f"❌ [DIALOGUE] Dialogue with ID {dialogue_id} not found")
            return None
    except Exception as e:
        print(f"❌ [DIALOGUE] Error reading dialogue file: {str(e)}")
        return None


@router.get("/dialogues")
async def get_all_dialogues(current_user: Dict[str, Any] = Depends(require_student)):
    """Get all available dialogues for Listen and Reply exercise"""
    print("🔄 [API] GET /dialogues endpoint called")
    try:
        print(f"📁 [API] Reading dialogue file from: {DIALOGUE_FILE}")
        with open(DIALOGUE_FILE, 'r', encoding='utf-8') as f:
            dialogues = json.load(f)
        print(f"✅ [API] Successfully loaded {len(dialogues)} dialogues")
        return {"dialogues": dialogues}
    except Exception as e:
        print(f"❌ [API] Error in get_all_dialogues: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to load dialogues: {str(e)}")

@router.get("/dialogues/{dialogue_id}")
async def get_dialogue(dialogue_id: int, current_user: Dict[str, Any] = Depends(require_student)):
    """Get a specific dialogue by ID"""
    print(f"🔄 [API] GET /dialogues/{dialogue_id} endpoint called")
    try:
        dialogue_data = get_dialogue_by_id(dialogue_id)
        if not dialogue_data:
            print(f"❌ [API] Dialogue {dialogue_id} not found")
            raise HTTPException(status_code=404, detail="Dialogue not found")
        print(f"✅ [API] Returning dialogue: {dialogue_data['ai_prompt']}")
        return {
            "id": dialogue_data['id'], 
            "ai_prompt": dialogue_data['ai_prompt'],
            "ai_prompt_urdu": dialogue_data['ai_prompt_urdu'],
            "expected_keywords": dialogue_data['expected_keywords'],
            "expected_keywords_urdu": dialogue_data['expected_keywords_urdu'],
            "category": dialogue_data['category'],
            "difficulty": dialogue_data['difficulty'],
            "context": dialogue_data['context']
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [API] Error in get_dialogue: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post(
    "/listen-and-reply/{dialogue_id}",
    summary="Convert dialogue prompt to audio for Listen and Reply Exercise",
    description="""
This endpoint is part of Stage 1 - Exercise 3 (Listen and Reply). 
It takes a dialogue ID from a predefined list, converts the corresponding AI prompt into speech (TTS),
and returns the generated audio file as the response.
""",
    tags=["Stage 1 - Exercise 3 (Listen and Reply)"]
)
async def listen_and_reply(dialogue_id: int, current_user: Dict[str, Any] = Depends(require_student)):
    print(f"🔄 [API] POST /listen-and-reply/{dialogue_id} endpoint called")
    try:
        dialogue_data = get_dialogue_by_id(dialogue_id)
        if not dialogue_data:
            print(f"❌ [API] Dialogue {dialogue_id} not found")
            raise HTTPException(status_code=404, detail="Dialogue not found")

        prompt_text = dialogue_data['ai_prompt']
        print(f"🎤 [API] Converting dialogue to speech: '{prompt_text}'")
        audio_content = await synthesize_speech_exercises(prompt_text)
        print(f"✅ [API] Audio content generated, size: {len(audio_content)} bytes")
        
        # Convert to base64 for React Native compatibility
        audio_base64 = base64.b64encode(audio_content).decode('utf-8')
        print(f"✅ [API] Audio converted to base64, length: {len(audio_base64)}")
        
        # Return base64 string directly
        return {"audio_base64": audio_base64}
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [API] Error in listen_and_reply: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post(
    "/evaluate-listen-reply",
    summary="Evaluate user's audio recording against expected keywords",
    description="""
This endpoint evaluates the user's recorded audio against the expected keywords for listen and reply dialogues.
It performs speech-to-text conversion and provides feedback on the response quality.
Also records progress tracking data in Supabase database.
""",
    tags=["Stage 1 - Exercise 3 (Listen and Reply)"]
)
async def evaluate_listen_reply(
    request: AudioEvaluationRequest,
    current_user: Dict[str, Any] = Depends(require_student)
):
    print(f"🔄 [API] POST /evaluate-listen-reply endpoint called")
    print(f"📝 [API] Request details: dialogue_id={request.dialogue_id}, filename={request.filename}")
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
        # Get the expected dialogue data
        dialogue_data = get_dialogue_by_id(request.dialogue_id)
        if not dialogue_data:
            print(f"❌ [API] Dialogue {request.dialogue_id} not found")
            raise HTTPException(status_code=404, detail="Dialogue not found")

        expected_keywords = dialogue_data['expected_keywords']
        expected_keywords_urdu = dialogue_data['expected_keywords_urdu']
        ai_prompt = dialogue_data['ai_prompt']
        print(f"✅ [API] Expected keywords: {expected_keywords}")
        print(f"✅ [API] AI Prompt: '{ai_prompt}'")

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
                "expected_keywords": expected_keywords
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
                    "expected_keywords": expected_keywords
                }

        except Exception as e:
            print(f"❌ [API] Error transcribing audio: {str(e)}")
            return {
                "success": False,
                "error": "transcription_failed",
                "message": "Failed to process audio. Please try again.",
                "expected_keywords": expected_keywords
            }

        # Evaluate the response
        try:
            print(f"🔄 [API] Evaluating response: '{user_text}' vs expected keywords")
            evaluation = evaluate_response_ex3_stage1(expected_keywords, user_text)
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
                        exercise_id=3,  # Exercise 3 (Listen and Reply)
                        topic_id=request.dialogue_id,
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
            
            return {
                "success": True,
                "ai_prompt": ai_prompt,
                "expected_keywords": expected_keywords,
                "expected_keywords_urdu": expected_keywords_urdu,
                "user_text": user_text,
                "evaluation": evaluation,
                "progress_recorded": progress_recorded,
                "unlocked_content": unlocked_content
            }

        except Exception as e:
            print(f"❌ [API] Error evaluating response: {str(e)}")
            return {
                "success": False,
                "error": "evaluation_failed",
                "message": "Failed to evaluate response. Please try again.",
                "expected_keywords": expected_keywords,
                "user_text": user_text
            }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [API] Unexpected error in evaluate_listen_reply: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}") 