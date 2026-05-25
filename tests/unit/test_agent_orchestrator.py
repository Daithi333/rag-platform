"""Unit tests for the agentic RAG orchestrator flow."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.config import AgentSettings, OpenSearchSettings
from src.services.agents.orchestrator import AgenticRAGService
from src.services.llm.base import LLMResponse


@pytest.fixture
def mock_opensearch():
    client = MagicMock()
    client.search = MagicMock(return_value={"total": 0, "hits": []})
    return client


@pytest.fixture
def mock_embedding_client():
    client = MagicMock()
    client.embed_single = AsyncMock(return_value=[0.1] * 1024)
    return client


@pytest.fixture
def mock_llm():
    return MagicMock()


@pytest.fixture
def agent_settings():
    return AgentSettings(
        max_rewrites=2, min_relevant_chunks=1, skip_guardrail=False, skip_grading=False
    )


@pytest.fixture
def opensearch_settings():
    return OpenSearchSettings()


@pytest.fixture
def service(mock_opensearch, mock_embedding_client, mock_llm, opensearch_settings, agent_settings):
    return AgenticRAGService(
        opensearch=mock_opensearch,
        embedding_client=mock_embedding_client,
        llm_client=mock_llm,
        opensearch_settings=opensearch_settings,
        agent_settings=agent_settings,
    )


class TestOrchestratorFlow:
    @pytest.mark.asyncio
    async def test_out_of_scope_exits_early(self, service, mock_llm):
        mock_llm.generate = AsyncMock(
            return_value=LLMResponse(text='{"in_scope": false, "reason": "not tech"}', model="test")
        )

        state = await service.ask("How do I cook pasta?")

        assert state.answer is not None
        assert "only answer questions" in state.answer.lower()
        assert len(state.reasoning_steps) == 1

    @pytest.mark.asyncio
    async def test_skip_guardrail(
        self, mock_opensearch, mock_embedding_client, mock_llm, opensearch_settings
    ):
        settings = AgentSettings(skip_guardrail=True, skip_grading=True)
        svc = AgenticRAGService(
            opensearch=mock_opensearch,
            embedding_client=mock_embedding_client,
            llm_client=mock_llm,
            opensearch_settings=opensearch_settings,
            agent_settings=settings,
        )

        mock_llm.generate = AsyncMock(
            side_effect=[
                LLMResponse(
                    text='{"tags": ["python"], "mode": "hybrid", "num_chunks": 3}', model="test"
                ),
                LLMResponse(text="The answer is 42.", model="test"),
            ]
        )
        mock_opensearch.search.return_value = {
            "total": 1,
            "hits": [
                {
                    "chunk_id": "c1",
                    "article_id": "a1",
                    "source_id": "1",
                    "chunk_index": 0,
                    "chunk_text": "some text",
                    "chunk_word_count": 2,
                    "title": "Article",
                    "author": "Auth",
                    "tags": ["python"],
                    "url": "https://example.com",
                    "_score": 1.0,
                    "_id": "d1",
                }
            ],
        }

        state = await svc.ask("What is Python?")

        assert "Guardrail: skipped" in state.reasoning_steps
        assert state.answer == "The answer is 42."

    @pytest.mark.asyncio
    async def test_no_results_still_generates(self, service, mock_llm, mock_opensearch):
        mock_llm.generate = AsyncMock(
            side_effect=[
                LLMResponse(text='{"in_scope": true, "reason": "tech"}', model="test"),
                LLMResponse(text='{"tags": null, "mode": "hybrid", "num_chunks": 5}', model="test"),
                LLMResponse(text="I couldn't find relevant information.", model="test"),
            ]
        )
        mock_opensearch.search.return_value = {"total": 0, "hits": []}

        state = await service.ask("Something obscure")

        assert "no results found" in " ".join(state.reasoning_steps).lower()
