"""
AI English Tutor Backend - Main Application

This is the main FastAPI application for the AI English Tutor system.
It provides comprehensive English learning features including:

- Progress Tracking System
- Learning Exercises (6 stages with multiple exercises)
- Real-time Conversation
- Translation Services
- Quiz and Assessment Tools
- English-Only AI Tutor (NEW)

Author: AI Tutor Development Team
Version: 1.0.0
"""

import logging
import asyncio
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

# Import all route modules
from app.routes import (
    conversation_ws,
    conversation_ws_2,
    english_only_ws,
    openai_realtime_ws,
    user,
    translator,
    repeat_after_me,
    quick_response,
    listen_and_reply,
    daily_routine,
    quick_answer,
    roleplay_simulation,
    storytelling,
    group_dialogue,
    problem_solving,
    abstract_topic,
    mock_interview,
    news_summary,
    critical_thinking,
    academic_presentation,
    in_depth_interview,
    spontaneous_speech,
    sensitive_scenario,
    critical_opinion_builder,
    quiz_parser,
    gpt_quiz_parser,
    progress_tracking,
    admin_dashboard,
    teacher_dashboard,
    messaging,
    auth,
    account_deletion
)
from .services.settings_manager import get_ai_settings
from .services.safety_manager import get_ai_safety_settings
from .supabase_client import progress_tracker, warmup_database_connections
from .cache import load_content_cache
from .services.connection_pool import connection_pool


from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel  
from gtts import gTTS
import io
from datetime import datetime

class TextRequest(BaseModel):
    text: str


