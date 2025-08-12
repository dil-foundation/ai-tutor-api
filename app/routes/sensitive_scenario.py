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
from app.services.feedback import evaluate_response_ex2_stage6
from app.supabase_client import progress_tracker
from app.auth_middleware import get_current_user, require_student,require_admin_or_teacher_or_student

router = APIRouter()

SENSITIVE_SCENARIO_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'stage6_exercise2.json')

class AudioEvaluationRequest(BaseModel):
    audio_base64: str
    scenario_id: int
    filename: str
    user_id: str
    time_spent_seconds: int
    urdu_used: bool

def get_scenario_by_id(scenario_id: int):
    print(f"🔍 [SCENARIO] Looking for scenario with ID: {scenario_id}")
    try:
        with open(SENSITIVE_SCENARIO_FILE, 'r', encoding='utf-8') as f:
            scenarios = json.load(f)
            print(f"📖 [SCENARIO] Loaded {len(scenarios)} scenarios from file")
            for scenario in scenarios:
                if scenario['id'] == scenario_id:
                    print(f"✅ [SCENARIO] Found scenario: {scenario['scenario']}")
                    return scenario  # Return the full scenario object
            print(f"❌ [SCENARIO] Scenario with ID {scenario_id} not found")
            return None
    except Exception as e:
        print(f"❌ [SCENARIO] Error reading scenario file: {str(e)}")
        return None

@router.get("/sensitive-scenario-scenarios")
async def get_all_scenarios(current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)):
    """Get all available scenarios for Sensitive Scenario exercise"""
    print("🔄 [API] GET /sensitive-scenario-scenarios endpoint called")
    try:
        print(f"📁 [API] Reading scenario file from: {SENSITIVE_SCENARIO_FILE}")
        with open(SENSITIVE_SCENARIO_FILE, 'r', encoding='utf-8') as f:
            scenarios = json.load(f)
        print(f"✅ [API] Successfully loaded {len(scenarios)} scenarios")
        return {"scenarios": scenarios}
    except Exception as e:
        print(f"❌ [API] Error in get_all_scenarios: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to load scenarios: {str(e)}")

