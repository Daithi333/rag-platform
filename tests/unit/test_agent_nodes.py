"""Unit tests for agentic RAG nodes."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.schemas.api.search import ChunkHit
from src.services.agents.nodes.grader import grade
from src.services.agents.nodes.guardrail import guardrail
from src.services.agents.nodes.rewriter import rewrite
from src.services.agents.nodes.router import route
from src.services.agents.nodes.generator import generate
from src.services.agents.state import AgentState
from src.services.llm.base import LLMResponse


def _mock_llm(response_text: str):
    llm = MagicMock()
    llm.generate = AsyncMock(return_value=LLMResponse(text=response_text, model="test"))
    return llm


def _make_state(question: str = "How do I handle errors in Python?") -> AgentState:
    return AgentState(question=question, current_query=question)


def _make_chunk(text: str = "Python uses try/except.", title: str = "Error Guide") -> ChunkHit:
    return ChunkHit(
        chunk_id="c1",
        article_id="a1",
        source_id="100",
        chunk_index=0,
        chunk_text=text,
        chunk_word_count=5,
        title=title,
        author="Author",
        tags=["python"],
        url="https://example.com/article",
        score=1.0,
        _id="d1",
    )


class TestGuardrail:
    @pytest.mark.asyncio
    async def test_in_scope(self):
        llm = _mock_llm('{"in_scope": true, "reason": "programming question"}')
        state = _make_state()

        result = await guardrail(state, llm)

        assert result.answer is None
        assert "in scope" in result.reasoning_steps[0]

    @pytest.mark.asyncio
    async def test_out_of_scope(self):
        llm = _mock_llm('{"in_scope": false, "reason": "cooking question"}')
        state = _make_state("How do I make pasta?")

        result = await guardrail(state, llm)

        assert result.answer is not None
        assert "out of scope" in result.reasoning_steps[0]

    @pytest.mark.asyncio
    async def test_malformed_response_defaults_to_in_scope(self):
        llm = _mock_llm("not valid json")
        state = _make_state()

        result = await guardrail(state, llm)

        assert result.answer is None


class TestRouter:
    @pytest.mark.asyncio
    async def test_routes_with_tags(self):
        llm = _mock_llm('{"tags": ["python"], "mode": "hybrid", "num_chunks": 5}')
        state = _make_state()

        result = await route(state, llm)

        assert result.search_params is not None
        assert result.search_params.tags == ["python"]
        assert result.search_params.num_chunks == 5

    @pytest.mark.asyncio
    async def test_clamps_num_chunks(self):
        llm = _mock_llm('{"tags": null, "mode": "bm25", "num_chunks": 50}')
        state = _make_state()

        result = await route(state, llm)

        assert result.search_params.num_chunks == 10

    @pytest.mark.asyncio
    async def test_malformed_response_uses_defaults(self):
        llm = _mock_llm("garbage")
        state = _make_state()

        result = await route(state, llm)

        assert result.search_params is not None
        assert result.search_params.num_chunks == 5


class TestGrader:
    @pytest.mark.asyncio
    async def test_keeps_relevant_chunks(self):
        llm = _mock_llm('{"relevant": true, "reason": "directly answers"}')
        state = _make_state()
        state.chunks = [_make_chunk(), _make_chunk("Another chunk")]

        result = await grade(state, llm)

        assert len(result.graded_chunks) == 2

    @pytest.mark.asyncio
    async def test_filters_irrelevant_chunks(self):
        llm = MagicMock()
        llm.generate = AsyncMock(
            side_effect=[
                LLMResponse(text='{"relevant": true, "reason": "good"}', model="test"),
                LLMResponse(text='{"relevant": false, "reason": "off topic"}', model="test"),
            ]
        )
        state = _make_state()
        state.chunks = [_make_chunk("relevant"), _make_chunk("irrelevant")]

        result = await grade(state, llm)

        assert len(result.graded_chunks) == 1

    @pytest.mark.asyncio
    async def test_malformed_response_keeps_chunk(self):
        llm = _mock_llm("not json")
        state = _make_state()
        state.chunks = [_make_chunk()]

        result = await grade(state, llm)

        assert len(result.graded_chunks) == 1


class TestRewriter:
    @pytest.mark.asyncio
    async def test_rewrites_query(self):
        llm = _mock_llm('{"rewritten_query": "Python exception handling best practices"}')
        state = _make_state()

        result = await rewrite(state, llm)

        assert result.current_query == "Python exception handling best practices"
        assert result.rewrite_count == 1

    @pytest.mark.asyncio
    async def test_malformed_response_keeps_original(self):
        llm = _mock_llm("not json")
        state = _make_state("original question")

        result = await rewrite(state, llm)

        assert result.current_query == "original question"


class TestGenerator:
    @pytest.mark.asyncio
    async def test_generates_answer(self):
        llm = _mock_llm("Python uses try/except blocks for error handling.")
        state = _make_state()
        state.graded_chunks = [_make_chunk()]

        result = await generate(state, llm)

        assert result.answer == "Python uses try/except blocks for error handling."
        assert result.model == "test"
        assert len(result.sources) == 1

    @pytest.mark.asyncio
    async def test_no_chunks_returns_fallback(self):
        llm = _mock_llm("should not be called")
        state = _make_state()
        state.graded_chunks = []

        result = await generate(state, llm)

        assert "couldn't find" in result.answer.lower()
        llm.generate.assert_not_called()
