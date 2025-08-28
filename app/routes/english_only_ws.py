"""
Enhanced English-Only AI Tutor WebSocket Handler

This module provides a ChatGPT-like voice mode experience for English learning with:
- Consistent Urdu-to-English correction for every response
- Separate logic flows for Vocabulary, Sentence Structure, and Topics
- Fallback to normal NLP conversation outside learning areas
- Professional error handling and edge case management
- Multi-stage conversation management with intelligent routing
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.tts import synthesize_speech_bytes, synthesize_speech_bytes_slow
from app.services.feedback import analyze_english_input_eng_only
from app.services import stt
from app.utils.profiler import Profiler
import json
import base64
import asyncio
from concurrent.futures import ThreadPoolExecutor
import httpx
from typing import Dict, Any, Optional

router = APIRouter()

# Global thread pool for CPU-intensive tasks
thread_pool = ThreadPoolExecutor(max_workers=10)

# Enhanced TTS cache with metadata
tts_cache: Dict[str, Dict[str, Any]] = {}

# Connection pool for HTTP clients
http_client = None

def get_http_client():
    global http_client
    if http_client is None:
        http_client = httpx.AsyncClient(timeout=30.0)
    return http_client

async def safe_send_json(websocket: WebSocket, data: dict):
    """Safely send JSON data with error handling"""
    try:
        await websocket.send_json(data)
        print(f"✅ [WEBSOCKET] JSON sent successfully: {data.get('step', 'unknown')}")
    except Exception as e:
        print(f"❌ [WEBSOCKET] Failed to send JSON: {e}")

async def safe_send_bytes(websocket: WebSocket, data: bytes):
    """Safely send binary data with error handling"""
    try:
        await websocket.send_bytes(data)
        print(f"✅ [WEBSOCKET] Audio bytes sent successfully: {len(data)} bytes")
    except Exception as e:
        print(f"❌ [WEBSOCKET] Failed to send binary: {e}")

# Async wrapper for CPU-intensive STT
async def async_transcribe_audio_eng_only(audio_bytes: bytes):
    """Run English-Only STT in thread pool to avoid blocking"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        thread_pool, 
        stt.transcribe_audio_bytes_eng_only, 
        audio_bytes
    )

