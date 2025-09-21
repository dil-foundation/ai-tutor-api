from fastapi import APIRouter, HTTPException, Depends
# from sqlalchemy.orm import Session
# from app.database import get_db
from app.schemas.roleplay import (
    RoleplayStartRequest, 
    RoleplayUserReply, 
    RoleplayResponse,
    RoleplayEvaluationRequest,
    RoleplayEvaluationResponse,
    ScenariosResponse,
    ConversationHistoryResponse
)
from app.services.roleplay_agent import roleplay_agent
from app.services.feedback import evaluate_response_ex3_stage2
from app.services.stt import transcribe_audio_bytes_eng_only
from app.supabase_client import supabase, progress_tracker
from app.redis_client import redis_client
from app.auth_middleware import get_current_user, require_student,require_admin_or_teacher_or_student
import json
import base64
from typing import List, Dict, Any
from fastapi.concurrency import run_in_threadpool

router = APIRouter()

async def get_scenario_by_id_from_db(scenario_id: int):
    """Fetch a roleplay scenario from Supabase by its topic_number for Stage 2, Exercise 3."""
    print(f"🔍 [DB] Looking for scenario with topic_number (ID): {scenario_id} for Stage 2, Exercise 3")
    try:
        # parent_id for Stage 2, Exercise 3 ('Roleplay Simulation') is 12.
        query = supabase.table("ai_tutor_content_hierarchy").select("id, topic_number, title, title_urdu, topic_data, category, difficulty").eq("level", "topic").eq("parent_id", 12).eq("topic_number", scenario_id).single()
        response = await run_in_threadpool(query.execute)
        
        if response.data:
            db_scenario = response.data
            topic_data = db_scenario.get("topic_data", {})
            
            formatted_scenario = {
                "id": db_scenario.get("topic_number"),
                "db_id": db_scenario.get("id"),
                "title": db_scenario.get("title"),
                "title_urdu": db_scenario.get("title_urdu"),
                "description": topic_data.get("description"),
                "description_urdu": topic_data.get("description_urdu"),
                "initial_prompt": topic_data.get("initial_prompt"),
                "initial_prompt_urdu": topic_data.get("initial_prompt_urdu"),
                "scenario_context": topic_data.get("scenario_context"),
                "difficulty": db_scenario.get("difficulty"),
                "expected_keywords": topic_data.get("expected_keywords", []),
                "expected_keywords_urdu": topic_data.get("expected_keywords_urdu", []),
                "ai_character": topic_data.get("ai_character"),
                "conversation_flow": topic_data.get("conversation_flow"),
                "cultural_context": topic_data.get("cultural_context"),
            }
            print(f"✅ [DB] Found scenario: {formatted_scenario['title']}")
            return formatted_scenario
        else:
            print(f"❌ [DB] Scenario with topic_number {scenario_id} not found for parent_id 12")
            return None
    except Exception as e:
        print(f"❌ [DB] Error fetching scenario from Supabase: {str(e)}")
        return None

async def get_all_scenarios_from_db():
    """Fetch all roleplay scenarios from Supabase for Stage 2, Exercise 3."""
    print("🔄 [DB] Fetching all scenarios for Stage 2, Exercise 3 from Supabase")
    try:
        query = supabase.table("ai_tutor_content_hierarchy").select("id, topic_number, title, title_urdu, topic_data, category, difficulty").eq("level", "topic").eq("parent_id", 12).order("topic_number", desc=False)
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
                    "description": topic_data.get("description"),
                    "description_urdu": topic_data.get("description_urdu"),
                    "initial_prompt": topic_data.get("initial_prompt"),
                    "initial_prompt_urdu": topic_data.get("initial_prompt_urdu"),
                    "scenario_context": topic_data.get("scenario_context"),
                    "difficulty": s.get("difficulty"),
                    "expected_keywords": topic_data.get("expected_keywords", []),
                    "expected_keywords_urdu": topic_data.get("expected_keywords_urdu", []),
                    "ai_character": topic_data.get("ai_character"),
                    "conversation_flow": topic_data.get("conversation_flow"),
                    "cultural_context": topic_data.get("cultural_context"),
                })
            print(f"✅ [DB] Successfully loaded {len(scenarios)} scenarios from Supabase")
            return scenarios
        else:
            print("❌ [DB] No scenarios found for Stage 2, Exercise 3")
            return []
    except Exception as e:
        print(f"❌ [DB] Error fetching all scenarios from Supabase: {str(e)}")
        return []

