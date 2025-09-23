from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
import os
import base64
from io import BytesIO
from typing import Dict, Any
from fastapi.concurrency import run_in_threadpool
from app.services.tts import synthesize_speech, synthesize_speech_exercises
from app.services.stt import transcribe_audio_bytes_eng_only
from app.services.feedback import evaluate_response_ex2_stage3
from app.supabase_client import supabase, progress_tracker
from app.auth_middleware import get_current_user, require_student, require_admin_or_teacher_or_student

router = APIRouter()

class AudioEvaluationRequest(BaseModel):
    audio_base64: str
    scenario_id: int
    filename: str
    user_id: str
    time_spent_seconds: int
    urdu_used: bool

async def get_scenario_by_id_from_db(scenario_id: int):
    """Fetch a group dialogue scenario from Supabase by its topic_number for Stage 3, Exercise 2."""
    print(f"🔍 [DB] Looking for scenario with topic_number (ID): {scenario_id} for Stage 3, Exercise 2")
    try:
        # parent_id for Stage 3, Exercise 2 ('Group Discussion Simulation') is 14.
        # Use limit(1) instead of single() to prevent errors from duplicate topic_numbers
        query = supabase.table("ai_tutor_content_hierarchy").select("id, topic_number, title, title_urdu, topic_data, category, difficulty").eq("level", "topic").eq("parent_id", 14).eq("topic_number", scenario_id).limit(1)
        response = await run_in_threadpool(query.execute)
        
        if response.data and len(response.data) > 0:
            db_scenario = response.data[0] # Take the first result
            topic_data = db_scenario.get("topic_data", {})
            
            formatted_scenario = {
                "id": db_scenario.get("topic_number"),
                "db_id": db_scenario.get("id"),
                "title": db_scenario.get("title"),
                "title_urdu": db_scenario.get("title_urdu"),
                "context": topic_data.get("context"),
                "context_urdu": topic_data.get("context_urdu"),
                "difficulty": db_scenario.get("difficulty"),
                "category": db_scenario.get("category"),
                "conversation_flow": topic_data.get("conversation_flow"),
                "initial_prompt": topic_data.get("initial_prompt"),
                "initial_prompt_urdu": topic_data.get("initial_prompt_urdu"),
                "follow_up_turns": topic_data.get("follow_up_turns", []),
                "expected_responses": topic_data.get("expected_responses", []),
                "evaluation_criteria": topic_data.get("evaluation_criteria", {}),
                "learning_objectives": topic_data.get("learning_objectives", [])
            }
            print(f"✅ [DB] Found scenario: {formatted_scenario['title']}")
            return formatted_scenario
        else:
            print(f"❌ [DB] Scenario with topic_number {scenario_id} not found for parent_id 14")
            return None
    except Exception as e:
        print(f"❌ [DB] Error fetching scenario from Supabase: {str(e)}")
        return None


