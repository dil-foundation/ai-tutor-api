from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class RoleplayStartRequest(BaseModel):
    scenario_id: int
    user_id: str

class RoleplayUserReply(BaseModel):
    session_id: str
    user_input: str
    user_id: str
    input_type: str = "text"  # "text" or "audio"
    audio_base64: Optional[str] = None

class RoleplayResponse(BaseModel):
    ai_response: str
    session_id: str
    done: bool
    audio_base64: Optional[str] = None
    scenario_context: Optional[str] = None
    ai_character: Optional[str] = None

class RoleplayEvaluationRequest(BaseModel):
    session_id: str
    user_id: str
    time_spent_seconds: int
    urdu_used: bool = False

class RoleplayEvaluationResponse(BaseModel):
    success: bool
    overall_score: int
    is_correct: bool
    completed: bool
    conversation_flow_score: int
    keyword_usage_score: int
    grammar_fluency_score: int
    cultural_appropriateness_score: int
    engagement_score: int
    keyword_matches: List[str]
    total_keywords_expected: int
    keywords_used_count: int
    grammar_errors: List[str]
    fluency_issues: List[str]
    strengths: List[str]
    areas_for_improvement: List[str]
    suggested_improvement: str
    conversation_quality: str
    learning_progress: str
    recommendations: List[str]
    progress_recorded: bool = False
    unlocked_content: List[str] = []
    error: Optional[str] = None
    message: Optional[str] = None

class ScenarioInfo(BaseModel):
    id: int
    title: str
    title_urdu: str
    description: str
    description_urdu: str
    initial_prompt: str
    initial_prompt_urdu: str
    scenario_context: str
    difficulty: str
    expected_keywords: List[str]
    expected_keywords_urdu: List[str]
    ai_character: str
    conversation_flow: str
    cultural_context: str
    is_completed: bool = False

class ScenariosResponse(BaseModel):
    scenarios: List[ScenarioInfo]
    total_count: int

class ConversationHistoryResponse(BaseModel):
    session_id: str
    history: List[Dict[str, Any]]
    scenario_info: Optional[Dict[str, Any]] = None 