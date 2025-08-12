from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.database import get_db
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
from app.supabase_client import progress_tracker
from app.redis_client import redis_client
from app.auth_middleware import get_current_user, require_student,require_admin_or_teacher_or_student
import json
import base64
from typing import List, Dict, Any

router = APIRouter()

@router.get("/roleplay-scenarios", response_model=ScenariosResponse)
async def get_roleplay_scenarios(
    user_id: str, 
    db: Session = Depends(get_db),
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
        scenarios = roleplay_agent.get_all_scenarios()
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
        scenario = roleplay_agent.get_scenario_by_id(scenario_id)
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
        scenario = roleplay_agent.get_scenario_by_id(request.scenario_id)
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
            scenario = roleplay_agent.get_scenario_by_id(session_data["scenario_id"])
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
    db: Session = Depends(get_db),
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
        scenario = roleplay_agent.get_scenario_by_id(session_data["scenario_id"])
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
                    topic_id=scenario["id"],
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
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [ROLEPLAY] Error evaluating roleplay: {str(e)}")
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
            message=f"Failed to evaluate roleplay: {str(e)}"
        ) 