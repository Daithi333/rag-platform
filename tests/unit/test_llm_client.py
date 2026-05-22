"""Unit tests for the Ollama LLM client."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.config import OllamaSettings
from src.exceptions import ExternalServiceError
from src.services.llm.base import LLMResponse
from src.services.llm.client import OllamaLLMClient


@pytest.fixture
def settings():
    return OllamaSettings(
        host="http://localhost:11434",
        model="llama3.2:3b",
        timeout_seconds=10,
        temperature=0.7,
        top_p=0.9,
    )


@pytest.fixture
def client(settings):
    return OllamaLLMClient(settings=settings)


class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_healthy(self, client):
        with patch("httpx.AsyncClient") as mock_http:
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            mock_resp.json.return_value = {"version": "0.5.0"}
            mock_http.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)
            result = await client.health_check()

        assert result["status"] == "healthy"
        assert result["version"] == "0.5.0"

    @pytest.mark.asyncio
    async def test_unhealthy(self, client):
        with patch("httpx.AsyncClient") as mock_http:
            mock_http.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.ConnectError("refused")
            )
            result = await client.health_check()

        assert result["status"] == "unhealthy"


class TestGenerate:
    @pytest.mark.asyncio
    async def test_success(self, client):
        with patch("httpx.AsyncClient") as mock_http:
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            mock_resp.json.return_value = {
                "response": "Test answer",
                "model": "llama3.2:3b",
                "total_duration": 500_000_000,
                "prompt_eval_count": 100,
                "eval_count": 50,
            }
            mock_http.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_resp)
            result = await client.generate("test prompt")

        assert isinstance(result, LLMResponse)
        assert result.text == "Test answer"
        assert result.model == "llama3.2:3b"
        assert result.total_duration_ms == 500.0
        assert result.prompt_tokens == 100
        assert result.completion_tokens == 50

    @pytest.mark.asyncio
    async def test_connection_error(self, client):
        with patch("httpx.AsyncClient") as mock_http:
            mock_http.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.ConnectError("refused")
            )
            with pytest.raises(ExternalServiceError) as exc_info:
                await client.generate("test")

        assert "Cannot connect" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_timeout(self, client):
        with patch("httpx.AsyncClient") as mock_http:
            mock_http.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.TimeoutException("timed out")
            )
            with pytest.raises(ExternalServiceError) as exc_info:
                await client.generate("test")

        assert "timed out" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_sends_correct_payload(self, client):
        with patch("httpx.AsyncClient") as mock_http:
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            mock_resp.json.return_value = {"response": "ok", "model": "test"}
            mock_post = AsyncMock(return_value=mock_resp)
            mock_http.return_value.__aenter__.return_value.post = mock_post

            await client.generate("hello world")

        payload = mock_post.call_args[1]["json"]
        assert payload["model"] == "llama3.2:3b"
        assert payload["prompt"] == "hello world"
        assert payload["stream"] is False
        assert payload["options"]["temperature"] == 0.7
        assert payload["options"]["top_p"] == 0.9
