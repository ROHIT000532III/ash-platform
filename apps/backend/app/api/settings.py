from fastapi import APIRouter

from app.engine.manager import engine_manager

router = APIRouter(prefix="/api", tags=["settings"])


@router.get("/settings")
async def settings_status() -> dict[str, object]:
    """Return active, non-secret runtime configuration and provider availability."""
    settings = engine_manager.settings
    availability = await engine_manager.status()
    return {
        "ai_provider": settings.ai_provider,
        "ollama_base_url": settings.ollama_base_url,
        "ollama_model": settings.ollama_model,
        "request_timeout_seconds": settings.request_timeout_seconds,
        "request_retries": settings.request_retries,
        "fallback_provider": settings.ai_fallback_provider,
        "fallback_enabled": availability.get("fallback_enabled", False),
        "provider_available": availability.get("provider_available", False),
        "model_available": availability.get("model_available", False),
        "available": availability.get("available", False),
        "detail": availability.get("detail", ""),
    }
