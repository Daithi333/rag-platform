"""Abstract base and shared types for LLM clients."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from pydantic import BaseModel


class LLMResponse(BaseModel):
    """Standardised response from any LLM provider."""

    text: str
    model: str | None = None
    total_duration_ms: float | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0


class BaseLLMClient(ABC):
    """Interface that all LLM implementations must satisfy."""

    @abstractmethod
    async def health_check(self) -> dict:
        """Check if the LLM service is reachable."""

    @abstractmethod
    async def generate(self, prompt: str) -> LLMResponse:
        """Generate a complete response."""

    @abstractmethod
    async def generate_stream(self, prompt: str) -> AsyncIterator[str]:
        """Stream generated text token by token."""
