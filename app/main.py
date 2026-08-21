from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router


app = FastAPI(
    title="ASH AI Enterprise",
    version="0.1.0",
    description="ASH AI Enterprise Backend API",
)


# --------------------------------------------------
# CORS
# --------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# Root
# --------------------------------------------------

@app.get("/")
async def root():
    return {
        "name": "ASH AI Enterprise",
        "status": "online",
        "version": "0.1.0",
    }


# --------------------------------------------------
# Health
# --------------------------------------------------

@app.get("/api/health")
async def health():
    return {
        "status": "online",
        "backend": "ready",
        "ai_engine": "standby",
    }


# --------------------------------------------------
# Chat API
# --------------------------------------------------

app.include_router(chat_router)