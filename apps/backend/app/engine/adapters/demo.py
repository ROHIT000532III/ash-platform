from collections.abc import AsyncIterator, Sequence

from app.engine.base import AIEngine, ConversationMessage, GenerationOptions


class DemoEngine(AIEngine):
    """An explicit local fallback for development when configured."""

    provider_name = "demo"

    async def generate(
        self, message: str, history: Sequence[ConversationMessage] = (), options: GenerationOptions = GenerationOptions()
    ) -> str:
        del history, options
        return f"ASH AI demo fallback: I received your message - {message}"

    async def generate_stream(
        self, message: str, history: Sequence[ConversationMessage] = (), options: GenerationOptions = GenerationOptions()
    ) -> AsyncIterator[str]:
        yield await self.generate(message, history, options)
