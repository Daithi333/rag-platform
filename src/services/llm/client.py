"""Ollama LLM client for local text generation."""

from collections.abc import AsyncIterator

import httpx
import structlog

from src.config import OllamaSettings
from src.exceptions import ExternalServiceError

from .base import BaseLLMClient, LLMResponse, StreamResponse
from src.services.tracing import tracer

logger = structlog.getLogger(__name__)


class OllamaLLMClient(BaseLLMClient):
    """Client for Ollama local LLM service."""

    def __init__(self, settings: OllamaSettings):
        self._settings = settings

    async def health_check(self) -> dict:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self._settings.host}/api/version")
                response.raise_for_status()
                return {"status": "healthy", "version": response.json().get("version")}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    @tracer.generation("llm_generate")
    async def generate(self, prompt: str) -> LLMResponse:
        try:
            async with httpx.AsyncClient(timeout=self._settings.timeout_seconds) as client:
                response = await client.post(
                    f"{self._settings.host}/api/generate",
                    json={
                        "model": self._settings.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": self._settings.temperature,
                            "top_p": self._settings.top_p,
                        },
                    },
                )
                response.raise_for_status()

            data = response.json()
            return LLMResponse(
                text=data.get("response", ""),
                model=data.get("model"),
                total_duration_ms=round(data.get("total_duration", 0) / 1_000_000, 2),
                prompt_tokens=data.get("prompt_eval_count", 0),
                completion_tokens=data.get("eval_count", 0),
            )

        except httpx.ConnectError as e:
            raise ExternalServiceError("Ollama", f"Cannot connect: {e}")
        except httpx.TimeoutException as e:
            raise ExternalServiceError("Ollama", f"Request timed out: {e}")
        except httpx.HTTPStatusError as e:
            raise ExternalServiceError(
                "Ollama", f"HTTP {e.response.status_code}: {e.response.text}"
            )

    async def generate_stream(self, prompt: str) -> StreamResponse:
        return StreamResponse(
            iterator=self._stream_tokens(prompt),
            model=self._settings.model,
        )

    async def _stream_tokens(self, prompt: str) -> AsyncIterator[str]:
        import json

        try:
            async with httpx.AsyncClient(timeout=self._settings.timeout_seconds) as client:
                async with client.stream(
                    "POST",
                    f"{self._settings.host}/api/generate",
                    json={
                        "model": self._settings.model,
                        "prompt": prompt,
                        "stream": True,
                        "options": {
                            "temperature": self._settings.temperature,
                            "top_p": self._settings.top_p,
                        },
                    },
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.strip():
                            chunk = json.loads(line)
                            if not chunk.get("done"):
                                yield chunk.get("response", "")

        except httpx.ConnectError as e:
            raise ExternalServiceError("Ollama", f"Cannot connect: {e}")
        except httpx.TimeoutException as e:
            raise ExternalServiceError("Ollama", f"Stream timed out: {e}")
        except httpx.HTTPStatusError as e:
            raise ExternalServiceError(
                "Ollama", f"HTTP {e.response.status_code}: {e.response.text}"
            )
        except (json.JSONDecodeError, KeyError) as e:
            raise ExternalServiceError("Ollama", f"Malformed stream response: {e}")
