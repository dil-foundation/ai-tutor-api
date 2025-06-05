from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from app.routes import user
from app.routes import translator
from .database import get_db, engine

from app.routes import repeat_after_me, quick_response, functional_dialogue

app = FastAPI()

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
app.include_router(functional_dialogue.router, prefix="/api")

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
    