async def check_exercise_completion(user_id: str) -> dict:
    """Check if user has completed the full Group Dialogue exercise (Stage 3, Exercise 2)"""
    print(f"🔍 [COMPLETION] Checking exercise completion for user: {user_id}")
    
    try:
        # Get total scenarios count from Supabase
        total_topics = 0
        try:
            # parent_id for 'Group Discussion Simulation' is 14
            query = supabase.table("ai_tutor_content_hierarchy").select("id", count="exact").eq("level", "topic").eq("parent_id", 14)
            response = await run_in_threadpool(query.execute)
            if response.count is not None:
                total_topics = response.count
                print(f"📊 [COMPLETION] Total scenarios available from DB: {total_topics}")
            else:
                print("⚠️ [COMPLETION] Could not get count from Supabase, falling back to default.")
                total_topics = 8
        except Exception as e:
            print(f"❌ [COMPLETION] Error getting scenario count from DB: {str(e)}")
            total_topics = 8 # Default fallback
        
        # Get user's progress for stage 3, exercise 2
        progress_result = await progress_tracker.get_user_topic_progress(
            user_id=user_id,
            stage_id=3,
            exercise_id=2
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
                "exercise_id": 2,
                "exercise_name": "Group Dialogue",
                "stage_name": "Stage 3 – B1 Intermediate",
                "error": progress_result.get("error", "Failed to get progress")
            }
        
        user_progress = progress_result.get("data", [])
        completed_topics = len([record for record in user_progress if record.get("completed", False)])
        
        # Get current topic ID
        current_topic_result = await progress_tracker.get_current_topic_for_exercise(
            user_id=user_id,
            stage_id=3,
            exercise_id=2
        )
        
        current_topic_id = 1
        if current_topic_result["success"]:
            current_topic_id = current_topic_result.get("current_topic_id", 1)
        
        # Calculate progress percentage
        progress_percentage = (completed_topics / total_topics * 100) if total_topics > 0 else 0.0
        
        # Determine if exercise is truly completed
        # Exercise is completed ONLY when ALL topics are completed
        exercise_completed = completed_topics >= total_topics and total_topics > 0
        
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
            "exercise_id": 2,
            "exercise_name": "Group Dialogue",
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
            "exercise_id": 2,
            "exercise_name": "Group Dialogue",
            "stage_name": "Stage 3 – B1 Intermediate",
            "error": str(e)
        }


@router.get("/group-dialogue-scenarios")
async def get_all_scenarios(current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)):
    """Get all available scenarios for Group Dialogue exercise from Supabase"""
    print("🔄 [API] GET /group-dialogue-scenarios endpoint called")
    try:
        print("🔄 [DB] Fetching all scenarios for Stage 3, Exercise 2 from Supabase")
        query = supabase.table("ai_tutor_content_hierarchy").select("id, topic_number, title, title_urdu, topic_data, category, difficulty").eq("level", "topic").eq("parent_id", 14).order("topic_number", desc=False)
        response = await run_in_threadpool(query.execute)

        if response.data:
            scenarios = []
            for s in response.data:
                topic_data = s.get("topic_data", {})
                scenarios.append({
                    "id": s.get("topic_number"),
                    "db_id": s.get("id"),
                    "title": s.get("title"),
                    "title_urdu": s.get("title_urdu"),
                    "context": topic_data.get("context"),
                    "context_urdu": topic_data.get("context_urdu"),
                    "difficulty": s.get("difficulty"),
                    "category": s.get("category"),
                    "conversation_flow": topic_data.get("conversation_flow"),
                    "initial_prompt": topic_data.get("initial_prompt"),
                    "initial_prompt_urdu": topic_data.get("initial_prompt_urdu"),
                    "follow_up_turns": topic_data.get("follow_up_turns", []),
                    "expected_responses": topic_data.get("expected_responses", []),
                    "evaluation_criteria": topic_data.get("evaluation_criteria", {}),
                    "learning_objectives": topic_data.get("learning_objectives", [])
                })
            print(f"✅ [DB] Successfully loaded {len(scenarios)} scenarios from Supabase")
            return {"scenarios": scenarios}
        else:
            print("❌ [DB] No scenarios found for Stage 3, Exercise 2")
            return {"scenarios": []}
    except Exception as e:
        print(f"❌ [API] Error in get_all_scenarios: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to load scenarios from database: {str(e)}")

