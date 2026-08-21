from abc import ABC, abstractmethod


class AIEngine(ABC):

    @abstractmethod
    async def generate(self, message: str) -> str:
        """Generate an AI response."""
        raise NotImplementedError