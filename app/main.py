from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from app.routes import conversation_ws

from app.routes import user
from app.routes import translator
from app.routes import repeat_after_me, quick_response, quiz_parser, gpt_quiz_parser, daily_routine, question_answer_wh, roleplay_simulation
from .database import get_db, engine


from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from gtts import gTTS
import io

class TextRequest(BaseModel):
    text: str


app = FastAPI(title="AI English Tutor",
    description="An AI-powered English learning application designed for Urdu-speaking learners.",
    version="1.0.0")

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

# Include the routers
app.include_router(user.router, prefix="/user")
app.include_router(translator.router, prefix="/api/translate")
app.include_router(repeat_after_me.router, prefix="/api")
app.include_router(quick_response.router, prefix="/api")
app.include_router(quiz_parser.router, prefix="/api")
app.include_router(daily_routine.router, prefix="/api", tags=["Stage 2 - Exercise 1 (Daily Routine Narration)"])
app.include_router(question_answer_wh.router,prefix="/api", tags=["Stage 2 - Exercise 2 (Questions & Answers Practice - Responding to WH-questions)"])
app.include_router(roleplay_simulation.router,prefix="/api", tags=["Stage 2 - Exercise 3 (Roleplay Simulation)"])
app.include_router(gpt_quiz_parser.router, prefix="/api/quiz")
app.include_router(conversation_ws.router, prefix="/api")

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
    return {"status": "ok"}

@app.get("/api/db-check")
def db_check(db: Session = Depends(get_db)):
    try:
        result = db.execute(text("SELECT 1"))
        row = result.fetchone()
        if row and row[0] == 1:
            return {"db_status": "ok", "result": row[0]}
        else:
            return {"db_status": "error", "detail": "Query did not return 1"}
    except Exception as e:
        return {"db_status": "error", "detail": str(e)}