@router.get("/group-dialogue-scenarios/{scenario_id}")
async def get_scenario(scenario_id: int, current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)):
    """Get a specific scenario by ID"""
    print(f"🔄 [API] GET /group-dialogue-scenarios/{scenario_id} endpoint called")
    try:
        scenario_data = await get_scenario_by_id_from_db(scenario_id)
        if not scenario_data:
            print(f"❌ [API] Scenario {scenario_id} not found")
            raise HTTPException(status_code=404, detail="Scenario not found")
        print(f"✅ [API] Returning scenario: {scenario_data['title']}")
        return {
            "id": scenario_data['id'],
            "title": scenario_data['title'],
            "title_urdu": scenario_data['title_urdu'],
            "context": scenario_data['context'],
            "context_urdu": scenario_data['context_urdu'],
            "difficulty": scenario_data['difficulty'],
            "category": scenario_data['category'],
            "conversation_flow": scenario_data['conversation_flow'],
            "initial_prompt": scenario_data['initial_prompt'],
            "initial_prompt_urdu": scenario_data['initial_prompt_urdu'],
            "follow_up_turns": scenario_data['follow_up_turns'],
            "expected_responses": scenario_data['expected_responses'],
            "evaluation_criteria": scenario_data['evaluation_criteria'],
            "learning_objectives": scenario_data['learning_objectives']
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [API] Error in get_scenario: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post(
    "/group-dialogue/{scenario_id}",
    summary="Convert scenario to audio for Group Dialogue Exercise",
    description="""
This endpoint is part of Stage 3 - Exercise 2 (Group Dialogue). 
It takes a scenario ID from a predefined list, converts the corresponding scenario into speech (TTS),
and returns the generated audio file as the response.
""",
    tags=["Stage 3 - Exercise 2 (Group Dialogue)"]
)
async def group_dialogue(scenario_id: int, current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)):
    print(f"🔄 [API] POST /group-dialogue/{scenario_id} endpoint called")
    try:
        scenario_data = await get_scenario_by_id_from_db(scenario_id)
        if not scenario_data:
            print(f"❌ [API] Scenario {scenario_id} not found")
            raise HTTPException(status_code=404, detail="Scenario not found")
        
        # Create the full conversation text
        conversation_text = f"{scenario_data['initial_prompt']}\n\n"
        for turn in scenario_data['follow_up_turns']:
            conversation_text += f"{turn['speaker']}: {turn['message']}\n\n"
        
        print(f"📝 [API] Generated conversation text: {conversation_text[:100]}...")
        
        # Generate audio using TTS
        print("🔄 [API] Generating audio...")
        audio_data = await synthesize_speech_exercises(conversation_text)
        
        if not audio_data:
            print("❌ [API] Failed to generate audio")
            raise HTTPException(status_code=500, detail="Failed to generate audio")
        
        print("✅ [API] Audio generated successfully")
        
        # Convert to base64
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        return {
            "audio_base64": audio_base64,
            "scenario_id": scenario_id,
            "title": scenario_data['title'],
            "conversation_text": conversation_text
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [API] Error in group_dialogue: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post(
    "/evaluate-group-dialogue",
    summary="Evaluate user's audio recording against expected responses and conversation flow",
    description="""
This endpoint evaluates the user's recorded audio against the expected responses and conversation flow for group dialogue scenarios.
It performs speech-to-text conversion and provides comprehensive feedback on the response quality.
Also records progress tracking data in Supabase database.
""",
    tags=["Stage 3 - Exercise 2 (Group Dialogue)"]
)
async def evaluate_group_dialogue(
    request: AudioEvaluationRequest,
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)
):
    print(f"🔄 [API] POST /evaluate-group-dialogue endpoint called")
    print(f"📊 [API] Request details: scenario_id={request.scenario_id}, user_id={request.user_id}")
    
    # Validate user_id and ensure user can only access their own data
    if not request.user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    
    if request.user_id != current_user['id']:
        raise HTTPException(status_code=403, detail="You can only access your own data")
    
    try:
        # Get scenario data
        scenario_data = await get_scenario_by_id_from_db(request.scenario_id)
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
                    "expected_responses": scenario_data['expected_responses'],
                    "prompt": scenario_data['initial_prompt']
                }

        except Exception as e:
            print(f"❌ [API] Error transcribing audio: {str(e)}")
            return {
                "success": False,
                "error": "transcription_failed",
                "message": "Failed to process audio. Please try again.",
                "expected_responses": scenario_data['expected_responses'],
                "prompt": scenario_data['initial_prompt']
            }
        
        # Evaluate the response
        try:
            print(f"🔄 [API] Evaluating response: '{user_text}' vs expected responses")
            evaluation = evaluate_response_ex2_stage3(
                expected_responses=scenario_data['expected_responses'],
                user_response=user_text,
                context=scenario_data['context'],
                initial_prompt=scenario_data['initial_prompt'],
                follow_up_turns=scenario_data['follow_up_turns']
            )
            print(f"✅ [API] Evaluation completed: {evaluation}")
            
            # Extract evaluation details for progress tracking
            score = evaluation.get("evaluation", {}).get("overall_score", 0)
            is_correct = evaluation.get("success", False)
            completed = evaluation.get("success", False)
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
                    time_spent = max(1, min(request.time_spent_seconds, 600))  # Between 1-600 seconds for group dialogue
                    if time_spent != request.time_spent_seconds:
                        print(f"⚠️ [API] Adjusted time spent from {request.time_spent_seconds} to {time_spent} seconds")
                    
                    # Record the topic attempt
                    progress_result = await progress_tracker.record_topic_attempt(
                        user_id=request.user_id,
                        stage_id=3,  # Stage 3
                        exercise_id=2,  # Exercise 2 (Group Dialogue)
                        topic_id=scenario_data['id'], # Use the topic_number
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
                        "exercise_id": 2,
                        "exercise_name": "Group Dialogue",
                        "stage_name": "Stage 3 – B1 Intermediate",
                        "error": str(completion_error)
                    }
            
            return {
                "success": True,
                "prompt": scenario_data['initial_prompt'],
                "expected_responses": scenario_data['expected_responses'],
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
                        "exercise_id": 2,
                        "exercise_name": "Group Dialogue",
                        "stage_name": "Stage 3 – B1 Intermediate",
                        "error": str(completion_error)
                    }
            
            return {
                "success": False,
                "error": "evaluation_failed",
                "message": "Failed to evaluate response. Please try again.",
                "expected_responses": scenario_data['expected_responses'],
                "prompt": scenario_data['initial_prompt'],
                "user_text": user_text,
                "exercise_completion": exercise_completion_status
            }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [API] Error in evaluate_group_dialogue: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/group-dialogue-progress/{user_id}")
