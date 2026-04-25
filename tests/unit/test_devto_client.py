from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from src.config import DevToSettings
from src.exceptions import DevToAPIException, DevToAPITimeoutError, DevToRateLimitError
from src.services.devto.client import DevToClient
from src.services.devto.factory import make_devto_client


MOCK_ARTICLE = {
    "id": 12345,
    "title": "Test Article",
    "description": "A test article",
    "body_markdown": "# Hello",
    "url": "https://dev.to/test/test-article",
    "published_at": "2026-01-15T10:00:00Z",
    "reading_time_minutes": 5,
    "tags": ["python", "testing"],
    "user": {"name": "Test Author"},
}


class TestDevToClient:
    @pytest.fixture
    def settings(self):
        return DevToSettings(
            api_key="test-key",
            base_url="https://dev.to/api",
            per_page=30,
            rate_limit_delay=0.0,
            timeout_seconds=5,
            max_retries=3,
            tags=["python", "webdev"],
        )

    @pytest.fixture
    def client(self, settings):
        return DevToClient(settings=settings)

    @pytest.fixture
    def unauthenticated_client(self):
        settings = DevToSettings(
            api_key="",
            base_url="https://dev.to/api",
        )
        return DevToClient(settings=settings)

    def test_factory_creates_client(self):
        client = make_devto_client()
        assert isinstance(client, DevToClient)

    def test_headers_with_api_key(self, client):
        headers = client._headers
        assert headers["api-key"] == "test-key"
        assert headers["Accept"] == "application/vnd.forem.api-v1+json"

    def test_headers_without_api_key(self, unauthenticated_client):
        headers = unauthenticated_client._headers
        assert "api-key" not in headers
        assert headers["Accept"] == "application/vnd.forem.api-v1+json"

    @pytest.mark.asyncio
    async def test_fetch_articles_success(self, client):
        with patch("httpx.AsyncClient") as mock_http:
            mock_response = MagicMock()
            mock_response.json.return_value = [MOCK_ARTICLE]
            mock_response.status_code = 200
            mock_response.headers = {}
            mock_response.raise_for_status.return_value = None

            mock_http.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            articles = await client.fetch_articles(tag="python")

            assert len(articles) == 1
            assert articles[0].id == 12345
            assert articles[0].title == "Test Article"
            assert articles[0].user == {"name": "Test Author"}

    @pytest.mark.asyncio
    async def test_fetch_articles_empty_response(self, client):
        with patch("httpx.AsyncClient") as mock_http:
            mock_response = MagicMock()
            mock_response.json.return_value = []
            mock_response.status_code = 200
            mock_response.headers = {}
            mock_response.raise_for_status.return_value = None

            mock_http.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            articles = await client.fetch_articles(tag="python")
            assert articles == []

    @pytest.mark.asyncio
    async def test_fetch_articles_timeout(self, client):
        with patch("httpx.AsyncClient") as mock_http:
            mock_http.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.TimeoutException("Request timeout")
            )

            with pytest.raises(DevToAPITimeoutError) as exc_info:
                await client.fetch_articles(tag="python")

            assert "timed out" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_fetch_articles_parse_error(self, client):
        with patch("httpx.AsyncClient") as mock_http:
            mock_response = MagicMock()
            mock_response.json.return_value = [{"invalid": "data"}]
            mock_response.status_code = 200
            mock_response.headers = {}
            mock_response.raise_for_status.return_value = None

            mock_http.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            with pytest.raises(DevToAPIException):
                await client.fetch_articles(tag="python")

    @pytest.mark.asyncio
    async def test_fetch_articles_rate_limited(self, client):
        with patch("httpx.AsyncClient") as mock_http:
            mock_response = MagicMock()
            mock_response.status_code = 429
            mock_response.headers = {"Retry-After": "30"}

            mock_http.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            with pytest.raises(DevToRateLimitError):
                await client.fetch_articles(tag="python")

    @pytest.mark.asyncio
    async def test_fetch_articles_server_error(self, client):
        with patch("httpx.AsyncClient") as mock_http:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.headers = {}
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Server error", request=MagicMock(), response=mock_response
            )

            mock_http.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            with pytest.raises(DevToAPIException) as exc_info:
                await client.fetch_articles(tag="python")

            assert "Server error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_fetch_all_articles_deduplicates(self, client):
        with patch.object(client, "fetch_articles") as mock_fetch:
            mock_fetch.side_effect = [
                [MagicMock(id=1), MagicMock(id=2)],
                [MagicMock(id=2), MagicMock(id=3)],
            ]

            articles = await client.fetch_all_articles(tags=["python", "webdev"])

            assert len(articles) == 3

    @pytest.mark.asyncio
    async def test_fetch_all_articles_stops_on_partial_page(self, client):
        with patch.object(client, "fetch_articles") as mock_fetch:
            # Return fewer than per_page to signal last page
            mock_fetch.return_value = [MagicMock(id=i) for i in range(5)]

            await client.fetch_all_articles(tags=["python"])

            assert mock_fetch.call_count == 1

    @pytest.mark.asyncio
    async def test_fetch_all_articles_uses_configured_tags(self, client):
        with patch.object(client, "fetch_articles", return_value=[]) as mock_fetch:
            await client.fetch_all_articles()

            tags_called = [
                call.kwargs.get("tag") or call.args[0] for call in mock_fetch.call_args_list
            ]
            assert tags_called == ["python", "webdev"]

    @pytest.mark.asyncio
    async def test_health_check_authenticated(self, client):
        with patch("httpx.AsyncClient") as mock_http:
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None

            mock_http.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await client.health_check()

            assert result["status"] == "ok"
            assert result["authenticated"] is True

    @pytest.mark.asyncio
    async def test_health_check_unauthenticated(self, unauthenticated_client):
        with patch("httpx.AsyncClient") as mock_http:
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None

            mock_http.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await unauthenticated_client.health_check()

            assert result["status"] == "ok"
            assert result["authenticated"] is False