async def check_exercise_completion(user_id: str) -> dict:
    """Check if user has completed the full Roleplay Simulation exercise (Stage 2, Exercise 3)"""
    print(f"🔍 [COMPLETION] Checking exercise completion for user: {user_id}")
    
    try:
        # Get total scenarios count from Supabase
        total_topics = 0
        try:
            query = supabase.table("ai_tutor_content_hierarchy").select("id", count="exact").eq("level", "topic").eq("parent_id", 12)
            response = await run_in_threadpool(query.execute)
            if response.count is not None:
                total_topics = response.count
                print(f"📊 [COMPLETION] Total scenarios available from DB: {total_topics}")
            else:
                print("⚠️ [COMPLETION] Could not get count from Supabase, falling back to default.")
                total_topics = 15
        except Exception as e:
            print(f"❌ [COMPLETION] Error getting scenario count from DB: {str(e)}")
            total_topics = 15 # Fallback
        
        # Get user's progress for stage 2, exercise 3
        progress_result = await progress_tracker.get_user_topic_progress(
            user_id=user_id,
            stage_id=2,
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
                "stage_id": 2,
                "exercise_id": 3,
                "exercise_name": "Roleplay Simulation",
                "stage_name": "Stage 2 – A2 Elementary",
                "error": progress_result.get("error", "Failed to get progress")
            }
        
        user_progress = progress_result.get("data", [])
        completed_topics = len([record for record in user_progress if record.get("completed", False)])
        
        # Get current topic ID
        current_topic_result = await progress_tracker.get_current_topic_for_exercise(
            user_id=user_id,
            stage_id=2,
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
            "stage_id": 2,
            "exercise_id": 3,
            "exercise_name": "Roleplay Simulation",
            "stage_name": "Stage 2 – A2 Elementary"
        }
        
    except Exception as e:
        print(f"❌ [COMPLETION] Error checking exercise completion: {str(e)}")
        return {
            "exercise_completed": False,
            "progress_percentage": 0.0,
            "completed_topics": 0,
            "total_topics": 0,
            "current_topic_id": 1,
            "stage_id": 2,
            "exercise_id": 3,
            "exercise_name": "Roleplay Simulation",
            "stage_name": "Stage 2 – A2 Elementary",
            "error": str(e)
        }


