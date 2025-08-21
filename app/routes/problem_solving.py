from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import json
import base64
from typing import List, Optional, Dict, Any
from app.services.feedback import evaluate_response_ex3_stage3
from app.services.stt import transcribe_audio_bytes_eng_only
from app.services.tts import synthesize_speech_exercises
from app.supabase_client import progress_tracker
from app.auth_middleware import get_current_user, require_student, require_admin_or_teacher_or_student
import os

router = APIRouter()

# Data models
class AudioEvaluationRequest(BaseModel):
    audio_base64: str
    scenario_id: int
    filename: str
    user_id: str
    time_spent_seconds: int
    urdu_used: bool

# Load scenarios data
def load_scenarios():
    """Load problem-solving scenarios from JSON file"""
    try:
        with open("app/data/stage3_exercise3.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ [DATA] Error loading scenarios: {str(e)}")
        return []

def get_scenario_by_id(scenario_id: int):
    """Get a specific scenario by ID"""
    scenarios = load_scenarios()
    for scenario in scenarios:
        if scenario["id"] == scenario_id:
            return scenario
    return None


async def check_exercise_completion(user_id: str) -> dict:
    """Check if user has completed the full Problem Solving exercise (Stage 3, Exercise 3)"""
    print(f"🔍 [COMPLETION] Checking exercise completion for user: {user_id}")
    
    try:
        # Get total scenarios count
        scenarios = load_scenarios()
        total_topics = len(scenarios)
        print(f"📊 [COMPLETION] Total scenarios available: {total_topics}")
        
        # Get user's progress for stage 3, exercise 3
        progress_result = await progress_tracker.get_user_topic_progress(
            user_id=user_id,
            stage_id=3,
            exercise_id=3
        )
        
        if not progress_result["success"]:
            print(f"❌ [COMPLETION] Failed to get user progress: {progress_result.get('error')}")
            return {
                "exercise_completed": False,
                "progress_percentage": 0.0,
                "completed_topics": 0,
                "total_topics": total_topics,
                "current_topic_id": 1,
                "stage_id": 3,
                "exercise_id": 3,
                "exercise_name": "Problem Solving",
                "stage_name": "Stage 3 – B1 Intermediate",
                "error": progress_result.get("error", "Failed to get progress")
            }
        
        user_progress = progress_result.get("data", [])
        completed_topics = len([record for record in user_progress if record.get("completed", False)])
        
        # Get current topic ID
        current_topic_result = await progress_tracker.get_current_topic_for_exercise(
            user_id=user_id,
            stage_id=3,
            exercise_id=3
        )
        
        current_topic_id = 1
        if current_topic_result["success"]:
            current_topic_id = current_topic_result.get("current_topic_id", 1)
        
        # Calculate progress percentage
        progress_percentage = (completed_topics / total_topics * 100) if total_topics > 0 else 0.0
        
        # Determine if exercise is truly completed
        # Exercise is completed ONLY when ALL topics are completed
        exercise_completed = completed_topics >= total_topics and completed_topics > 0
        
        print(f"📊 [COMPLETION] Completion status calculated:")
        print(f"   - Total scenarios: {total_topics}")
        print(f"   - Completed topics: {completed_topics}")
        print(f"   - Current topic ID: {current_topic_id}")
        print(f"   - Progress percentage: {progress_percentage:.1f}%")
        print(f"   - Exercise completed: {exercise_completed}")
        
        # Additional logging for completion logic
        if completed_topics >= total_topics:
            print(f"🎉 [COMPLETION] User has completed all {total_topics} scenarios!")
        else:
            print(f"📚 [COMPLETION] User still needs to complete {total_topics - completed_topics} more scenarios")
        
        return {
            "exercise_completed": exercise_completed,
            "progress_percentage": progress_percentage,
            "completed_topics": completed_topics,
            "total_topics": total_topics,
            "current_topic_id": current_topic_id,
            "stage_id": 3,
            "exercise_id": 3,
            "exercise_name": "Problem Solving",
            "stage_name": "Stage 3 – B1 Intermediate"
        }
        
    except Exception as e:
        print(f"❌ [COMPLETION] Error checking exercise completion: {str(e)}")
        return {
            "exercise_completed": False,
            "progress_percentage": 0.0,
            "completed_topics": 0,
            "total_topics": 0,
            "current_topic_id": 1,
            "stage_id": 3,
            "exercise_id": 3,
            "exercise_name": "Problem Solving",
            "stage_name": "Stage 3 – B1 Intermediate",
            "error": str(e)
        }


