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
import os
import json
import sys
from pathlib import Path
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

# Configure comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.StreamHandler(sys.stderr)
    ]
)

# Create logger for this module
logger = logging.getLogger(__name__)

# Print startup banner to ensure logs are visible
print("=" * 80)
print("🚀 AI ENGLISH TUTOR BACKEND STARTING UP")
print("=" * 80)
print(f"Python version: {sys.version}")
print(f"Working directory: {os.getcwd()}")
print(f"Environment variables loaded:")
for key in ['OPENAI_API_KEY', 'SUPABASE_URL', 'REDIS_HOST', 'ELEVEN_API_KEY']:
    value = os.getenv(key)
    if value:
        print(f"  ✅ {key}: {'*' * min(len(value), 10)}...")
    else:
        print(f"  ❌ {key}: NOT SET")
print("=" * 80)

# Setup Google credentials before importing modules that might need them
def setup_google_credentials():
    """Setup Google credentials from environment variable or file"""
    credentials_json = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')
    
    if credentials_json:
        # Create credentials file from environment variable
        credentials_dir = Path('/app/credentials')
        credentials_dir.mkdir(exist_ok=True)
        
        credentials_file = credentials_dir / 'google-credentials.json'
        with open(credentials_file, 'w') as f:
            f.write(credentials_json)
        
        # Set environment variable for Google client libraries
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(credentials_file)
        print("✅ Google credentials loaded from environment variable")
        return True
    else:
        # Check if file exists (for local development)
        credentials_file = '/app/credentials/google-credentials.json'
        if os.path.exists(credentials_file):
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_file
            print("✅ Google credentials loaded from file")
            return True
        else:
            print("⚠️ Google credentials not found")
            return False

# Setup credentials before imports
setup_google_credentials()

# Import all route modules
from app.routes import (
    conversation_ws,
    conversation_ws_2,
    english_only_ws,
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
    auth
)
from .services.settings_manager import get_ai_settings
from .services.safety_manager import get_ai_safety_settings


from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel  
from gtts import gTTS
import io

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
    logger.info("🚀 [STARTUP] AI English Tutor Backend starting...")
    
    # Log all environment variables for debugging
    print("🔍 [STARTUP] Environment Variables Check:")
    logger.info("🔍 [STARTUP] Environment Variables Check:")
    
    env_vars = [
        'OPENAI_API_KEY', 'SUPABASE_URL', 'SUPABASE_SERVICE_KEY',
        'ELEVEN_API_KEY', 'ELEVEN_VOICE_ID', 'REDIS_HOST', 'REDIS_PORT',
        'WP_SITE_URL', 'WP_API_USERNAME', 'WP_API_APPLICATION_PASSWORD',
        'GOOGLE_APPLICATION_CREDENTIALS_JSON', 'ENVIRONMENT'
    ]
    
    for var in env_vars:
        value = os.getenv(var)
        if value:
            masked_value = f"{'*' * min(len(value), 10)}..." if len(value) > 10 else "***"
            print(f"  ✅ {var}: {masked_value}")
            logger.info(f"  ✅ {var}: {masked_value}")
        else:
            print(f"  ❌ {var}: NOT SET")
            logger.warning(f"  ❌ {var}: NOT SET")

    # Try to initialize settings but don't fail startup if it fails
    try:
        print("⚙️ [STARTUP] Initializing AI Tutor settings...")
        logger.info("⚙️ [STARTUP] Initializing AI Tutor settings...")
        await get_ai_settings()
        print("✅ [STARTUP] AI Tutor settings initialized successfully")
        logger.info("✅ [STARTUP] AI Tutor settings initialized successfully")
    except Exception as e:
        print(f"⚠️ [STARTUP] Failed to initialize AI Tutor settings: {str(e)}")
        logger.error(f"⚠️ [STARTUP] Failed to initialize AI Tutor settings: {str(e)}")
        print("⚠️ [STARTUP] Continuing with default settings...")
        logger.warning("⚠️ [STARTUP] Continuing with default settings...")

    try:
        print("🛡️ [STARTUP] Initializing AI Safety & Ethics settings...")
        logger.info("🛡️ [STARTUP] Initializing AI Safety & Ethics settings...")
        await get_ai_safety_settings()
        print("✅ [STARTUP] AI Safety & Ethics settings initialized successfully")
        logger.info("✅ [STARTUP] AI Safety & Ethics settings initialized successfully")
    except Exception as e:
        print(f"⚠️ [STARTUP] Failed to initialize AI Safety & Ethics settings: {str(e)}")
        logger.error(f"⚠️ [STARTUP] Failed to initialize AI Safety & Ethics settings: {str(e)}")
        print("⚠️ [STARTUP] Continuing with default settings...")
        logger.warning("⚠️ [STARTUP] Continuing with default settings...")
    
    print("📊 [STARTUP] Features enabled:")
    logger.info("📊 [STARTUP] Features enabled:")
    features = [
        "Progress Tracking System",
        "Learning Exercises", 
        "Real-time Conversation",
        "Translation Services",
        "English-Only AI Tutor"
    ]
    
    for feature in features:
        print(f"   - {feature}")
        logger.info(f"   - {feature}")
    
    print("✅ [STARTUP] Application started successfully")
    logger.info("✅ [STARTUP] Application started successfully")
    print("🌐 [STARTUP] Server is ready to accept connections on port 8000")
    logger.info("🌐 [STARTUP] Server is ready to accept connections on port 8000")

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    print("🛑 [SHUTDOWN] AI English Tutor Backend shutting down...")
    print("✅ [SHUTDOWN] Application shutdown complete")

# Include all API routers with proper organization
print("🚀 [MAIN] Initializing AI English Tutor API...")

# User management and authentication
app.include_router(user.router, prefix="/user", tags=["User Management"])
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

# Progress tracking routes (NEW - Comprehensive Progress System)
app.include_router(progress_tracking.router, prefix="/api/progress", tags=["Progress Tracking"])

# Admin dashboard routes (NEW - Admin Dashboard System)
app.include_router(admin_dashboard.router, tags=["Admin Dashboard"])

# Teacher dashboard routes (NEW - Teacher Dashboard System)
app.include_router(teacher_dashboard.router, tags=["Teacher Dashboard"])

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
    """Root health check endpoint - simplified for ALB health checks"""
    return {"status": "ok"}

@app.get("/healthz")
async def kubernetes_health_check():
    """Kubernetes-style health check endpoint"""
    return {"status": "ok"}

@app.get("/")
async def root():
    """Root endpoint that can also serve as health check"""
    return {"message": "AI Tutor Backend is running", "status": "ok"}


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
 