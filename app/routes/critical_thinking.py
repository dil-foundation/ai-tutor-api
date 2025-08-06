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
from app.services.feedback import evaluate_response_ex1_stage5
from app.supabase_client import progress_tracker
from app.auth_middleware import get_current_user, require_student

router = APIRouter()

CRITICAL_THINKING_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'stage5_exercise1.json')

class AudioEvaluationRequest(BaseModel):
    audio_base64: str
    topic_id: int
    filename: str
    user_id: str
    time_spent_seconds: int
    urdu_used: bool

def get_topic_by_id(topic_id: int):
    print(f"🔍 [TOPIC] Looking for topic with ID: {topic_id}")
    try:
        with open(CRITICAL_THINKING_FILE, 'r', encoding='utf-8') as f:
            topics = json.load(f)
            print(f"📖 [TOPIC] Loaded {len(topics)} topics from file")
            for topic in topics:
                if topic['id'] == topic_id:
                    print(f"✅ [TOPIC] Found topic: {topic['topic']}")
                    return topic
            print(f"❌ [TOPIC] Topic with ID {topic_id} not found")
            return None
    except Exception as e:
        print(f"❌ [TOPIC] Error reading topic file: {str(e)}")
        return None

@router.get("/critical-thinking-topics")
async def get_all_topics(current_user: Dict[str, Any] = Depends(require_student)):
    """Get all available topics for Critical Thinking Dialogues exercise"""
    print("🔄 [API] GET /critical-thinking-topics endpoint called")
    try:
        print(f"📁 [API] Reading topic file from: {CRITICAL_THINKING_FILE}")
        with open(CRITICAL_THINKING_FILE, 'r', encoding='utf-8') as f:
            topics = json.load(f)
        print(f"✅ [API] Successfully loaded {len(topics)} topics")
        return {"topics": topics}
    except Exception as e:
        print(f"❌ [API] Error in get_all_topics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to load topics: {str(e)}")

