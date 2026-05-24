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


class StreamResponse:
    """Async iterator over tokens that also captures usage metadata after completion.

    Usage:
        stream = await client.generate_stream(prompt)
        async for token in stream:
            print(token)
        # After iteration, usage is available:
        print(stream.usage)  # {"input": 850, "output": 120}
        print(stream.model)  # "gpt-4o-mini"
    """

    def __init__(self, iterator: AsyncIterator[str], model: str | None = None):
        self._iterator = iterator
        self.model = model
        self._usage_holder: dict | None = None

    @property
    def usage(self) -> dict[str, int] | None:
        """Available after iteration completes."""
        if self._usage_holder:
            return self._usage_holder.get("usage")
        return None

    def __aiter__(self):
        return self

    async def __anext__(self) -> str:
        return await self._iterator.__anext__()


class BaseLLMClient(ABC):
    """Interface that all LLM implementations must satisfy."""

    @abstractmethod
    async def health_check(self) -> dict:
        """Check if the LLM service is reachable."""

    @abstractmethod
    async def generate(self, prompt: str) -> LLMResponse:
        """Generate a complete response."""

    @abstractmethod
    async def generate_stream(self, prompt: str) -> StreamResponse:
        """Stream generated text token by token. Usage available after iteration."""
