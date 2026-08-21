from .base import AIEngine


class DemoEngine(AIEngine):

    async def generate(self, message: str) -> str:
        return f"ASH AI: I received your message — {message}"


class EngineManager:

    def __init__(self):
        self.engine: AIEngine = DemoEngine()

    async def generate(self, message: str) -> str:
        return await self.engine.generate(message)


engine_manager = EngineManager()