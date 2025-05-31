from fastapi import FastAPI
from app.routes import user
from app.routes import translator
from app.routes import repeat_after_me,quick_response

app = FastAPI()

# Include the user router
app.include_router(user.router, prefix="/user")
app.include_router(translator.router, prefix="/api/translate")
app.include_router(repeat_after_me.router, prefix="/api")
app.include_router(quick_response.router, prefix="/api")