@router.get(
    "/problem-solving-scenarios",
    summary="Get all problem-solving scenarios",
    description="Retrieve all available problem-solving scenarios for Stage 3 Exercise 3",
    tags=["Stage 3 - Exercise 3 (Problem-Solving)"]
)
async def get_problem_solving_scenarios(current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)):
    """Get all problem-solving scenarios"""
    print("🔄 [API] GET /problem-solving-scenarios endpoint called")
    
    try:
        scenarios = load_scenarios()
        print(f"✅ [API] Retrieved {len(scenarios)} scenarios")
        
        return {
            "scenarios": scenarios,
            "total_count": len(scenarios)
        }
    except Exception as e:
        print(f"❌ [API] Error retrieving scenarios: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to load scenarios: {str(e)}")

@router.get(
    "/problem-solving-scenarios/{scenario_id}",
    summary="Get specific problem-solving scenario",
    description="Retrieve a specific problem-solving scenario by ID",
    tags=["Stage 3 - Exercise 3 (Problem-Solving)"]
)
async def get_problem_solving_scenario(scenario_id: int, current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)):
    """Get a specific problem-solving scenario by ID"""
    print(f"🔄 [API] GET /problem-solving-scenarios/{scenario_id} endpoint called")
    
    try:
        scenario = get_scenario_by_id(scenario_id)
        if not scenario:
            print(f"❌ [API] Scenario {scenario_id} not found")
            raise HTTPException(status_code=404, detail="Scenario not found")
        
        print(f"✅ [API] Retrieved scenario: {scenario['title']}")
        return scenario
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [API] Error retrieving scenario: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to load scenario: {str(e)}")

@router.post(
    "/problem-solving/{scenario_id}",
    summary="Generate audio for problem-solving scenario",
    description="Generate audio narration for a specific problem-solving scenario",
    tags=["Stage 3 - Exercise 3 (Problem-Solving)"]
)
async def generate_problem_solving_audio(
    scenario_id: int,
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)
):
    """Generate audio for a problem-solving scenario"""
    print(f"🔄 [API] POST /problem-solving/{scenario_id} endpoint called")
    
    try:
        scenario = get_scenario_by_id(scenario_id)
        if not scenario:
            print(f"❌ [API] Scenario {scenario_id} not found")
            raise HTTPException(status_code=404, detail="Scenario not found")
        
        # Create audio text from scenario
        audio_text = f"""
        {scenario['title']}
        
        {scenario['problem_description']}
        
        Context: {scenario['context']}
        
        Please respond appropriately to this situation using polite language and clear problem description.
        """
        
        print(f"✅ [API] Generating audio for scenario: {scenario['title']}")
        
        # Generate audio using TTS service
        audio_content = await synthesize_speech_exercises(audio_text)
        print(f"✅ [API] Audio content generated, size: {len(audio_content)} bytes")
        
        # Convert to base64 for React Native compatibility
        audio_base64 = base64.b64encode(audio_content).decode('utf-8')
        print(f"✅ [API] Audio converted to base64, length: {len(audio_base64)}")
        
        return {
            "scenario_id": scenario_id,
            "title": scenario['title'],
            "audio_base64": audio_base64,
            "message": "Audio generated successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [API] Error generating audio: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate audio: {str(e)}")

