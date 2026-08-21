from collections.abc import AsyncIterator, Sequence

from app.core.config import Settings, get_settings
from app.engine.adapters import DemoEngine, OllamaEngine
from app.engine.base import (
    AIEngine,
    ConversationMessage,
    GenerationOptions,
    EngineConfigurationError,
    ProviderResponseError,
    ProviderUnavailableError,
)


class EngineManager:
    """The API-facing entry point for all current and future AI providers."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._configuration_error: EngineConfigurationError | None = None
        self.engine = self._build_engine(self.settings.ai_provider)
        self.fallback_engine = self._build_fallback()

    def _build_engine(self, provider: str) -> AIEngine | None:
        if provider == "ollama":
            return OllamaEngine(self.settings)
        if provider == "demo":
            return DemoEngine()
        self._configuration_error = EngineConfigurationError(
            f"AI provider '{provider}' is not configured. Use 'ollama' or 'demo'."
        )
        return None

    def _build_fallback(self) -> AIEngine | None:
        if self.settings.ai_fallback_provider == "demo":
            return DemoEngine()
        return None

    def _require_engine(self) -> AIEngine:
        if self._configuration_error:
            raise self._configuration_error
        if self.engine is None:
            raise EngineConfigurationError("No AI provider is configured.")
        return self.engine

    async def generate(
        self, message: str, history: Sequence[ConversationMessage] = (), options: GenerationOptions = GenerationOptions()
    ) -> str:
        try:
            return await self._require_engine().generate(message, history, options)
        except ProviderUnavailableError:
            if self.fallback_engine is not None:
                return await self.fallback_engine.generate(message, history, options)
            raise

    async def generate_stream(
        self, message: str, history: Sequence[ConversationMessage] = (), options: GenerationOptions = GenerationOptions()
    ) -> AsyncIterator[str]:
        try:
            async for chunk in self._require_engine().generate_stream(message, history, options):
                yield chunk
        except ProviderUnavailableError:
            if self.fallback_engine is None:
                raise
            async for chunk in self.fallback_engine.generate_stream(message, history, options):
                yield chunk

    async def status(self) -> dict[str, object]:
        if self._configuration_error:
            return {
                "provider": self.settings.ai_provider,
                "model": self.settings.ollama_model,
                "available": False,
                "model_available": False,
                "fallback_enabled": self.fallback_engine is not None,
                "detail": str(self._configuration_error),
            }

        engine = self._require_engine()
        provider_available = False
        model_available = True
        detail = "Provider is available."

        try:
            if isinstance(engine, OllamaEngine):
                models = await engine.list_models()
                provider_available = True
                model_available = await engine.model_available()
                if model_available:
                    detail = "Ollama is available and the configured model is installed."
                else:
                    detail = (
                        f"Ollama is available, but model '{engine.model}' was not found. "
                        f"Installed models: {', '.join(models) if models else 'none'}."
                    )
            else:
                provider_available = await engine.is_available()
                detail = "Provider is available." if provider_available else "Provider is unavailable."
        except ProviderUnavailableError as error:
            detail = str(error)
        except ProviderResponseError as error:
            provider_available = True
            model_available = False
            detail = str(error)

        return {
            "provider": engine.provider_name,
            "model": getattr(engine, "model", "demo"),
            "available": provider_available and model_available,
            "provider_available": provider_available,
            "model_available": model_available,
            "fallback_enabled": self.fallback_engine is not None,
            "detail": detail,
        }

    async def installed_models(self) -> list[dict[str, object]]:
        engine = self._require_engine()
        if not isinstance(engine, OllamaEngine):
            raise EngineConfigurationError("Model discovery is only available for the Ollama provider.")
        models = await engine.list_model_details()
        for model in models:
            name = model.get("name")
            model["active"] = name == engine.model or (
                isinstance(name, str) and name.split(":", 1)[0] == engine.model
            )
        return models


engine_manager = EngineManager()