@router.get("/roleplay-scenarios", response_model=ScenariosResponse)
async def get_roleplay_scenarios(
    user_id: str, 
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)
):
    """
    Get all available roleplay scenarios with completion status for the user
    """
    print(f"🔄 [ROLEPLAY] GET /roleplay-scenarios called for user: {user_id}")
    
    # Validate user_id and ensure user can only access their own data
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    
    if user_id != current_user['id']:
        raise HTTPException(status_code=403, detail="You can only access your own data")
    
    try:
        # Get all scenarios
        scenarios = await get_all_scenarios_from_db()
        print(f"📊 [ROLEPLAY] Found {len(scenarios)} scenarios")
        
        # Get user's progress for stage 2, exercise 3
        user_progress = []
        try:
            progress_result = await progress_tracker.get_user_topic_progress(
                user_id=user_id,
                stage_id=2,
                exercise_id=3
            )
            if progress_result["success"]:
                user_progress = progress_result.get("data", [])
                print(f"📊 [ROLEPLAY] Found {len(user_progress)} progress records for user")
        except Exception as e:
            print(f"⚠️ [ROLEPLAY] Error getting user progress: {str(e)}")
        
        # Create progress lookup
        progress_lookup = {record["topic_id"]: record["completed"] for record in user_progress}
        
        # Build response with completion status
        scenario_responses = []
        for scenario in scenarios:
            is_completed = progress_lookup.get(scenario["id"], False)
            scenario_response = {
                "id": scenario["id"],
                "title": scenario["title"],
                "title_urdu": scenario["title_urdu"],
                "description": scenario["description"],
                "description_urdu": scenario["description_urdu"],
                "initial_prompt": scenario["initial_prompt"],
                "initial_prompt_urdu": scenario["initial_prompt_urdu"],
                "scenario_context": scenario["scenario_context"],
                "difficulty": scenario["difficulty"],
                "expected_keywords": scenario["expected_keywords"],
                "expected_keywords_urdu": scenario["expected_keywords_urdu"],
                "ai_character": scenario["ai_character"],
                "conversation_flow": scenario["conversation_flow"],
                "cultural_context": scenario["cultural_context"],
                "is_completed": is_completed
            }
            scenario_responses.append(scenario_response)
        
        print(f"✅ [ROLEPLAY] Returning {len(scenario_responses)} scenarios")
        return ScenariosResponse(
            scenarios=scenario_responses,
            total_count=len(scenario_responses)
        )
        
    except Exception as e:
        print(f"❌ [ROLEPLAY] Error getting scenarios: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get scenarios: {str(e)}")

@router.get("/roleplay-scenarios/{scenario_id}")
async def get_scenario_by_id(scenario_id: int, current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)):
    """
    Get specific scenario by ID
    """
    print(f"🔄 [ROLEPLAY] GET /roleplay-scenarios/{scenario_id} called")
    
    try:
        scenario = await get_scenario_by_id_from_db(scenario_id)
        if not scenario:
            raise HTTPException(status_code=404, detail="Scenario not found")
        
        print(f"✅ [ROLEPLAY] Found scenario: {scenario['title']}")
        return scenario
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [ROLEPLAY] Error getting scenario: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get scenario: {str(e)}")

