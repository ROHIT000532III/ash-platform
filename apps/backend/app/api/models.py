from fastapi import APIRouter, HTTPException, status

from app.engine.base import EngineConfigurationError, ProviderResponseError, ProviderUnavailableError
from app.engine.manager import engine_manager

router = APIRouter(prefix="/api", tags=["models"])


@router.get("/models")
async def models() -> dict[str, object]:
    try:
        return {"provider": engine_manager.settings.ai_provider, "models": await engine_manager.installed_models()}
    except (EngineConfigurationError, ProviderUnavailableError) as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    except ProviderResponseError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error
