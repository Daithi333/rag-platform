"""Abstract base and shared types for LLM clients."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass

from pydantic import BaseModel


@dataclass
class LLMUsage:
    """Token usage metadata from an LLM call."""

    model: str | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_duration_ms: float | None = None

    @property
    def usage_details(self) -> dict[str, int] | None:
        """Formatted for Langfuse. Returns None if no token data available."""
        if self.prompt_tokens or self.completion_tokens:
            return {"input": self.prompt_tokens, "output": self.completion_tokens}
        return None


class LLMResponse(BaseModel):
    """Standardised response from any LLM provider."""

    text: str
    model: str | None = None
    total_duration_ms: float | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def usage(self) -> LLMUsage:
        return LLMUsage(
            model=self.model,
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
            total_duration_ms=self.total_duration_ms,
        )


class StreamResponse:
    """Async iterator over tokens that also captures usage metadata after completion.

    Usage:
        stream = await client.generate_stream(prompt)
        async for token in stream:
            print(token)
        # After iteration:
        print(stream.usage.model)           # "gpt-4o-mini"
        print(stream.usage.usage_details)   # {"input": 850, "output": 120}
    """

    def __init__(self, iterator: AsyncIterator[str], model: str | None = None):
        self._iterator = iterator
        self._usage = LLMUsage(model=model)
        self._usage_holder: dict | None = None

    @property
    def usage(self) -> LLMUsage:
        """Available after iteration completes."""
        if self._usage_holder:
            raw = self._usage_holder.get("usage")
            if raw:
                self._usage.prompt_tokens = raw.get("input", 0)
                self._usage.completion_tokens = raw.get("output", 0)
        return self._usage

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
