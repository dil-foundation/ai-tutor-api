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
from app.services.feedback import evaluate_response_ex2_stage5
from app.supabase_client import progress_tracker
from app.auth_middleware import get_current_user, require_student

router = APIRouter()

ACADEMIC_PRESENTATION_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'stage5_exercise2.json')

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
        with open(ACADEMIC_PRESENTATION_FILE, 'r', encoding='utf-8') as f:
            topics = json.load(f)
            print(f"📖 [TOPIC] Loaded {len(topics)} topics from file")
            for topic in topics:
                if topic['id'] == topic_id:
                    print(f"✅ [TOPIC] Found topic: {topic['topic']}")
                    return topic  # Return the full topic object
            print(f"❌ [TOPIC] Topic with ID {topic_id} not found")
            return None
    except Exception as e:
        print(f"❌ [TOPIC] Error reading topic file: {str(e)}")
        return None

@router.get("/academic-presentation-topics")
async def get_all_topics(current_user: Dict[str, Any] = Depends(require_student)):
    """Get all available topics for Academic Presentation exercise"""
    print("🔄 [API] GET /academic-presentation-topics endpoint called")
    try:
        print(f"📁 [API] Reading topic file from: {ACADEMIC_PRESENTATION_FILE}")
        with open(ACADEMIC_PRESENTATION_FILE, 'r', encoding='utf-8') as f:
            topics = json.load(f)
        print(f"✅ [API] Successfully loaded {len(topics)} topics")
        return {"topics": topics}
    except Exception as e:
        print(f"❌ [API] Error in get_all_topics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to load topics: {str(e)}")

