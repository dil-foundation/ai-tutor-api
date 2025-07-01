from fastapi import APIRouter, HTTPException
from app.schemas.roleplay import RoleplayStartRequest, RoleplayUserReply, RoleplayResponse,RoleplayEvaluationResponse
from app.services import roleplay_agent
from app.redis_client import redis
import json

router = APIRouter()

@router.post("/roleplay/start", response_model=RoleplayResponse)
async def start_roleplay(request: RoleplayStartRequest):
    scenario = roleplay_agent.get_scenario_by_id(request.scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    session_id, prompt = roleplay_agent.create_session(scenario)
    return RoleplayResponse(ai_response=prompt, session_id=session_id, done=False)

@router.post("/roleplay/respond", response_model=RoleplayResponse)
async def continue_roleplay(reply: RoleplayUserReply):
    ai_response, status, error = roleplay_agent.update_session(reply.session_id, reply.user_input)

    if error:
        raise HTTPException(status_code=400, detail=error)

    return RoleplayResponse(
        ai_response=ai_response,
        session_id=reply.session_id,
        done=(status == "end")
    )

@router.get("/roleplay/history/{session_id}")
async def get_roleplay_history(session_id: str):
    history_json = redis.get(session_id)
    if not history_json:
        raise HTTPException(status_code=404, detail="Session not found")

    history = json.loads(history_json)
    return {"session_id": session_id, "history": history}


@router.get("/roleplay/evaluate/{session_id}", response_model=RoleplayEvaluationResponse)
async def evaluate_chat_session(session_id: str):
    session_data_json = redis.get(session_id)
    if not session_data_json:
        raise HTTPException(status_code=404, detail="Session not found")

    session_data = json.loads(session_data_json)
    history = session_data.get("history", [])

    result = roleplay_agent.evaluate_conversation(history)
    return result