app = FastAPI(
    title="AI English Tutor",
    description="An AI-powered English learning application designed for Urdu-speaking learners with comprehensive progress tracking and dynamic learning paths.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

origins = [
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging to suppress WebSocket debug logs
logging.getLogger("websockets").setLevel(logging.WARNING)
logging.getLogger("uvicorn.protocols.websockets").setLevel(logging.WARNING)
logging.getLogger("uvicorn.protocols.http.h11_impl").setLevel(logging.WARNING)
logging.getLogger("uvicorn.protocols.websocket").setLevel(logging.WARNING)
logging.getLogger("uvicorn.protocols.http").setLevel(logging.WARNING)
logging.getLogger("uvicorn.lifespan").setLevel(logging.WARNING)
logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

# Application lifecycle events
@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    print("🚀 [STARTUP] AI English Tutor Backend starting...")
    
    # Display API key information for verification
    import os
    from dotenv import load_dotenv
    load_dotenv()

    # Initialize pre-warmed connection pools
    print("🔥 [STARTUP] Initializing connection pools...")
    await connection_pool.initialize()
    
    api_key = os.getenv('OPENAI_API_KEY')
    if api_key:
        print(f"🔑 [STARTUP] OPENAI_API_KEY: {api_key[:15]}... (Length: {len(api_key)} chars)")
    else:
        print("❌ [STARTUP] OPENAI_API_KEY not found in environment variables!")

    # OPTIMIZATION: Warm up database connections first
    print("🔥 [STARTUP] Warming up database connections...")
    await warmup_database_connections()
    
    # OPTIMIZATION: Parallel initialization of all startup tasks
    print("⚙️ [STARTUP] Initializing all services in parallel...")
    await asyncio.gather(
        get_ai_settings(),
        get_ai_safety_settings(), 
        load_content_cache(progress_tracker)
    )
    
    print("📊 [STARTUP] Features enabled:")
    print("   - Progress Tracking System")
    print("   - Learning Exercises")
    print("   - Real-time Conversation")
    print("   - Translation Services")
    print("   - English-Only AI Tutor")
    print("✅ [STARTUP] Application started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    await connection_pool.close()
    print("🛑 [SHUTDOWN] AI English Tutor Backend shutting down...")
    print("✅ [SHUTDOWN] Application shutdown complete")

# Include all API routers with proper organization
print("🚀 [MAIN] Initializing AI English Tutor API...")

# User management and authentication
app.include_router(user.router, prefix="/api/user", tags=["User Management"])
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])

# Translation services
app.include_router(translator.router, prefix="/api/translate", tags=["Translation"])

# Learning exercise routes
app.include_router(repeat_after_me.router, prefix="/api", tags=["Stage 1 - Exercise 1 (Repeat After Me)"])
app.include_router(quick_response.router, prefix="/api", tags=["Stage 1 - Exercise 2 (Quick Response)"])
app.include_router(listen_and_reply.router, prefix="/api", tags=["Stage 1 - Exercise 3 (Listen and Reply)"])
app.include_router(daily_routine.router, prefix="/api", tags=["Stage 2 - Exercise 1 (Daily Routine)"])
app.include_router(quick_answer.router, prefix="/api", tags=["Stage 2 - Exercise 2 (Quick Answer)"])
app.include_router(roleplay_simulation.router, prefix="/api", tags=["Stage 2 - Exercise 3 (Roleplay Simulation)"])
app.include_router(storytelling.router, prefix="/api", tags=["Stage 3 - Exercise 1 (Storytelling)"])
app.include_router(group_dialogue.router, prefix="/api", tags=["Stage 3 - Exercise 2 (Group Dialogue)"])
app.include_router(problem_solving.router, prefix="/api", tags=["Stage 3 - Exercise 3 (Problem-Solving)"])
app.include_router(abstract_topic.router, prefix="/api", tags=["Stage 4 - Exercise 1 (Abstract Topic Monologue)"])
app.include_router(mock_interview.router, prefix="/api", tags=["Stage 4 - Exercise 2 (Mock Interview)"])
app.include_router(news_summary.router, prefix="/api", tags=["Stage 4 - Exercise 3 (News Summary)"])
app.include_router(critical_thinking.router, prefix="/api", tags=["Stage 5 - Exercise 1 (Critical Thinking Dialogues)"])
app.include_router(academic_presentation.router, prefix="/api", tags=["Stage 5 - Exercise 2 (Academic Presentation)"])
app.include_router(in_depth_interview.router, prefix="/api", tags=["Stage 5 - Exercise 3 (In-Depth Interview)"])
app.include_router(spontaneous_speech.router, prefix="/api", tags=["Stage 6 - Exercise 1 (Spontaneous Speech)"])
app.include_router(sensitive_scenario.router, prefix="/api", tags=["Stage 6 - Exercise 2 (Sensitive Scenario)"])
app.include_router(critical_opinion_builder.router, prefix="/api", tags=["Stage 6 - Exercise 3 (Critical Opinion Builder)"])
app.include_router(quiz_parser.router, prefix="/api", tags=["Quiz Parser"])

# Stage 2 exercises

# Quiz and assessment routes
app.include_router(gpt_quiz_parser.router, prefix="/api/quiz", tags=["Quiz & Assessment"])

# WebSocket routes for real-time communication
app.include_router(conversation_ws.router, prefix="/api", tags=["WebSocket - Conversation"])
app.include_router(conversation_ws_2.router, tags=["WebSocket - Conversation 2"])
app.include_router(english_only_ws.router, prefix="/api", tags=["WebSocket - English-Only AI Tutor"])
app.include_router(openai_realtime_ws.router, prefix="/api", tags=["WebSocket - OpenAI Realtime"])

# Progress tracking routes (NEW - Comprehensive Progress System)
app.include_router(progress_tracking.router, prefix="/api/progress", tags=["Progress Tracking"])

# Admin dashboard routes (NEW - Admin Dashboard System)
app.include_router(admin_dashboard.router, tags=["Admin Dashboard"])

# Teacher dashboard routes (NEW - Teacher Dashboard System)
app.include_router(teacher_dashboard.router, tags=["Teacher Dashboard"])

# Account deletion routes (NEW - Account Deletion System)
app.include_router(account_deletion.router, prefix="/api/account", tags=["Account Deletion"])

# Messaging system routes (NEW - Real-time Messaging)
app.include_router(messaging.router, prefix="/api", tags=["Messaging System"])

print("✅ [MAIN] All routers included successfully")

@app.post("/tts")
async def tts_generate_audio(data: TextRequest):
    # Generate the audio in memory
    tts = gTTS(text=data.text, lang='en')
    audio_buffer = io.BytesIO()
    tts.write_to_fp(audio_buffer)
    audio_buffer.seek(0)

    return StreamingResponse(audio_buffer, media_type="audio/mpeg")

@app.get("/api/healthcheck")
async def health_check():
    """Health check endpoint for API monitoring"""
    return {
        "status": "ok",
        "service": "ai_tutor_backend",
        "version": "1.0.0",
        "timestamp": "2025-01-20T10:00:00Z"
    }

@app.get("/health")
async def root_health_check():
    """Root health check endpoint"""
    return {
        "status": "healthy", 
        "service": "ai_tutor_backend",
        "version": "1.0.0",
        "features": [
            "progress_tracking",
            "learning_exercises", 
            "real_time_conversation",
            "translation_services",
            "english_only_tutor"
        ]
    }


@app.get("/api/status")
async def api_status():
    """Comprehensive API status endpoint"""
    return {
        "status": "operational",
        "service": "AI English Tutor Backend",
        "version": "1.0.0",
        "features": {
            "progress_tracking": "enabled",
            "learning_exercises": "enabled",
            "real_time_conversation": "enabled",
            "translation_services": "enabled",
            "english_only_tutor": "enabled",
            "database": "connected"
        },
        "endpoints": {
            "health": "/health",
            "api_health": "/api/healthcheck",
            "db_check": "/api/db-check",
            "docs": "/docs",
            "progress_tracking": "/api/progress/*",
            "english_only_tutor": "/api/ws/english-only"
        }
    }

@app.post("/api/warmup")
async def warmup_application():
    """Warm up application for optimal performance"""
    print("🔥 [WARMUP] Manual application warmup requested")
    try:
        # Warm up database connections
        await warmup_database_connections()
        
        # Warm up teacher dashboard endpoints
        from app.routes.teacher_dashboard import _get_behavior_insights, _get_learn_feature_engagement_summary
        
        # Pre-calculate common queries
        await asyncio.gather(
            _get_behavior_insights("all_time"),
            _get_learn_feature_engagement_summary("all_time")
        )
        
        return {
            "status": "success",
            "message": "Application warmed up successfully",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"❌ [WARMUP] Warmup failed: {str(e)}")
        return {
            "status": "error", 
            "message": f"Warmup failed: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }
 