@router.get("/academic-presentation-topics/{topic_id}")
async def get_topic(topic_id: int, current_user: Dict[str, Any] = Depends(require_student)):
    """Get a specific topic by ID"""
    print(f"🔄 [API] GET /academic-presentation-topics/{topic_id} endpoint called")
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
    "/academic-presentation/{topic_id}",
    summary="Convert topic to audio for Academic Presentation Exercise",
    description="""
This endpoint is part of Stage 5 - Exercise 2 (Academic Presentation). 
It takes a topic ID from a predefined list, converts the corresponding topic into speech (TTS),
and returns the generated audio file as the response.
""",
    tags=["Stage 5 - Exercise 2 (Academic Presentation)"]
)
async def academic_presentation(topic_id: int, current_user: Dict[str, Any] = Depends(require_student)):
    print(f"🔄 [API] POST /academic-presentation/{topic_id} endpoint called")
    try:
        topic_data = get_topic_by_id(topic_id)
        if not topic_data:
            print(f"❌ [API] Topic {topic_id} not found")
            raise HTTPException(status_code=404, detail="Topic not found")

        topic_text = topic_data['topic']
        print(f"🎤 [API] Converting topic to speech: '{topic_text}'")
        audio_content = await synthesize_speech_exercises(topic_text)
        print(f"✅ [API] Audio content generated, size: {len(audio_content)} bytes")
        
        # Convert to base64 for React Native compatibility
        audio_base64 = base64.b64encode(audio_content).decode('utf-8')
        print(f"✅ [API] Audio converted to base64, length: {len(audio_base64)}")
        
        # Return base64 string directly
        return {"audio_base64": audio_base64}
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [API] Error in academic_presentation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post(
    "/evaluate-academic-presentation",
    summary="Evaluate user's academic presentation against expected structure and content",
    description="""
This endpoint evaluates the user's recorded academic presentation against the expected structure, 
keywords, and academic presentation criteria. It performs speech-to-text conversion and provides 
comprehensive feedback on the presentation quality, argument structure, and academic tone.
Also records progress tracking data in Supabase database.
""",
    tags=["Stage 5 - Exercise 2 (Academic Presentation)"]
)
async def evaluate_academic_presentation(
    request: AudioEvaluationRequest,
    current_user: Dict[str, Any] = Depends(require_student)
):
    print(f"🔄 [API] POST /evaluate-academic-presentation endpoint called")
    print(f"📝 [API] Request details: topic_id={request.topic_id}, filename={request.filename}")
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
        # Get the expected topic and keywords
        topic_data = get_topic_by_id(request.topic_id)
        if not topic_data:
            print(f"❌ [API] Topic {request.topic_id} not found")
            raise HTTPException(status_code=404, detail="Topic not found")

        expected_keywords = topic_data['expected_keywords']
        topic_text = topic_data['topic']
        topic_urdu = topic_data['topic_urdu']
        model_response = topic_data['model_response']
        expected_structure = topic_data['expected_structure']
        vocabulary_focus = topic_data['vocabulary_focus']
        print(f"✅ [API] Expected keywords: {expected_keywords}")
        print(f"✅ [API] Topic: '{topic_text}'")
        print(f"✅ [API] Expected structure: '{expected_structure}'")
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
        if len(audio_bytes) < 2000:  # Less than 2KB indicates very short/silent audio for 3-minute presentation
            print(f"⚠️ [API] Audio too short ({len(audio_bytes)} bytes), likely silent")
            return {
                "success": False,
                "error": "no_speech_detected",
                "message": "No speech detected. Please try again with a longer presentation.",
                "expected_keywords": expected_keywords,
                "topic": topic_text
            }

        # Transcribe the audio
        try:
            print("🔄 [API] Transcribing audio...")
            transcription_result = transcribe_audio_bytes_eng_only(audio_bytes)
            user_text = transcription_result.get("text", "").strip()
            print(f"✅ [API] Transcription result: '{user_text}'")
            
            # Check if transcription is empty or too short for academic presentation
            if not user_text or len(user_text) < 20:
                print(f"⚠️ [API] Transcription too short or empty: '{user_text}'")
                return {
                    "success": False,
                    "error": "no_speech_detected",
                    "message": "No clear speech detected. Please speak more clearly and deliver a complete academic presentation.",
                    "expected_keywords": expected_keywords,
                    "topic": topic_text
                }

        except Exception as e:
            print(f"❌ [API] Error transcribing audio: {str(e)}")
            return {
                "success": False,
                "error": "transcription_failed",
                "message": "Failed to process audio. Please try again.",
                "expected_keywords": expected_keywords,
                "topic": topic_text
            }

        # Evaluate the response
        try:
            print(f"🔄 [API] Evaluating academic presentation: '{user_text}' vs expected keywords: {expected_keywords}")
            evaluation = evaluate_response_ex2_stage5(user_text, topic_text, expected_keywords, vocabulary_focus, model_response, expected_structure)
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
            argument_structure_score = evaluation.get("argument_structure_score", 0)
            academic_tone_score = evaluation.get("academic_tone_score", 0)
            
            print(f"📊 [API] Evaluation details: score={score}, is_correct={is_correct}, completed={completed}")
            print(f"📊 [API] Keyword matches: {keyword_matches}/{total_keywords}")
            print(f"📊 [API] Fluency score: {fluency_score}, Grammar score: {grammar_score}")
            print(f"📊 [API] Argument structure score: {argument_structure_score}, Academic tone score: {academic_tone_score}")
            
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
                    # Validate time spent (should be reasonable for 3-minute presentation)
                    time_spent = max(30, min(request.time_spent_seconds, 300))  # Between 30-300 seconds for academic presentation
                    if time_spent != request.time_spent_seconds:
                        print(f"⚠️ [API] Adjusted time spent from {request.time_spent_seconds} to {time_spent} seconds")
                    
                    # Record the topic attempt
                    progress_result = await progress_tracker.record_topic_attempt(
                        user_id=request.user_id,
                        stage_id=5,  # Stage 5
                        exercise_id=2,  # Exercise 2 (Academic Presentation)
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
                "topic": topic_text,
                "expected_keywords": expected_keywords,
                "user_text": user_text,
                "evaluation": evaluation,
                "suggested_improvement": suggested_improvement,
                "progress_recorded": progress_recorded,
                "unlocked_content": unlocked_content,
                "keyword_matches": keyword_matches,
                "total_keywords": total_keywords,
                "fluency_score": fluency_score,
                "grammar_score": grammar_score,
                "argument_structure_score": argument_structure_score,
                "academic_tone_score": academic_tone_score
            }

        except Exception as e:
            print(f"❌ [API] Error evaluating response: {str(e)}")
            return {
                "success": False,
                "error": "evaluation_failed",
                "message": "Failed to evaluate response. Please try again.",
                "expected_keywords": expected_keywords,
                "topic": topic_text,
                "user_text": user_text
            }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [API] Unexpected error in evaluate_academic_presentation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}") 