@router.post("/roleplay/start", response_model=RoleplayResponse)
async def start_roleplay(
    request: RoleplayStartRequest,
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)
):
    """
    Start a new roleplay session for a specific scenario
    """
    print(f"🔄 [ROLEPLAY] POST /roleplay/start called for scenario: {request.scenario_id}")
    print(f"👤 [ROLEPLAY] User ID: {request.user_id}")
    
    # Validate user_id and ensure user can only access their own data
    if not request.user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    
    if request.user_id != current_user['id']:
        raise HTTPException(status_code=403, detail="You can only access your own data")
    
    try:
        # Get scenario
        scenario = await get_scenario_by_id_from_db(request.scenario_id)
        if not scenario:
            raise HTTPException(status_code=404, detail="Scenario not found")
        
        # Create session
        session_id, initial_prompt = roleplay_agent.create_session(scenario)
        
        # Generate audio for initial prompt
        audio_base64 = None
        try:
            audio_content = await roleplay_agent.generate_audio_for_response(initial_prompt)
            if audio_content:
                audio_base64 = base64.b64encode(audio_content).decode('utf-8')
                print(f"✅ [ROLEPLAY] Generated audio for initial prompt")
        except Exception as e:
            print(f"⚠️ [ROLEPLAY] Error generating audio: {str(e)}")
        
        print(f"✅ [ROLEPLAY] Session started: {session_id}")
        return RoleplayResponse(
            ai_response=initial_prompt,
            session_id=session_id,
            done=False,
            audio_base64=audio_base64,
            scenario_context=scenario["scenario_context"],
            ai_character=scenario["ai_character"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [ROLEPLAY] Error starting roleplay: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start roleplay: {str(e)}")

@router.post("/roleplay/respond", response_model=RoleplayResponse)
async def continue_roleplay(
    reply: RoleplayUserReply,
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)
):
    """
    Continue roleplay conversation with user input (text or audio)
    """
    print(f"🔄 [ROLEPLAY] POST /roleplay/respond called")
    print(f"📝 [ROLEPLAY] Session ID: {reply.session_id}")
    print(f"👤 [ROLEPLAY] User ID: {reply.user_id}")
    print(f"📝 [ROLEPLAY] Input type: {reply.input_type}")
    
    # Validate user_id and ensure user can only access their own data
    if not reply.user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    
    if reply.user_id != current_user['id']:
        raise HTTPException(status_code=403, detail="You can only access your own data")
    
    try:
        user_input = reply.user_input
        
        # Handle audio input
        if reply.input_type == "audio" and reply.audio_base64:
            print(f"🎤 [ROLEPLAY] Processing audio input")
            try:
                # Decode audio
                audio_data = base64.b64decode(reply.audio_base64)
                print(f"✅ [ROLEPLAY] Audio decoded, size: {len(audio_data)} bytes")
                
                # Transcribe audio
                transcription_result = transcribe_audio_bytes_eng_only(audio_data)
                user_input = transcription_result.get("text", "").strip()
                
                if not user_input:
                    raise HTTPException(status_code=400, detail="No speech detected in audio")
                
                print(f"✅ [ROLEPLAY] Audio transcribed: '{user_input}'")
                
            except Exception as e:
                print(f"❌ [ROLEPLAY] Error processing audio: {str(e)}")
                raise HTTPException(status_code=400, detail=f"Failed to process audio: {str(e)}")
        
        # Update session with user input
        ai_response, status, error = roleplay_agent.update_session(reply.session_id, user_input)
        
        if error:
            raise HTTPException(status_code=400, detail=error)
        
        # If conversation is done, don't mark as completed yet
        # Wait for user to explicitly request evaluation
        if status == "end":
            print(f"✅ [ROLEPLAY] Conversation ended. Waiting for user to request evaluation.")

        # Generate audio for AI response
        audio_base64 = None
        try:
            audio_content = await roleplay_agent.generate_audio_for_response(ai_response)
            if audio_content:
                audio_base64 = base64.b64encode(audio_content).decode('utf-8')
                print(f"✅ [ROLEPLAY] Generated audio for AI response")
        except Exception as e:
            print(f"⚠️ [ROLEPLAY] Error generating audio: {str(e)}")
        
        print(f"✅ [ROLEPLAY] Response generated, status: {status}")
        return RoleplayResponse(
            ai_response=ai_response,
            session_id=reply.session_id,
            done=(status == "end"),
            audio_base64=audio_base64
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [ROLEPLAY] Error continuing roleplay: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to continue roleplay: {str(e)}")

@router.get("/roleplay/history/{session_id}", response_model=ConversationHistoryResponse)
async def get_roleplay_history(session_id: str, current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)):
    """
    Get conversation history for a session
    """
    print(f"🔄 [ROLEPLAY] GET /roleplay/history/{session_id} called")
    
    try:
        # Get session data from Redis
        session_data_json = redis_client.get(session_id)
        if not session_data_json:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session_data = json.loads(session_data_json)
        history = session_data.get("history", [])
        
        # Get scenario info
        scenario_info = None
        if "scenario_id" in session_data:
            scenario = await get_scenario_by_id_from_db(session_data["scenario_id"])
            if scenario:
                scenario_info = {
                    "id": scenario["id"],
                    "title": scenario["title"],
                    "scenario_context": scenario["scenario_context"],
                    "ai_character": scenario["ai_character"]
                }
        
        print(f"✅ [ROLEPLAY] Retrieved history with {len(history)} messages")
        return ConversationHistoryResponse(
            session_id=session_id,
            history=history,
            scenario_info=scenario_info
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [ROLEPLAY] Error getting history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get history: {str(e)}")

@router.post("/roleplay/evaluate", response_model=RoleplayEvaluationResponse)
async def evaluate_roleplay_session(
    request: RoleplayEvaluationRequest, 
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher_or_student)
):
    """
    Evaluate a completed roleplay session
    """
    print(f"🔄 [ROLEPLAY] POST /roleplay/evaluate called")
    print(f"📝 [ROLEPLAY] Session ID: {request.session_id}")
    print(f"👤 [ROLEPLAY] User ID: {request.user_id}")
    print(f"⏱️ [ROLEPLAY] Time spent: {request.time_spent_seconds} seconds")
    
    # Validate user_id and ensure user can only access their own data
    if not request.user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    
    if request.user_id != current_user['id']:
        raise HTTPException(status_code=403, detail="You can only access your own data")
    
    try:
        # Get session data from Redis
        session_data_json = redis_client.get(request.session_id)
        if not session_data_json:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session_data = json.loads(session_data_json)
        history = session_data.get("history", [])
        
        if not history:
            raise HTTPException(status_code=400, detail="No conversation history found")
        
        # Get scenario info
        scenario = await get_scenario_by_id_from_db(session_data["scenario_id"])
        if not scenario:
            raise HTTPException(status_code=404, detail="Scenario not found")
        
        print(f"📊 [ROLEPLAY] Evaluating conversation with {len(history)} messages")
        print(f"🎯 [ROLEPLAY] Expected keywords: {scenario['expected_keywords']}")
        
        # Evaluate the conversation
        evaluation = evaluate_response_ex3_stage2(
            conversation_history=history,
            scenario_context=scenario["scenario_context"],
            expected_keywords=scenario["expected_keywords"],
            ai_character=scenario["ai_character"]
        )
        
        # Record progress in Supabase
        progress_recorded = False
        unlocked_content = []
        
        if request.user_id and request.user_id.strip():
            print(f"🔄 [ROLEPLAY] Recording progress for user: {request.user_id}")
            try:
                # Validate time spent
                time_spent = max(1, min(request.time_spent_seconds, 1800))  # Between 1-30 minutes
                
                # Record the topic attempt with actual evaluation results
                progress_result = await progress_tracker.record_topic_attempt(
                    user_id=request.user_id,
                    stage_id=2,  # Stage 2
                    exercise_id=3,  # Exercise 3 (Roleplay Simulation)
                    topic_id=scenario["db_id"],
                    score=float(evaluation.get("overall_score", 0)),
                    urdu_used=request.urdu_used,
                    time_spent_seconds=time_spent,
                    completed=True  # Mark as completed when user requests evaluation
                )
                
                if progress_result["success"]:
                    print(f"✅ [ROLEPLAY] Progress recorded successfully")
                    progress_recorded = True
                    
                    # Check for unlocked content
                    unlock_result = await progress_tracker.check_and_unlock_content(request.user_id)
                    if unlock_result["success"]:
                        unlocked_content = unlock_result.get("unlocked_content", [])
                        if unlocked_content:
                            print(f"🎉 [ROLEPLAY] Unlocked content: {unlocked_content}")
                else:
                    print(f"❌ [ROLEPLAY] Failed to record progress: {progress_result.get('error')}")
                    
            except Exception as e:
                print(f"❌ [ROLEPLAY] Error recording progress: {str(e)}")
                # Don't fail the entire request if progress tracking fails
        
        # Check exercise completion status
        exercise_completion_status = None
        if request.user_id and request.user_id.strip():
            try:
                exercise_completion_status = await check_exercise_completion(request.user_id)
                print(f"📊 [ROLEPLAY] Exercise completion status: {exercise_completion_status}")
            except Exception as completion_error:
                print(f"⚠️ [ROLEPLAY] Failed to check exercise completion: {str(completion_error)}")
                exercise_completion_status = {
                    "exercise_completed": False,
                    "progress_percentage": 0.0,
                    "completed_topics": 0,
                    "total_topics": 0,
                    "current_topic_id": 1,
                    "stage_id": 2,
                    "exercise_id": 3,
                    "exercise_name": "Roleplay Simulation",
                    "stage_name": "Stage 2 – A2 Elementary",
                    "error": str(completion_error)
                }
        
        # Clean up session from Redis
        try:
            roleplay_agent.delete_session(request.session_id)
            print(f"✅ [ROLEPLAY] Session cleaned up from Redis")
        except Exception as e:
            print(f"⚠️ [ROLEPLAY] Error cleaning up session: {str(e)}")
        
        print(f"✅ [ROLEPLAY] Evaluation completed successfully")
        return RoleplayEvaluationResponse(
            success=True,
            overall_score=evaluation.get("overall_score", 0),
            is_correct=evaluation.get("is_correct", False),
            completed=evaluation.get("completed", False),
            conversation_flow_score=evaluation.get("conversation_flow_score", 0),
            keyword_usage_score=evaluation.get("keyword_usage_score", 0),
            grammar_fluency_score=evaluation.get("grammar_fluency_score", 0),
            cultural_appropriateness_score=evaluation.get("cultural_appropriateness_score", 0),
            engagement_score=evaluation.get("engagement_score", 0),
            keyword_matches=evaluation.get("keyword_matches", []),
            total_keywords_expected=evaluation.get("total_keywords_expected", 0),
            keywords_used_count=evaluation.get("keywords_used_count", 0),
            grammar_errors=evaluation.get("grammar_errors", []),
            fluency_issues=evaluation.get("fluency_issues", []),
            strengths=evaluation.get("strengths", []),
            areas_for_improvement=evaluation.get("areas_for_improvement", []),
            suggested_improvement=evaluation.get("suggested_improvement", ""),
            conversation_quality=evaluation.get("conversation_quality", "needs_improvement"),
            learning_progress=evaluation.get("learning_progress", "none"),
            recommendations=evaluation.get("recommendations", []),
            progress_recorded=progress_recorded,
            unlocked_content=unlocked_content
        )
        
    except Exception as e:
        print(f"❌ [ROLEPLAY] Error evaluating roleplay: {str(e)}")
        
        # Check exercise completion status even for errors
        exercise_completion_status = None
        if request.user_id and request.user_id.strip():
            try:
                exercise_completion_status = await check_exercise_completion(request.user_id)
            except Exception as completion_error:
                print(f"⚠️ [ROLEPLAY] Failed to check exercise completion: {str(completion_error)}")
                exercise_completion_status = {
                    "exercise_completed": False,
                    "progress_percentage": 0.0,
                    "completed_topics": 0,
                    "total_topics": 0,
                    "current_topic_id": 1,
                    "stage_id": 2,
                    "exercise_id": 3,
                    "exercise_name": "Roleplay Simulation",
                    "stage_name": "Stage 2 – A2 Elementary",
                    "error": str(completion_error)
                }
        
        return RoleplayEvaluationResponse(
            success=False,
            overall_score=0,
            is_correct=False,
            completed=False,
            conversation_flow_score=0,
            keyword_usage_score=0,
            grammar_fluency_score=0,
            cultural_appropriateness_score=0,
            engagement_score=0,
            keyword_matches=[],
            total_keywords_expected=0,
            keywords_used_count=0,
            grammar_errors=[],
            fluency_issues=[],
            strengths=[],
            areas_for_improvement=[],
            suggested_improvement="Please try again later.",
            conversation_quality="needs_improvement",
            learning_progress="none",
            recommendations=["Retry after system restart"],
            progress_recorded=False,
            unlocked_content=[],
            error="evaluation_failed",
            message=f"Failed to evaluate roleplay: {str(e)}",
            exercise_completion=exercise_completion_status
        )