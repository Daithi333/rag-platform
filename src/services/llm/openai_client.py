"""OpenAI-compatible LLM client. Works with OpenAI, Groq, and any provider
that implements the OpenAI chat completions API."""

from collections.abc import AsyncIterator

import httpx
import structlog

from src.config import OpenAISettings
from src.exceptions import ExternalServiceError

from .base import BaseLLMClient, LLMResponse

logger = structlog.getLogger(__name__)


class OpenAILLMClient(BaseLLMClient):
    """Client for OpenAI-compatible chat completions API (OpenAI, Groq, etc.)."""

    def __init__(self, settings: OpenAISettings):
        self._settings = settings
        self._headers = {
            "Authorization": f"Bearer {settings.api_key}",
            "Content-Type": "application/json",
        }

    def _completions_url(self) -> str:
        return f"{self._settings.base_url}/chat/completions"

    async def health_check(self) -> dict:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{self._settings.base_url}/models",
                    headers=self._headers,
                )
                response.raise_for_status()
                return {"status": "healthy", "provider": self._settings.base_url}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    async def generate(self, prompt: str) -> LLMResponse:
        payload = {
            "model": self._settings.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self._settings.temperature,
            "top_p": self._settings.top_p,
            "max_tokens": self._settings.max_tokens,
            "stream": False,
        }

        try:
            async with httpx.AsyncClient(timeout=self._settings.timeout_seconds) as client:
                response = await client.post(
                    self._completions_url(),
                    headers=self._headers,
                    json=payload,
                )
                response.raise_for_status()

            data = response.json()
            choice = data["choices"][0]
            usage = data.get("usage", {})

            return LLMResponse(
                text=choice["message"]["content"],
                model=data.get("model"),
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
            )

        except httpx.ConnectError as e:
            raise ExternalServiceError("OpenAI-compatible", f"Cannot connect: {e}")
        except httpx.TimeoutException as e:
            raise ExternalServiceError("OpenAI-compatible", f"Request timed out: {e}")
        except httpx.HTTPStatusError as e:
            raise ExternalServiceError(
                "OpenAI-compatible", f"HTTP {e.response.status_code}: {e.response.text}"
            )

    async def generate_stream(self, prompt: str) -> AsyncIterator[str]:
        import json

        payload = {
            "model": self._settings.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self._settings.temperature,
            "top_p": self._settings.top_p,
            "max_tokens": self._settings.max_tokens,
            "stream": True,
        }

        try:
            async with httpx.AsyncClient(timeout=self._settings.timeout_seconds) as client:
                async with client.stream(
                    "POST",
                    self._completions_url(),
                    headers=self._headers,
                    json=payload,
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data_str = line[len("data: ") :]
                        if data_str.strip() == "[DONE]":
                            break
                        chunk = json.loads(data_str)
                        delta = chunk["choices"][0].get("delta", {})
                        content = delta.get("content")
                        if content:
                            yield content

        except httpx.ConnectError as e:
            raise ExternalServiceError("OpenAI-compatible", f"Cannot connect: {e}")
        except httpx.TimeoutException as e:
            raise ExternalServiceError("OpenAI-compatible", f"Stream timed out: {e}")
        except httpx.HTTPStatusError as e:
            raise ExternalServiceError(
                "OpenAI-compatible", f"HTTP {e.response.status_code}: {e.response.text}"
            )
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            raise ExternalServiceError("OpenAI-compatible", f"Malformed stream response: {e}")
