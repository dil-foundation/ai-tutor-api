from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import user
from app.routes import translator
from app.routes import repeat_after_me, quick_response

app = FastAPI()

# Add CORS middleware
origins = [
    "http://localhost:8081",  # Reverted from "*" to be compatible with allow_credentials=True
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