@router.post(
    "/evaluate-problem-solving",
    summary="Evaluate user's audio recording against problem-solving scenario",
    description="""
This endpoint evaluates the user's recorded audio against the problem-solving scenario requirements.
It performs speech-to-text conversion and provides comprehensive feedback on the response quality.
Also records progress tracking data in Supabase database.
""",
    tags=["Stage 3 - Exercise 3 (Problem-Solving)"]
)
async def evaluate_problem_solving(
    request: AudioEvaluationRequest,
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)
):
    """Evaluate user's response for problem-solving scenario"""
    print(f"🔄 [API] POST /evaluate-problem-solving endpoint called")
    print(f"📊 [API] Request details: scenario_id={request.scenario_id}, user_id={request.user_id}")
    
    # Validate user_id and ensure user can only access their own data
    if not request.user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    
    if request.user_id != current_user['id']:
        raise HTTPException(status_code=403, detail="You can only access your own data")
    
    try:
        # Get scenario data
        scenario_data = get_scenario_by_id(request.scenario_id)
        if not scenario_data:
            print(f"❌ [API] Scenario {request.scenario_id} not found")
            raise HTTPException(status_code=404, detail="Scenario not found")
        
        print(f"✅ [API] Found scenario: {scenario_data['title']}")
        
        # Convert base64 audio to bytes
        try:
            audio_bytes = base64.b64decode(request.audio_base64)
            print(f"📊 [API] Audio decoded successfully, size: {len(audio_bytes)} bytes")
        except Exception as e:
            print(f"❌ [API] Error decoding audio: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid audio data")
        
        # Check if audio is too short (silence detection)
        if len(audio_bytes) < 1000:  # Less than 1KB indicates very short/silent audio
            print(f"⚠️ [API] Audio too short ({len(audio_bytes)} bytes), likely silent")
            return {
                "success": False,
                "error": "no_speech_detected",
                "message": "No speech detected. Please try again.",
                "expected_keywords": scenario_data['expected_keywords'],
                "problem_description": scenario_data['problem_description']
            }
        
        # Transcribe audio to text
        try:
            print("🔄 [API] Transcribing audio...")
            transcription_result = transcribe_audio_bytes_eng_only(audio_bytes)
            user_text = transcription_result.get("text", "").strip()
            print(f"✅ [API] Transcription result: '{user_text}'")
            
            # Check if transcription is empty or too short
            if not user_text or len(user_text) < 5:
                print(f"⚠️ [API] Transcription too short or empty: '{user_text}'")
                return {
                    "success": False,
                    "error": "no_speech_detected",
                    "message": "No clear speech detected. Please speak more clearly and respond appropriately.",
                    "expected_keywords": scenario_data['expected_keywords'],
                    "problem_description": scenario_data['problem_description']
                }

        except Exception as e:
            print(f"❌ [API] Error transcribing audio: {str(e)}")
            return {
                "success": False,
                "error": "transcription_failed",
                "message": "Failed to process audio. Please try again.",
                "expected_keywords": scenario_data['expected_keywords'],
                "problem_description": scenario_data['problem_description']
            }
        
        # Evaluate the response
        try:
            print(f"🔄 [API] Evaluating response: '{user_text}' vs expected keywords")
            evaluation = evaluate_response_ex3_stage3(
                expected_keywords=scenario_data['expected_keywords'],
                user_response=user_text,
                problem_description=scenario_data['problem_description'],
                context=scenario_data['context'],
                polite_phrases=scenario_data['polite_phrases'],
                sample_responses=scenario_data['sample_responses']
            )
            print(f"✅ [API] Evaluation completed: {evaluation}")
            
            # Extract evaluation details for progress tracking
            score = evaluation.get("score", 0)
            is_correct = evaluation.get("is_correct", False)
            completed = evaluation.get("completed", False)
            suggested_improvement = evaluation.get("suggested_improvement", "")
            keyword_matches = evaluation.get("matched_keywords_count", 0)
            total_keywords = evaluation.get("total_keywords", 0)
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
                    time_spent = max(1, min(request.time_spent_seconds, 600))  # Between 1-600 seconds for problem-solving
                    if time_spent != request.time_spent_seconds:
                        print(f"⚠️ [API] Adjusted time spent from {request.time_spent_seconds} to {time_spent} seconds")
                    
                    # Record the topic attempt
                    progress_result = await progress_tracker.record_topic_attempt(
                        user_id=request.user_id,
                        stage_id=3,  # Stage 3
                        exercise_id=3,  # Exercise 3 (Problem-Solving)
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
            
            # Check exercise completion status
            exercise_completion_status = None
            if request.user_id and request.user_id.strip():
                try:
                    exercise_completion_status = await check_exercise_completion(request.user_id)
                    print(f"📊 [API] Exercise completion status: {exercise_completion_status}")
                except Exception as completion_error:
                    print(f"⚠️ [API] Failed to check exercise completion: {str(completion_error)}")
                    exercise_completion_status = {
                        "exercise_completed": False,
                        "progress_percentage": 0.0,
                        "completed_topics": 0,
                        "total_topics": 0,
                        "current_topic_id": 1,
                        "stage_id": 3,
                        "exercise_id": 3,
                        "exercise_name": "Problem Solving",
                        "stage_name": "Stage 3 – B1 Intermediate",
                        "error": str(completion_error)
                    }
            
            return {
                "success": True,
                "problem_description": scenario_data['problem_description'],
                "expected_keywords": scenario_data['expected_keywords'],
                "user_text": user_text,
                "evaluation": evaluation,
                "suggested_improvement": suggested_improvement,
                "progress_recorded": progress_recorded,
                "unlocked_content": unlocked_content,
                "keyword_matches": keyword_matches,
                "total_keywords": total_keywords,
                "fluency_score": fluency_score,
                "grammar_score": grammar_score,
                "response_type": evaluation.get("response_type", ""),
                "scenario_title": scenario_data['title'],
                "scenario_context": scenario_data['context'],
                "exercise_completion": exercise_completion_status
            }

        except Exception as e:
            print(f"❌ [API] Error evaluating response: {str(e)}")
            
            # Check exercise completion status even for evaluation errors
            exercise_completion_status = None
            if request.user_id and request.user_id.strip():
                try:
                    exercise_completion_status = await check_exercise_completion(request.user_id)
                except Exception as completion_error:
                    print(f"⚠️ [API] Failed to check exercise completion: {str(completion_error)}")
                    exercise_completion_status = {
                        "exercise_completed": False,
                        "progress_percentage": 0.0,
                        "completed_topics": 0,
                        "total_topics": 0,
                        "current_topic_id": 1,
                        "stage_id": 3,
                        "exercise_id": 3,
                        "exercise_name": "Problem Solving",
                        "stage_name": "Stage 3 – B1 Intermediate",
                        "error": str(completion_error)
                    }
            
            return {
                "success": False,
                "error": "evaluation_failed",
                "message": "Failed to evaluate response. Please try again.",
                "expected_keywords": scenario_data['expected_keywords'],
                "problem_description": scenario_data['problem_description'],
                "user_text": user_text,
                "exercise_completion": exercise_completion_status
            }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [API] Error in evaluate_problem_solving: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get(
    "/problem-solving-progress/{user_id}",
    summary="Get user's problem-solving progress",
    description="Retrieve the user's progress for Stage 3 Exercise 3 (Problem-Solving)",
    tags=["Stage 3 - Exercise 3 (Problem-Solving)"]
)
async def get_problem_solving_progress(
    user_id: str,
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)
):
    """Get user's problem-solving progress"""
    print(f"🔄 [API] GET /problem-solving-progress/{user_id} endpoint called")
    
    # Ensure user can only access their own data
    if user_id != current_user['id']:
        raise HTTPException(status_code=403, detail="You can only access your own data")
    
    try:
        # Get user's progress for Stage 3 Exercise 3
        progress_result = await progress_tracker.get_user_topic_progress(
            user_id=user_id,
            stage_id=3,
            exercise_id=3
        )
        
        if progress_result["success"]:
            print(f"✅ [API] Retrieved progress for user: {user_id}")
            return {
                "success": True,
                "topic_progress": progress_result.get("topic_progress", []),
                "overall_progress": progress_result.get("overall_progress", {})
            }
        else:
            print(f"❌ [API] Failed to retrieve progress: {progress_result.get('error')}")
            return {
                "success": False,
                "error": progress_result.get("error", "Failed to retrieve progress"),
                "topic_progress": [],
                "overall_progress": {}
            }
    except Exception as e:
        print(f"❌ [API] Error retrieving progress: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to retrieve progress: {str(e)}",
            "topic_progress": [],
            "overall_progress": {}
        }