@router.get("/sensitive-scenario-scenarios/{scenario_id}")
async def get_scenario(scenario_id: int, current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)):
    """Get a specific scenario by ID"""
    print(f"🔄 [API] GET /sensitive-scenario-scenarios/{scenario_id} endpoint called")
    try:
        scenario_data = get_scenario_by_id(scenario_id)
        if not scenario_data:
            print(f"❌ [API] Scenario {scenario_id} not found")
            raise HTTPException(status_code=404, detail="Scenario not found")
        print(f"✅ [API] Returning scenario: {scenario_data['scenario']}")
        return {
            "id": scenario_data['id'],
            "scenario": scenario_data['scenario'],
            "category": scenario_data['category'],
            "difficulty": scenario_data['difficulty'],
            "scenario_type": scenario_data['scenario_type'],
            "context": scenario_data['context'],
            "stakeholder_emotions": scenario_data['stakeholder_emotions'],
            "expected_structure": scenario_data['expected_structure'],
            "expected_keywords": scenario_data['expected_keywords'],
            "vocabulary_focus": scenario_data['vocabulary_focus'],
            "model_response": scenario_data['model_response'],
            "evaluation_criteria": scenario_data['evaluation_criteria']
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [API] Error in get_scenario: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post(
    "/sensitive-scenario/{scenario_id}",
    summary="Convert scenario to audio for Sensitive Scenario Exercise",
    description="""
This endpoint is part of Stage 6 - Exercise 2 (Roleplay - Handle a Sensitive Scenario). 
It takes a scenario ID from a predefined list, converts the corresponding scenario into speech (TTS),
and returns the generated audio file as the response.
""",
    tags=["Stage 6 - Exercise 2 (Sensitive Scenario)"]
)
async def sensitive_scenario(scenario_id: int, current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)):
    print(f"🔄 [API] POST /sensitive-scenario/{scenario_id} endpoint called")
    try:
        scenario_data = get_scenario_by_id(scenario_id)
        if not scenario_data:
            print(f"❌ [API] Scenario {scenario_id} not found")
            raise HTTPException(status_code=404, detail="Scenario not found")

        scenario_text = scenario_data['scenario']
        print(f"🎤 [API] Converting scenario to speech: '{scenario_text}'")
        audio_content = await synthesize_speech_exercises(scenario_text)
        print(f"✅ [API] Audio content generated, size: {len(audio_content)} bytes")
        
        # Convert to base64 for React Native compatibility
        audio_base64 = base64.b64encode(audio_content).decode('utf-8')
        print(f"✅ [API] Audio converted to base64, length: {len(audio_base64)}")
        
        # Return base64 string directly
        return {"audio_base64": audio_base64}
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [API] Error in sensitive_scenario: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post(
    "/evaluate-sensitive-scenario",
    summary="Evaluate user's audio recording against expected keywords and sensitive scenario criteria",
    description="""
This endpoint evaluates the user's recorded audio against the expected keywords and sensitive scenario criteria for C2-level scenarios.
It performs speech-to-text conversion and provides comprehensive feedback on the response quality.
Also records progress tracking data in Supabase database.
""",
    tags=["Stage 6 - Exercise 2 (Sensitive Scenario)"]
)
async def evaluate_sensitive_scenario(
    request: AudioEvaluationRequest,
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)
):
    print(f"🔄 [API] POST /evaluate-sensitive-scenario endpoint called")
    print(f"📝 [API] Request details: scenario_id={request.scenario_id}, filename={request.filename}")
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
        # Get the expected scenario and keywords
        scenario_data = get_scenario_by_id(request.scenario_id)
        if not scenario_data:
            print(f"❌ [API] Scenario {request.scenario_id} not found")
            raise HTTPException(status_code=404, detail="Scenario not found")

        expected_keywords = scenario_data['expected_keywords']
        scenario_text = scenario_data['scenario']
        model_response = scenario_data['model_response']
        evaluation_criteria = scenario_data['evaluation_criteria']
        print(f"✅ [API] Expected keywords: {expected_keywords}")
        print(f"✅ [API] Scenario: '{scenario_text}'")
        print(f"✅ [API] Model response: '{model_response}'")

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
                "expected_keywords": expected_keywords,
                "scenario": scenario_text
            }

        # Transcribe the audio
        try:
            print("🔄 [API] Transcribing audio...")
            transcription_result = transcribe_audio_bytes_eng_only(audio_bytes)
            user_text = transcription_result.get("text", "").strip()
            print(f"✅ [API] Transcription result: '{user_text}'")
            
            # Check if transcription is empty or too short
            if not user_text or len(user_text) < 10:
                print(f"⚠️ [API] Transcription too short or empty: '{user_text}'")
                return {
                    "success": False,
                    "error": "no_speech_detected",
                    "message": "No clear speech detected. Please speak more clearly and provide a comprehensive response.",
                    "expected_keywords": expected_keywords,
                    "scenario": scenario_text
                }

        except Exception as e:
            print(f"❌ [API] Error transcribing audio: {str(e)}")
            return {
                "success": False,
                "error": "transcription_failed",
                "message": "Failed to process audio. Please try again.",
                "expected_keywords": expected_keywords,
                "scenario": scenario_text
            }

        # Evaluate the response
        try:
            print(f"🔄 [API] Evaluating response: '{user_text}' vs expected keywords: {expected_keywords}")
            evaluation = evaluate_response_ex2_stage6(expected_keywords, user_text, scenario_text, model_response, evaluation_criteria)
            print(f"✅ [API] Evaluation completed: {evaluation}")
            
            # Extract evaluation details for progress tracking
            score = evaluation.get("score", 0)
            is_correct = evaluation.get("is_correct", False)
            completed = evaluation.get("completed", False)
            suggested_improvement = evaluation.get("suggested_improvement", "")
            keyword_matches = evaluation.get("keyword_matches", 0)
            total_keywords = evaluation.get("total_keywords", len(expected_keywords))
            fluency_score = evaluation.get("fluency_score", 0)
            grammar_score = evaluation.get("grammar_score", 0)
            
            print(f"📊 [API] Evaluation details: score={score}, is_correct={is_correct}, completed={completed}")
            print(f"📊 [API] Keyword matches: {keyword_matches}/{total_keywords}")
            print(f"📊 [API] Fluency score: {fluency_score}, Grammar score: {grammar_score}")
            
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
                    time_spent = max(1, min(request.time_spent_seconds, 600))  # Between 1-600 seconds for sensitive scenarios
                    if time_spent != request.time_spent_seconds:
                        print(f"⚠️ [API] Adjusted time spent from {request.time_spent_seconds} to {time_spent} seconds")
                    
                    # Record the scenario attempt
                    progress_result = await progress_tracker.record_topic_attempt(
                        user_id=request.user_id,
                        stage_id=6,  # Stage 6
                        exercise_id=2,  # Exercise 2 (Sensitive Scenario)
                        topic_id=request.scenario_id,
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
                "scenario": scenario_text,
                "expected_keywords": expected_keywords,
                "user_text": user_text,
                "evaluation": evaluation,
                "suggested_improvement": suggested_improvement,
                "progress_recorded": progress_recorded,
                "unlocked_content": unlocked_content,
                "keyword_matches": keyword_matches,
                "total_keywords": total_keywords,
                "fluency_score": fluency_score,
                "grammar_score": grammar_score
            }

        except Exception as e:
            print(f"❌ [API] Error evaluating response: {str(e)}")
            return {
                "success": False,
                "error": "evaluation_failed",
                "message": "Failed to evaluate response. Please try again.",
                "expected_keywords": expected_keywords,
                "scenario": scenario_text,
                "user_text": user_text
            }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [API] Unexpected error in evaluate_sensitive_scenario: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}") 