from fastapi import FastAPI, Depends, HTTPException
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
    

@app.get("/api/wp-users", summary="Fetch all WordPress users with full columns")
def get_wp_users(db: Session = Depends(get_db)):
    try:
        query = text("SELECT * FROM wp_users LIMIT 15")
        result = db.execute(query)
        
        column_names = result.keys()
        users = [dict(zip(column_names, row)) for row in result.fetchall()]
        
        return {"users": users}
    except Exception as e:
        return {"error": str(e)}
    
@app.get("/api/user-stage/{user_id}", summary="Fetch CEFR stage for a user")
def get_user_stage(user_id: int, db: Session = Depends(get_db)):
    try:
        query = text("""
            SELECT meta_value 
            FROM wp_usermeta 
            WHERE user_id = :user_id AND meta_key = 'stage'
            ORDER BY umeta_id DESC 
            LIMIT 1
        """)
        result = db.execute(query, {"user_id": user_id})
        row = result.fetchone()
        if row:
            return {"user_id": user_id, "stage": row[0]}
        else:
            raise HTTPException(status_code=404, detail="Stage not found for this user.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