# Async wrapper for English feedback analysis with enhanced stage management
async def async_analyze_english_input(user_text: str, stage: str, topic: str = None):
    """Run English analysis in thread pool with enhanced stage management"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        thread_pool,
        analyze_english_input_eng_only,
        user_text,
        stage,
        topic
    )

# Enhanced TTS caching with metadata
async def get_cached_or_generate_tts(text: str, use_slow_tts: bool = False) -> bytes:
    """Get TTS audio from cache or generate new with metadata tracking"""
    cache_key = f"{text}_{'slow' if use_slow_tts else 'normal'}"
    
    if cache_key in tts_cache:
        print(f"🎵 [TTS] Using cached audio for: '{text[:50]}...'")
        return tts_cache[cache_key]['audio']
    
    try:
        print(f"🎵 [TTS] Generating new audio for: '{text[:50]}...'")
        if use_slow_tts:
            audio = await synthesize_speech_bytes_slow(text)
        else:
            audio = await synthesize_speech_bytes(text)
        
        # Cache with metadata
        tts_cache[cache_key] = {
            'audio': audio,
            'text': text,
            'tts_type': 'slow' if use_slow_tts else 'normal',
            'cache_time': asyncio.get_event_loop().time(),
            'size_bytes': len(audio)
        }
        
        # Limit cache size to prevent memory issues
        if len(tts_cache) > 100:
            # Remove oldest entries
            oldest_keys = sorted(tts_cache.keys(), 
                               key=lambda k: tts_cache[k]['cache_time'])[:20]
            for key in oldest_keys:
                del tts_cache[key]
            print(f"🧹 [TTS] Cache cleaned, removed 20 oldest entries")
        
        return audio
        
    except Exception as e:
        print(f"❌ [TTS] Error generating audio: {e}")
        # Return empty audio as fallback
        return b''

@router.websocket("/ws/english-only")
async def english_only_conversation(websocket: WebSocket):
    """Enhanced WebSocket handler with multi-stage conversation management"""
    await websocket.accept()
    profiler = Profiler()
    
    # Enhanced state management
    conversation_state = {
        "stage": "greeting",
        "topic": None,
        "user_name": "there",
        "session_start": asyncio.get_event_loop().time(),
        "interaction_count": 0,
        "last_stage_change": asyncio.get_event_loop().time(),
        "learning_path": None,
        "skill_level": "unknown",
        "preferred_language": "english"
    }
    
    print(f"🚀 [WEBSOCKET] New English-Only session started for user: {conversation_state['user_name']}")

    try:
        while True:
            # Step 1: Receive message data
            data = await websocket.receive_text()
            profiler.mark("📥 Received message")
            conversation_state["interaction_count"] += 1

            try:
                message = json.loads(data)
                message_type = message.get("type")
                user_name = message.get("user_name", conversation_state["user_name"])
                conversation_state["user_name"] = user_name
                
            except json.JSONDecodeError as e:
                print(f"❌ [WEBSOCKET] JSON decode error: {e}")
                await safe_send_json(websocket, {
                    "response": "I'm having trouble understanding that message. Please try again.",
                    "step": "error",
                    "error_type": "json_decode"
                })
                continue
            
            # Handle different message types with enhanced logic
            if message_type == "greeting":
                await _handle_greeting_message(websocket, message, conversation_state, profiler)
                continue
                
            elif message_type == "prolonged_pause":
                await _handle_prolonged_pause_message(websocket, message, conversation_state, profiler)
                continue

            elif message_type == "user_silent_after_ai":
                await _handle_user_silent_message(websocket, message, conversation_state, profiler)
                continue

            elif message_type == "no_speech_detected":
                await _handle_no_speech_message(websocket, message, conversation_state, profiler)
                continue

            elif message_type == "processing_started":
                await _handle_processing_started_message(websocket, message, conversation_state, profiler)
                continue

            # Main audio processing block
            await _handle_audio_processing(websocket, message, conversation_state, profiler)
            
    except WebSocketDisconnect:
        print(f"🔌 [WEBSOCKET] Client disconnected: {conversation_state['user_name']}")
    except Exception as e:
        print(f"❌ [WEBSOCKET] Unexpected error: {e}")
        # Try to send error response before closing
        try:
            await safe_send_json(websocket, {
                "response": "I'm experiencing a technical difficulty. Please try reconnecting.",
                "step": "error",
                "error_type": "unexpected_error"
            })
        except:
            pass
    finally:
        print(f"🏁 [WEBSOCKET] Session ended for user: {conversation_state['user_name']}")
        print(f"📊 Session stats: {conversation_state['interaction_count']} interactions, "
              f"duration: {asyncio.get_event_loop().time() - conversation_state['session_start']:.1f}s")

async def _handle_greeting_message(websocket: WebSocket, message: dict, 
                                 conversation_state: dict, profiler: Profiler):
    """Handle greeting message with enhanced stage management"""
    print(f"👋 [GREETING] Processing greeting for user: {conversation_state['user_name']}")
    
    # Update conversation state
    conversation_state["stage"] = "intent_detection"
    conversation_state["last_stage_change"] = asyncio.get_event_loop().time()
    conversation_state["learning_path"] = None
    conversation_state["skill_level"] = "unknown"
    
    user_name = message.get("user_name", "there")
    greeting_text = f"Hi {user_name}, I'm your AI English tutor. I can help you with Vocabulary, Sentence Structure, Grammar, Topic Discussion, and Pronunciation Practice. What would you like to learn today?"
    
    # Generate greeting audio
    greeting_audio = await get_cached_or_generate_tts(greeting_text)
    profiler.mark("👋 Greeting generated")
    
    # Send enhanced response
    await safe_send_json(websocket, {
        "response": greeting_text,
        "step": "greeting",
        "user_name": user_name,
        "conversation_stage": conversation_state["stage"],
        "available_options": ["Vocabulary", "Sentence Structure", "Grammar", "Topic Discussion", "Pronunciation"],
        "session_id": id(websocket)
    })
    
    await safe_send_bytes(websocket, greeting_audio)

async def _handle_prolonged_pause_message(websocket: WebSocket, message: dict, 
                                        conversation_state: dict, profiler: Profiler):
    """Handle prolonged pause with context-aware response"""
    user_name = message.get("user_name", "there")
    
    # Context-aware pause response based on current stage
    if conversation_state["stage"] in ["vocabulary_learning", "sentence_practice", "topic_discussion"]:
        pause_text = f"Would you like to continue learning about {conversation_state['topic'] or 'this topic'}, or would you prefer to try something else, {user_name}?"
    else:
        pause_text = f"Would you like to learn anything else, {user_name}? I'm here to help!"
    
    pause_audio = await get_cached_or_generate_tts(pause_text)
    
    await safe_send_json(websocket, {
        "response": pause_text, 
        "step": "pause_detected", 
        "user_name": user_name,
        "conversation_stage": conversation_state["stage"],
        "current_topic": conversation_state["topic"]
    })
    await safe_send_bytes(websocket, pause_audio)

async def _handle_user_silent_message(websocket: WebSocket, message: dict, 
                                    conversation_state: dict, profiler: Profiler):
    """Handle user silent after AI with personalized reminder"""
    user_name = message.get("user_name", "there")
    
    # Personalized reminder based on learning context
    if conversation_state["learning_path"]:
        reminder_text = f"Are you still there, {user_name}? We were working on {conversation_state['learning_path']}. Would you like to continue?"
    else:
        reminder_text = f"Are you still there, {user_name}? I'm ready to help you learn English!"
    
    reminder_audio = await get_cached_or_generate_tts(reminder_text)
    
    await safe_send_json(websocket, {
        "response": reminder_text, 
        "step": "user_reminded", 
        "user_name": user_name,
        "conversation_stage": conversation_state["stage"],
        "learning_path": conversation_state["learning_path"]
    })
    await safe_send_bytes(websocket, reminder_audio)

async def _handle_no_speech_message(websocket: WebSocket, message: dict, 
                                  conversation_state: dict, profiler: Profiler):
    """Handle no speech detected with context-aware response"""
    no_speech_text = f"I didn't catch that. Could you please repeat, {conversation_state['user_name']}?"
    no_speech_audio = await get_cached_or_generate_tts(no_speech_text)
    
    await safe_send_json(websocket, {
        "response": no_speech_text, 
        "step": "no_speech_detected",
        "conversation_stage": conversation_state["stage"]
    })
    await safe_send_bytes(websocket, no_speech_audio)

async def _handle_processing_started_message(websocket: WebSocket, message: dict, 
                                           conversation_state: dict, profiler: Profiler):
    """Handle processing started with encouraging feedback"""
    processing_text = "Great! I'm listening and processing your speech."
    processing_audio = await get_cached_or_generate_tts(processing_text)
    
    await safe_send_json(websocket, {
        "response": processing_text, 
        "step": "processing_started",
        "conversation_stage": conversation_state["stage"]
    })
    await safe_send_bytes(websocket, processing_audio)

async def _handle_audio_processing(websocket: WebSocket, message: dict, 
                                 conversation_state: dict, profiler: Profiler):
    """Handle main audio processing with enhanced stage management"""
    audio_base64 = message.get("audio_base64")
    user_name = message.get("user_name", conversation_state["user_name"])

    if not audio_base64:
        print("⚠️ [AUDIO] No audio data received")
        return

    try:
        # Decode audio
        audio_bytes = await asyncio.get_event_loop().run_in_executor(
            thread_pool, base64.b64decode, audio_base64
        )
        profiler.mark("🎙️ Audio decoded")

        # Transcribe audio
        transcription_result = await async_transcribe_audio_eng_only(audio_bytes)
        transcribed_text = transcription_result["text"]
        profiler.mark("📝 STT completed")

        if not transcribed_text.strip():
            await _handle_empty_transcription(websocket, user_name, conversation_state, profiler)
            return
        
        print(f"🔍 [ENGLISH_ONLY] Processing: '{transcribed_text}' at stage: {conversation_state['stage']}")

        # Analyze with enhanced stage management
        analysis_result = await async_analyze_english_input(
            user_text=transcribed_text,
            stage=conversation_state["stage"],
            topic=conversation_state["topic"]
        )
        profiler.mark("🧠 AI analysis completed")

        # Update conversation state based on AI response
        await _update_conversation_state(conversation_state, analysis_result, transcribed_text)
        
        # Generate TTS response
        conversation_text = analysis_result.get("conversation_text", "Let's continue.")
        response_audio = await get_cached_or_generate_tts(conversation_text, use_slow_tts=True)
        profiler.mark("🔊 TTS response generated")

        # Send enhanced response with full context
        await safe_send_json(websocket, {
            "response": conversation_text,
            "conversation_text": conversation_text,
            "step": conversation_state["stage"],
            "original_text": transcribed_text,
            "user_name": user_name,
            "conversation_stage": conversation_state["stage"],
            "current_topic": conversation_state["topic"],
            "learning_path": conversation_state["learning_path"],
            "skill_level": conversation_state["skill_level"],
            "analysis": {
                "next_stage": analysis_result.get("next_stage"),
                "current_topic": conversation_state["topic"],
                "needs_correction": analysis_result.get("needs_correction", False),
                "correction_type": analysis_result.get("correction_type", "none"),
                "learning_activity": analysis_result.get("learning_activity"),
                "session_progress": analysis_result.get("session_progress")
            }
        })
        
        await safe_send_bytes(websocket, response_audio)
        profiler.summary()

    except Exception as e:
        print(f"❌ [AUDIO] Error processing audio: {e}")
        await _handle_audio_processing_error(websocket, user_name, conversation_state, e)

async def _handle_empty_transcription(websocket: WebSocket, user_name: str, 
                                    conversation_state: dict, profiler: Profiler):
    """Handle empty transcription with context-aware response"""
    no_speech_text = f"I didn't catch that. Could you please repeat, {user_name}?"
    no_speech_audio = await get_cached_or_generate_tts(no_speech_text)
    
    await safe_send_json(websocket, {
        "response": no_speech_text, 
        "step": "no_speech_detected_after_processing",
        "conversation_stage": conversation_state["stage"]
    })
    await safe_send_bytes(websocket, no_speech_audio)

async def _update_conversation_state(conversation_state: dict, analysis_result: dict, 
                                   original_text: str):
    """Update conversation state based on AI analysis"""
    # Update stage
    new_stage = analysis_result.get("next_stage")
    if new_stage and new_stage != conversation_state["stage"]:
        old_stage = conversation_state["stage"]
        conversation_state["stage"] = new_stage
        conversation_state["last_stage_change"] = asyncio.get_event_loop().time()
        print(f"🔄 [STATE] Stage transition: {old_stage} → {new_stage}")
    
    # Update topic if provided
    extracted_topic = analysis_result.get("extracted_topic")
    if extracted_topic:
        conversation_state["topic"] = extracted_topic
        print(f"📚 [STATE] Topic updated: {extracted_topic}")
    
    # Update learning path
    if new_stage in ["vocabulary_learning", "sentence_practice", "topic_discussion", "grammar_focus"]:
        conversation_state["learning_path"] = new_stage
        print(f"🎯 [STATE] Learning path set: {new_stage}")
    
    # Update skill level if detected
    skill_assessment = analysis_result.get("skill_assessment")
    if skill_assessment:
        conversation_state["skill_level"] = skill_assessment
        print(f"📊 [STATE] Skill level assessed: {skill_assessment}")
    
    # Log state update
    print(f"📝 [STATE] Updated state: stage={conversation_state['stage']}, "
          f"topic={conversation_state['topic']}, path={conversation_state['learning_path']}")

async def _handle_audio_processing_error(websocket: WebSocket, user_name: str, 
                                       conversation_state: dict, error: Exception):
    """Handle audio processing errors gracefully"""
    error_text = f"I'm having trouble processing that right now. Let's continue our conversation, {user_name}!"
    error_audio = await get_cached_or_generate_tts(error_text)
    
    await safe_send_json(websocket, {
        "response": error_text,
        "step": "error",
        "error_type": "audio_processing",
        "conversation_stage": conversation_state["stage"]
    })
    await safe_send_bytes(websocket, error_audio)