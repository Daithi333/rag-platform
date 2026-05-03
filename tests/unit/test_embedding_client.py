from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.config import JinaSettings
from src.exceptions import ExternalServiceError
from src.services.embeddings.client import EmbeddingClient


@pytest.fixture
def settings():
    return JinaSettings(
        api_key="test-key",
        model="jina-embeddings-v3",
        base_url="https://api.jina.ai/v1",
        batch_size=2,
        timeout_seconds=5,
        max_retries=3,
        retry_multiplier=0.01,
        retry_min_wait=0,
        retry_max_wait=0,
    )


@pytest.fixture
def client(settings):
    return EmbeddingClient(settings=settings)


def _mock_response(status_code: int = 200, data: dict | None = None):
    response = MagicMock()
    response.status_code = status_code
    response.raise_for_status = MagicMock()
    if status_code >= 400:
        response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=response
        )
    response.json.return_value = data or {}
    return response


class TestEmbedTexts:
    @pytest.mark.asyncio
    async def test_empty_input_returns_empty(self, client):
        result = await client.embed_texts([])
        assert result == []

    @pytest.mark.asyncio
    async def test_single_batch(self, client):
        mock_resp = _mock_response(
            data={
                "data": [
                    {"index": 0, "embedding": [0.1, 0.2]},
                    {"index": 1, "embedding": [0.3, 0.4]},
                ]
            }
        )

        with patch("httpx.AsyncClient") as mock_http:
            mock_http.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_resp)
            result = await client.embed_texts(["hello", "world"])

        assert len(result) == 2
        assert result[0] == [0.1, 0.2]
        assert result[1] == [0.3, 0.4]

    @pytest.mark.asyncio
    async def test_multiple_batches(self, client):
        """With batch_size=2, 3 texts should produce 2 API calls."""
        batch1_resp = _mock_response(
            data={
                "data": [
                    {"index": 0, "embedding": [0.1]},
                    {"index": 1, "embedding": [0.2]},
                ]
            }
        )
        batch2_resp = _mock_response(data={"data": [{"index": 0, "embedding": [0.3]}]})

        with patch("httpx.AsyncClient") as mock_http:
            mock_post = AsyncMock(side_effect=[batch1_resp, batch2_resp])
            mock_http.return_value.__aenter__.return_value.post = mock_post

            result = await client.embed_texts(["a", "b", "c"])

        assert len(result) == 3
        assert mock_post.call_count == 2

    @pytest.mark.asyncio
    async def test_preserves_order_when_api_returns_unordered(self, client):
        mock_resp = _mock_response(
            data={
                "data": [
                    {"index": 1, "embedding": [0.2]},
                    {"index": 0, "embedding": [0.1]},
                ]
            }
        )

        with patch("httpx.AsyncClient") as mock_http:
            mock_http.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_resp)
            result = await client.embed_texts(["first", "second"])

        assert result[0] == [0.1]
        assert result[1] == [0.2]


class TestEmbedSingle:
    @pytest.mark.asyncio
    async def test_returns_single_vector(self, client):
        mock_resp = _mock_response(data={"data": [{"index": 0, "embedding": [0.5, 0.6]}]})

        with patch("httpx.AsyncClient") as mock_http:
            mock_http.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_resp)
            result = await client.embed_single("test query")

        assert result == [0.5, 0.6]


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_insufficient_tokens_raises_domain_error(self, client):
        mock_resp = MagicMock()
        mock_resp.status_code = 402

        with patch("httpx.AsyncClient") as mock_http:
            mock_http.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_resp)

            with pytest.raises(ExternalServiceError) as exc_info:
                await client.embed_texts(["test"])

            assert "Insufficient tokens" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_server_error_retries_then_raises(self, client):
        mock_resp = _mock_response(status_code=500)

        with patch("httpx.AsyncClient") as mock_http:
            mock_post = AsyncMock(return_value=mock_resp)
            mock_http.return_value.__aenter__.return_value.post = mock_post

            with pytest.raises(httpx.HTTPStatusError):
                await client.embed_texts(["test"])

            assert mock_post.call_count == 3

    @pytest.mark.asyncio
    async def test_timeout_retries_then_raises(self, client):
        with patch("httpx.AsyncClient") as mock_http:
            mock_post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
            mock_http.return_value.__aenter__.return_value.post = mock_post

            with pytest.raises(httpx.TimeoutException):
                await client.embed_texts(["test"])

            assert mock_post.call_count == 3

    @pytest.mark.asyncio
    async def test_sends_correct_payload(self, client):
        mock_resp = _mock_response(data={"data": [{"index": 0, "embedding": [0.1]}]})

        with patch("httpx.AsyncClient") as mock_http:
            mock_post = AsyncMock(return_value=mock_resp)
            mock_http.return_value.__aenter__.return_value.post = mock_post

            await client.embed_texts(["hello"])

            call_kwargs = mock_post.call_args[1]
            payload = call_kwargs["json"]
            assert payload["model"] == "jina-embeddings-v3"
            assert payload["input"] == ["hello"]
            assert payload["normalized"] is True
            assert call_kwargs["headers"]["Authorization"] == "Bearer test-key"