@router.get("/critical-thinking-topics/{topic_id}")
async def get_topic(topic_id: int, current_user: Dict[str, Any] = Depends(require_student)):
    """Get a specific topic by ID"""
    print(f"🔄 [API] GET /critical-thinking-topics/{topic_id} endpoint called")
    try:
        topic_data = get_topic_by_id(topic_id)
        if not topic_data:
            print(f"❌ [API] Topic {topic_id} not found")
            raise HTTPException(status_code=404, detail="Topic not found")
        print(f"✅ [API] Returning topic: {topic_data['topic']}")
        return {
            "id": topic_data['id'],
            "topic": topic_data['topic'],
            "topic_urdu": topic_data['topic_urdu'],
            "ai_position": topic_data['ai_position'],
            "ai_position_urdu": topic_data['ai_position_urdu'],
            "category": topic_data['category'],
            "difficulty": topic_data['difficulty'],
            "speaking_duration": topic_data['speaking_duration'],
            "thinking_time": topic_data['thinking_time'],
            "expected_structure": topic_data['expected_structure'],
            "expected_keywords": topic_data['expected_keywords'],
            "expected_keywords_urdu": topic_data['expected_keywords_urdu'],
            "vocabulary_focus": topic_data['vocabulary_focus'],
            "vocabulary_focus_urdu": topic_data['vocabulary_focus_urdu'],
            "model_response": topic_data['model_response'],
            "model_response_urdu": topic_data['model_response_urdu'],
            "evaluation_criteria": topic_data['evaluation_criteria'],
            "learning_objectives": topic_data['learning_objectives']
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [API] Error in get_topic: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post(
    "/critical-thinking/{topic_id}",
    summary="Convert topic to audio for Critical Thinking Dialogues Exercise",
    description="""
This endpoint is part of Stage 5 - Exercise 1 (Critical Thinking Dialogues). 
It takes a topic ID from a predefined list, converts the corresponding topic into speech (TTS),
and returns the generated audio file as the response.
""",
    tags=["Stage 5 - Exercise 1 (Critical Thinking Dialogues)"]
)
async def critical_thinking(topic_id: int, current_user: Dict[str, Any] = Depends(require_student)):
    print(f"🔄 [API] POST /critical-thinking/{topic_id} endpoint called")
    try:
        topic_data = get_topic_by_id(topic_id)
        if not topic_data:
            print(f"❌ [API] Topic {topic_id} not found")
            raise HTTPException(status_code=404, detail="Topic not found")
        
        # Create the topic text for audio generation
        topic_text = f"{topic_data['topic']}\n\nAI Position: {topic_data['ai_position']}"
        
        print(f"📝 [API] Generated topic text: {topic_text[:100]}...")
        
        # Generate audio using TTS
        print("🔄 [API] Generating audio...")
        audio_data = await synthesize_speech_exercises(topic_text)
        
        if not audio_data:
            print("❌ [API] Failed to generate audio")
            raise HTTPException(status_code=500, detail="Failed to generate audio")
        
        print("✅ [API] Audio generated successfully")
        
        # Convert to base64
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        return {
            "audio_base64": audio_base64,
            "topic_id": topic_id,
            "topic": topic_data['topic'],
            "topic_text": topic_text
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [API] Error in critical_thinking: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post(
    "/evaluate-critical-thinking",
    summary="Evaluate user's audio recording against expected critical thinking criteria",
    description="""
This endpoint evaluates the user's recorded audio against the expected critical thinking criteria for philosophical debate topics.
It performs speech-to-text conversion and provides comprehensive feedback on the response quality.
Also records progress tracking data in Supabase database.
""",
    tags=["Stage 5 - Exercise 1 (Critical Thinking Dialogues)"]
)
async def evaluate_critical_thinking(
    request: AudioEvaluationRequest,
    current_user: Dict[str, Any] = Depends(require_student)
):
    print(f"🔄 [API] POST /evaluate-critical-thinking endpoint called")
    print(f"📊 [API] Request details: topic_id={request.topic_id}, user_id={request.user_id}")
    
    # Validate user_id and ensure user can only access their own data
    if not request.user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    
    if request.user_id != current_user['id']:
        raise HTTPException(status_code=403, detail="You can only access your own data")
    
    try:
        # Get topic data
        topic_data = get_topic_by_id(request.topic_id)
        if not topic_data:
            print(f"❌ [API] Topic {request.topic_id} not found")
            raise HTTPException(status_code=404, detail="Topic not found")
        
        print(f"✅ [API] Found topic: {topic_data['topic']}")
        
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
            if not user_text or len(user_text) < 10:
                print(f"⚠️ [API] Transcription too short or empty: '{user_text}'")
                return {
                    "success": False,
                    "error": "no_speech_detected",
                    "message": "No clear speech detected. Please speak more clearly and provide a thoughtful response.",
                    "expected_keywords": topic_data['expected_keywords'],
                    "topic": topic_data['topic']
                }

        except Exception as e:
            print(f"❌ [API] Error transcribing audio: {str(e)}")
            return {
                "success": False,
                "error": "transcription_failed",
                "message": "Failed to process audio. Please try again.",
                "expected_keywords": topic_data['expected_keywords'],
                "topic": topic_data['topic']
            }
        
        # Evaluate the response
        try:
            print(f"🔄 [API] Evaluating response: '{user_text}' vs expected criteria")
            evaluation = evaluate_response_ex1_stage5(
                user_response=user_text,
                topic=topic_data['topic'],
                ai_position=topic_data['ai_position'],
                expected_keywords=topic_data['expected_keywords'],
                vocabulary_focus=topic_data['vocabulary_focus'],
                model_response=topic_data['model_response']
            )
            print(f"✅ [API] Evaluation completed: {evaluation}")
            
            # Extract evaluation details for progress tracking
            score = evaluation.get("evaluation", {}).get("overall_score", 0)
            is_correct = evaluation.get("evaluation", {}).get("is_correct", False)
            completed = evaluation.get("evaluation", {}).get("completed", False)
            suggested_improvement = evaluation.get("suggested_improvement", "")
            keyword_matches = evaluation.get("matched_keywords_count", 0)
            total_keywords = evaluation.get("total_keywords", 0)
            fluency_score = evaluation.get("fluency_score", 0)
            grammar_score = evaluation.get("grammar_score", 0)
            
            print(f"📊 [API] Evaluation details: score={score}, is_correct={is_correct}, completed={completed}")
            print(f"📊 [API] Raw evaluation structure: {evaluation}")
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
                    time_spent = max(1, min(request.time_spent_seconds, 600))  # Between 1-600 seconds for critical thinking
                    if time_spent != request.time_spent_seconds:
                        print(f"⚠️ [API] Adjusted time spent from {request.time_spent_seconds} to {time_spent} seconds")
                    
                    # Record the topic attempt
                    progress_result = await progress_tracker.record_topic_attempt(
                        user_id=request.user_id,
                        stage_id=5,  # Stage 5
                        exercise_id=1,  # Exercise 1 (Critical Thinking Dialogues)
                        topic_id=request.topic_id,
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
                "topic": topic_data['topic'],
                "expected_keywords": topic_data['expected_keywords'],
                "user_text": user_text,
                "evaluation": evaluation,
                "suggested_improvement": suggested_improvement,
                "progress_recorded": progress_recorded,
                "unlocked_content": unlocked_content,
                "keyword_matches": keyword_matches,
                "total_keywords": total_keywords,
                "fluency_score": fluency_score,
                "grammar_score": grammar_score,
                "argument_type": evaluation.get("argument_type", ""),
                "topic_title": topic_data['topic'],
                "topic_category": topic_data['category']
            }

        except Exception as e:
            print(f"❌ [API] Error evaluating response: {str(e)}")
            return {
                "success": False,
                "error": "evaluation_failed",
                "message": "Failed to evaluate response. Please try again.",
                "expected_keywords": topic_data['expected_keywords'],
                "topic": topic_data['topic'],
                "user_text": user_text
            }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [API] Error in evaluate_critical_thinking: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/critical-thinking-progress/{user_id}")
async def get_user_progress(
    user_id: str,
    current_user: Dict[str, Any] = Depends(require_student)
):
    """Get user's progress for Critical Thinking Dialogues exercise"""
    print(f"🔄 [API] GET /critical-thinking-progress/{user_id} endpoint called")
    
    # Ensure user can only access their own data
    if user_id != current_user['id']:
        raise HTTPException(status_code=403, detail="You can only access your own data")
    
    try:
        # Get topic progress for this specific exercise
        topic_progress = await progress_tracker.get_user_topic_progress(user_id, stage_id=5, exercise_id=1)
        
        # Get current topic
        current_topic = await progress_tracker.get_current_topic_for_exercise(user_id, stage_id=5, exercise_id=1)
        
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

@router.get("/critical-thinking-current-topic/{user_id}")
async def get_current_topic(
    user_id: str,
    current_user: Dict[str, Any] = Depends(require_student)
):
    """Get user's current topic for Critical Thinking Dialogues exercise"""
    print(f"🔄 [API] GET /critical-thinking-current-topic/{user_id} endpoint called")
    
    # Ensure user can only access their own data
    if user_id != current_user['id']:
        raise HTTPException(status_code=403, detail="You can only access your own data")
    
    try:
        topic_data = await progress_tracker.get_current_topic_for_exercise(user_id, stage_id=5, exercise_id=1)
        print(f"✅ [API] Current topic retrieved: {topic_data}")
        return topic_data
    except Exception as e:
        print(f"❌ [API] Error getting current topic: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get current topic: {str(e)}") 