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

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.sql import text

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
    quiz_parser,
    gpt_quiz_parser,
    progress_tracking
)
from .database import get_db, engine


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

# Application lifecycle events
@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    print("🚀 [STARTUP] AI English Tutor Backend starting...")
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
    print("🛑 [SHUTDOWN] AI English Tutor Backend shutting down...")
    print("✅ [SHUTDOWN] Application shutdown complete")

# Include all API routers with proper organization
print("🚀 [MAIN] Initializing AI English Tutor API...")

# User management routes
app.include_router(user.router, prefix="/user", tags=["User Management"])

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
