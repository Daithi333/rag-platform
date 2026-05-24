"""Unit tests for the Redis cache client."""

from unittest.mock import MagicMock

import pytest

from src.config import RedisSettings
from src.schemas.api.rag import AskRequest, AskResponse, Source
from src.services.cache.client import CacheClient


@pytest.fixture
def settings():
    return RedisSettings(host="localhost", port=6379, password="", db=0, ttl_seconds=300)


@pytest.fixture
def mock_redis():
    return MagicMock()


@pytest.fixture
def client(mock_redis, settings):
    return CacheClient(redis_client=mock_redis, settings=settings)


@pytest.fixture
def sample_request():
    return AskRequest(question="What is Python?", mode="hybrid", num_chunks=5)


@pytest.fixture
def sample_response():
    return AskResponse(
        question="What is Python?",
        answer="A programming language.",
        sources=[Source(title="Intro to Python", url="https://example.com", author="Author")],
        chunks_used=3,
        model="gpt-4o-mini",
    )


class TestCacheGet:
    @pytest.mark.asyncio
    async def test_cache_hit(self, client, mock_redis, sample_request, sample_response):
        mock_redis.get.return_value = sample_response.model_dump_json()

        result = await client.get(sample_request)

        assert result is not None
        assert result.answer == "A programming language."
        assert result.question == "What is Python?"

    @pytest.mark.asyncio
    async def test_cache_miss(self, client, mock_redis, sample_request):
        mock_redis.get.return_value = None

        result = await client.get(sample_request)

        assert result is None

    @pytest.mark.asyncio
    async def test_cache_error_returns_none(self, client, mock_redis, sample_request):
        mock_redis.get.side_effect = Exception("connection lost")

        result = await client.get(sample_request)

        assert result is None


class TestCacheSet:
    @pytest.mark.asyncio
    async def test_stores_response(self, client, mock_redis, sample_request, sample_response):
        await client.set(sample_request, sample_response)

        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert call_args[1]["ex"] == 300

    @pytest.mark.asyncio
    async def test_error_fails_silently(self, client, mock_redis, sample_request, sample_response):
        mock_redis.set.side_effect = Exception("connection lost")

        await client.set(sample_request, sample_response)


class TestCacheKey:
    @pytest.mark.asyncio
    async def test_same_question_same_key(self, client, mock_redis, sample_response):
        req1 = AskRequest(question="What is Python?", mode="hybrid", num_chunks=5)
        req2 = AskRequest(question="What is Python?", mode="hybrid", num_chunks=5)

        await client.set(req1, sample_response)
        key1 = mock_redis.set.call_args[0][0]

        mock_redis.reset_mock()
        await client.set(req2, sample_response)
        key2 = mock_redis.set.call_args[0][0]

        assert key1 == key2

    @pytest.mark.asyncio
    async def test_different_question_different_key(self, client, mock_redis, sample_response):
        req1 = AskRequest(question="What is Python?", mode="hybrid", num_chunks=5)
        req2 = AskRequest(question="What is Java?", mode="hybrid", num_chunks=5)

        await client.set(req1, sample_response)
        key1 = mock_redis.set.call_args[0][0]

        mock_redis.reset_mock()
        await client.set(req2, sample_response)
        key2 = mock_redis.set.call_args[0][0]

        assert key1 != key2

    @pytest.mark.asyncio
    async def test_case_insensitive(self, client, mock_redis, sample_response):
        req1 = AskRequest(question="What is Python?", mode="hybrid", num_chunks=5)
        req2 = AskRequest(question="what is python?", mode="hybrid", num_chunks=5)

        await client.set(req1, sample_response)
        key1 = mock_redis.set.call_args[0][0]

        mock_redis.reset_mock()
        await client.set(req2, sample_response)
        key2 = mock_redis.set.call_args[0][0]

        assert key1 == key2
