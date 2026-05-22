"""Unit tests for the OpenAI-compatible LLM client."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.config import OpenAISettings
from src.exceptions import ExternalServiceError
from src.services.llm.base import LLMResponse
from src.services.llm.openai_client import OpenAILLMClient


@pytest.fixture
def settings():
    return OpenAISettings(
        api_key="sk-test-key",
        base_url="https://api.openai.com/v1",
        model="gpt-4o-mini",
        timeout_seconds=10,
        temperature=0.7,
        top_p=0.9,
        max_tokens=1024,
    )


@pytest.fixture
def client(settings):
    return OpenAILLMClient(settings=settings)


class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_healthy(self, client):
        with patch("httpx.AsyncClient") as mock_http:
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            mock_resp.json.return_value = {"data": [{"id": "gpt-4o-mini"}]}
            mock_http.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)
            result = await client.health_check()

        assert result["status"] == "healthy"
        assert result["provider"] == "https://api.openai.com/v1"

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
                "choices": [{"message": {"content": "Test answer"}}],
                "model": "gpt-4o-mini",
                "usage": {
                    "prompt_tokens": 50,
                    "completion_tokens": 30,
                },
            }
            mock_http.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_resp)
            result = await client.generate("test prompt")

        assert isinstance(result, LLMResponse)
        assert result.text == "Test answer"
        assert result.model == "gpt-4o-mini"
        assert result.prompt_tokens == 50
        assert result.completion_tokens == 30
        assert result.total_duration_ms is None

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
            mock_resp.json.return_value = {
                "choices": [{"message": {"content": "ok"}}],
                "model": "gpt-4o-mini",
                "usage": {},
            }
            mock_post = AsyncMock(return_value=mock_resp)
            mock_http.return_value.__aenter__.return_value.post = mock_post

            await client.generate("hello world")

        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["json"]["model"] == "gpt-4o-mini"
        assert call_kwargs["json"]["messages"] == [{"role": "user", "content": "hello world"}]
        assert call_kwargs["json"]["temperature"] == 0.7
        assert call_kwargs["json"]["max_tokens"] == 1024
        assert call_kwargs["json"]["stream"] is False

    @pytest.mark.asyncio
    async def test_sends_auth_header(self, client):
        with patch("httpx.AsyncClient") as mock_http:
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            mock_resp.json.return_value = {
                "choices": [{"message": {"content": "ok"}}],
                "model": "gpt-4o-mini",
                "usage": {},
            }
            mock_post = AsyncMock(return_value=mock_resp)
            mock_http.return_value.__aenter__.return_value.post = mock_post

            await client.generate("test")

        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["headers"]["Authorization"] == "Bearer sk-test-key"


class TestGroqCompatibility:
    """Verify the client works with Groq's API shape (same as OpenAI)."""

    @pytest.mark.asyncio
    async def test_groq_settings(self):
        groq_settings = OpenAISettings(
            api_key="gsk-test-key",
            base_url="https://api.groq.com/openai/v1",
            model="llama-3.1-8b-instant",
            timeout_seconds=30,
            temperature=0.7,
            top_p=0.9,
            max_tokens=1024,
        )
        groq_client = OpenAILLMClient(settings=groq_settings)

        with patch("httpx.AsyncClient") as mock_http:
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            mock_resp.json.return_value = {
                "choices": [{"message": {"content": "Groq response"}}],
                "model": "llama-3.1-8b-instant",
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            }
            mock_http.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_resp)
            result = await groq_client.generate("test")

        assert result.text == "Groq response"
        assert result.model == "llama-3.1-8b-instant"
