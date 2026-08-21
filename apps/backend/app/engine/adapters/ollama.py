from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config import Settings
from app.engine.base import (
    AIEngine,
    ConversationMessage,
    GenerationOptions,
    ProviderResponseError,
    ProviderUnavailableError,
)


class OllamaEngine(AIEngine):
    provider_name = "ollama"

    def __init__(self, settings: Settings):
        self.base_url = settings.ollama_base_url
        self.model = settings.ollama_model
        self.timeout_seconds = settings.request_timeout_seconds
        self.retries = settings.request_retries

    def _messages(
        self, message: str, history: Sequence[ConversationMessage]
    ) -> list[dict[str, str]]:
        return [
            *({"role": item.role, "content": item.content} for item in history),
            {"role": "user", "content": message},
        ]

    def _payload(
        self, message: str, history: Sequence[ConversationMessage], stream: bool,
        options: GenerationOptions = GenerationOptions(),
    ) -> bytes:
        payload: dict[str, object] = {"model": self.model, "messages": self._messages(message, history), "stream": stream}
        ollama_options: dict[str, object] = {}
        if options.temperature is not None:
            ollama_options["temperature"] = options.temperature
        if options.max_tokens is not None:
            ollama_options["num_predict"] = options.max_tokens
        if ollama_options:
            payload["options"] = ollama_options
        return json.dumps(payload).encode("utf-8")

    async def generate(
        self, message: str, history: Sequence[ConversationMessage] = (), options: GenerationOptions = GenerationOptions()
    ) -> str:
        payload = self._payload(message, history, stream=False, options=options)
        result = await self._request_json("/api/chat", payload)
        content = result.get("message", {}).get("content", "")
        if not isinstance(content, str) or not content.strip():
            raise ProviderResponseError("Ollama returned an empty response.")
        return content.strip()

    async def generate_stream(
        self, message: str, history: Sequence[ConversationMessage] = (), options: GenerationOptions = GenerationOptions()
    ) -> AsyncIterator[str]:
        payload = self._payload(message, history, stream=True, options=options)
        stream = await self._open_stream_with_retries(payload)
        try:
            while True:
                line = await asyncio.to_thread(stream.readline)
                if not line:
                    break
                try:
                    item = json.loads(line.decode("utf-8"))
                except json.JSONDecodeError as error:
                    raise ProviderResponseError(
                        "Ollama returned an invalid streaming response."
                    ) from error

                if item.get("error"):
                    raise ProviderResponseError(str(item.get("error")))
                content = item.get("message", {}).get("content", "")
                if content:
                    yield content
                if item.get("done"):
                    break
        finally:
            stream.close()

    async def is_available(self) -> bool:
        try:
            await self.list_models()
            return True
        except (ProviderUnavailableError, ProviderResponseError):
            return False

    async def list_models(self) -> list[str]:
        return [item["name"] for item in await self.list_model_details()]

    async def list_model_details(self) -> list[dict[str, object]]:
        result = await self._request_json("/api/tags", None)
        models = result.get("models", [])
        if not isinstance(models, list):
            raise ProviderResponseError("Ollama returned an invalid model list.")
        details: list[dict[str, object]] = []
        for item in models:
            if isinstance(item, dict) and isinstance(item.get("name"), str):
                detail: dict[str, object] = {"name": item["name"]}
                if isinstance(item.get("size"), int):
                    detail["size"] = item["size"]
                if isinstance(item.get("modified_at"), str):
                    detail["modified_at"] = item["modified_at"]
                details.append(detail)
        return details

    async def model_available(self) -> bool:
        names = await self.list_models()
        return self.model in names or any(name.split(":", 1)[0] == self.model for name in names)

    async def _request_json(self, path: str, payload: bytes | None) -> dict[str, object]:
        last_error: ProviderUnavailableError | ProviderResponseError | None = None
        for attempt in range(self.retries + 1):
            try:
                result = await asyncio.to_thread(self._request, path, payload)
                if not isinstance(result, dict):
                    raise ProviderResponseError("Ollama returned an invalid response.")
                return result
            except (ProviderUnavailableError, ProviderResponseError) as error:
                last_error = error
                if attempt < self.retries:
                    await asyncio.sleep(0.25 * (attempt + 1))
        assert last_error is not None
        raise last_error

    async def _open_stream_with_retries(self, payload: bytes):
        last_error: ProviderUnavailableError | ProviderResponseError | None = None
        for attempt in range(self.retries + 1):
            try:
                return await asyncio.to_thread(self._open_stream, payload)
            except (ProviderUnavailableError, ProviderResponseError) as error:
                last_error = error
                if attempt < self.retries:
                    await asyncio.sleep(0.25 * (attempt + 1))
        assert last_error is not None
        raise last_error

    def _open_stream(self, payload: bytes):
        request = Request(
            f"{self.base_url}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json", "Accept": "application/x-ndjson"},
            method="POST",
        )
        try:
            return urlopen(request, timeout=self.timeout_seconds)
        except (HTTPError, URLError, TimeoutError, OSError) as error:
            raise self._provider_error(error) from error

    def _request(self, path: str, payload: bytes | None) -> dict[str, object]:
        request = Request(
            f"{self.base_url}{path}",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST" if payload is not None else "GET",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, OSError) as error:
            raise self._provider_error(error) from error
        except json.JSONDecodeError as error:
            raise ProviderResponseError("Ollama returned invalid JSON.") from error

    def _provider_error(self, error: Exception) -> ProviderUnavailableError | ProviderResponseError:
        if isinstance(error, HTTPError):
            if error.code == 404:
                return ProviderResponseError(f"Ollama model '{self.model}' was not found.")
            try:
                detail = error.read().decode("utf-8")
            except Exception:
                detail = ""
            if detail:
                return ProviderResponseError(f"Ollama rejected the request: {detail}")
            return ProviderResponseError("Ollama rejected the request.")
        return ProviderUnavailableError(
            "Ollama is unavailable. Start Ollama and confirm the configured model is installed."
        )
