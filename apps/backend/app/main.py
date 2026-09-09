from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router
from app.api.conversations import router as conversations_router
from app.api.settings import router as settings_router
from app.api.models import router as models_router
from app.api.auth import router as auth_router
from app.api.explorer import router as explorer_router
from app.core.dependencies import conversation_repository, workspace_service
from app.engine.manager import engine_manager


app = FastAPI(
    title="ASH AI Enterprise API",
    version="1.0.0",
    description="Backend API for ASH AI Enterprise",
)


@app.on_event("startup")
def initialize_database() -> None:
    conversation_repository.initialize()
    workspace_service.initialize()


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],
    allow_origin_regex=r"^app://(?:\./)?(?:[A-Za-z0-9._~-]+)?$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


@app.get("/")
def root():
    return {
        "name": "ASH AI Enterprise",
        "status": "running",
        "version": "1.0.0",
    }


@app.get("/health")
async def health():
    engine_status = await engine_manager.status()
    return {
        "status": "online" if engine_status["available"] else "degraded",
        "backend": "FastAPI",
        "ai_engine": "ready" if engine_status["available"] else "unavailable",
        "provider": engine_status["provider"],
        "model": engine_status["model"],
        "provider_available": engine_status.get("provider_available", False),
        "model_available": engine_status.get("model_available", False),
        "fallback_enabled": engine_status.get("fallback_enabled", False),
        "detail": engine_status.get("detail", ""),
    }


app.include_router(chat_router)
app.include_router(conversations_router)
app.include_router(settings_router)
app.include_router(models_router)
app.include_router(auth_router)
app.include_router(explorer_router)
