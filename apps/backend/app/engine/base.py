from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class ConversationMessage:
    role: Literal["user", "assistant"]
    content: str


@dataclass(frozen=True)
class GenerationOptions:
    temperature: float | None = None
    max_tokens: int | None = None


class EngineError(Exception):
    """A safe error that can be returned to the API client."""


class EngineConfigurationError(EngineError):
    pass


class ProviderUnavailableError(EngineError):
    pass


class ProviderResponseError(EngineError):
    pass


class AIEngine(ABC):
    """
    Base interface for every ASH AI engine.
    """

    @abstractmethod
    async def generate(
        self, message: str, history: Sequence[ConversationMessage] = (), options: GenerationOptions = GenerationOptions()
    ) -> str:
        """
        Generate an AI response from the given message.
        """
        raise NotImplementedError

    @abstractmethod
    async def generate_stream(
        self, message: str, history: Sequence[ConversationMessage] = (), options: GenerationOptions = GenerationOptions()
    ) -> AsyncIterator[str]:
        """Yield response chunks when the provider supports streaming."""
        raise NotImplementedError

    async def is_available(self) -> bool:
        return True
