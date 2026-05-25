"""Unit tests for StreamResponse usage propagation."""

import pytest

from src.services.llm.base import StreamResponse


async def _token_generator(tokens: list[str]):
    for token in tokens:
        yield token


class TestStreamResponse:
    @pytest.mark.asyncio
    async def test_iterates_tokens(self):
        stream = StreamResponse(iterator=_token_generator(["hello", " world"]), model="test-model")

        tokens = []
        async for token in stream:
            tokens.append(token)

        assert tokens == ["hello", " world"]

    @pytest.mark.asyncio
    async def test_model_available_via_usage(self):
        stream = StreamResponse(iterator=_token_generator(["hi"]), model="gpt-4o-mini")

        async for _ in stream:
            pass

        assert stream.usage.model == "gpt-4o-mini"

    @pytest.mark.asyncio
    async def test_usage_none_when_no_holder(self):
        stream = StreamResponse(iterator=_token_generator(["hi"]), model="test")

        async for _ in stream:
            pass

        assert stream.usage.usage_details is None
        assert stream.usage.prompt_tokens == 0
        assert stream.usage.completion_tokens == 0

    @pytest.mark.asyncio
    async def test_usage_populated_from_holder(self):
        stream = StreamResponse(iterator=_token_generator(["hi"]), model="gpt-4o-mini")
        stream._usage_holder = {"usage": {"input": 100, "output": 50}}

        async for _ in stream:
            pass

        assert stream.usage.prompt_tokens == 100
        assert stream.usage.completion_tokens == 50
        assert stream.usage.usage_details == {"input": 100, "output": 50}

    @pytest.mark.asyncio
    async def test_usage_details_none_when_zero_tokens(self):
        stream = StreamResponse(iterator=_token_generator(["hi"]), model="test")
        stream._usage_holder = {"usage": {"input": 0, "output": 0}}

        async for _ in stream:
            pass

        assert stream.usage.usage_details is None
