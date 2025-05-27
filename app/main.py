from fastapi import FastAPI
from app.routes import user
from app.routes import translator

app = FastAPI()

# Include the user router
app.include_router(user.router, prefix="/user")
app.include_router(translator.router, prefix="/api/translate")