@router.get(
    "/problem-solving-current-topic/{user_id}",
    summary="Get user's current problem-solving topic",
    description="Retrieve the user's current topic for Stage 3 Exercise 3 (Problem-Solving)",
    tags=["Stage 3 - Exercise 3 (Problem-Solving)"]
)
async def get_problem_solving_current_topic(
    user_id: str,
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)
):
    """Get user's current problem-solving topic"""
    print(f"🔄 [API] GET /problem-solving-current-topic/{user_id} endpoint called")
    
    # Ensure user can only access their own data
    if user_id != current_user['id']:
        raise HTTPException(status_code=403, detail="You can only access your own data")
    
    try:
        # Get user's current topic for Stage 3 Exercise 3
        current_topic_result = await progress_tracker.get_current_topic_for_exercise(
            user_id=user_id,
            stage_id=3,
            exercise_id=3
        )
        
        if current_topic_result["success"]:
            print(f"✅ [API] Retrieved current topic for user: {user_id}")
            return {
                "success": True,
                "current_topic_id": current_topic_result.get("current_topic_id", 1),
                "total_topics": current_topic_result.get("total_topics", 5)
            }
        else:
            print(f"❌ [API] Failed to retrieve current topic: {current_topic_result.get('error')}")
            return {
                "success": False,
                "error": current_topic_result.get("error", "Failed to retrieve current topic"),
                "current_topic_id": 1,
                "total_topics": 5
            }
    except Exception as e:
        print(f"❌ [API] Error retrieving current topic: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to retrieve current topic: {str(e)}",
            "current_topic_id": 1,
            "total_topics": 5
        } 

        