async def get_user_progress(
    user_id: str,
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)
):
    """Get user's progress for Group Dialogue exercise"""
    print(f"🔄 [API] GET /group-dialogue-progress/{user_id} endpoint called")
    
    # Ensure user can only access their own data
    if user_id != current_user['id']:
        raise HTTPException(status_code=403, detail="You can only access your own data")
    
    try:
        # Get topic progress for this specific exercise
        topic_progress = await progress_tracker.get_user_topic_progress(user_id, stage_id=3, exercise_id=2)
        
        # Get current topic
        current_topic = await progress_tracker.get_current_topic_for_exercise(user_id, stage_id=3, exercise_id=2)
        
        # Combine the data
        progress_data = {
            "success": True,
            "topic_progress": topic_progress.get("data", []),
            "current_topic": current_topic.get("current_topic_id", 1),
            "is_completed": current_topic.get("is_completed", False)
        }
        
        print(f"✅ [API] Progress data retrieved: {progress_data}")
        return progress_data
    except Exception as e:
        print(f"❌ [API] Error getting progress: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get progress: {str(e)}")

@router.get("/group-dialogue-current-topic/{user_id}")
async def get_current_topic(
    user_id: str,
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)
):
    """Get user's current topic for Group Dialogue exercise"""
    print(f"🔄 [API] GET /group-dialogue-current-topic/{user_id} endpoint called")
    
    # Ensure user can only access their own data
    if user_id != current_user['id']:
        raise HTTPException(status_code=403, detail="You can only access your own data")
    
    try:
        topic_data = await progress_tracker.get_current_topic_for_exercise(user_id, stage_id=3, exercise_id=2)
        print(f"✅ [API] Current topic retrieved: {topic_data}")
        return topic_data
    except Exception as e:
        print(f"❌ [API] Error getting current topic: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get current topic: {str(e)}") 