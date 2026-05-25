"""Agentic RAG orchestrator: coordinates the node pipeline with conditional logic."""

import structlog

from src.config import AgentSettings, OpenSearchSettings
from src.schemas.api.search import ChunkHit
from src.services.agents.nodes.generator import generate
from src.services.agents.nodes.grader import grade
from src.services.agents.nodes.guardrail import guardrail
from src.services.agents.nodes.rewriter import rewrite
from src.services.agents.nodes.router import route
from src.services.agents.state import AgentState
from src.services.embeddings.client import EmbeddingClient
from src.services.llm.base import BaseLLMClient
from src.services.opensearch.client import OpenSearchClient
from src.services.search import SearchService
from src.services.tracing import tracer

logger = structlog.getLogger(__name__)


class AgenticRAGService:
    """Orchestrates the agentic RAG pipeline: guardrail → route → retrieve → grade → generate."""

    def __init__(
        self,
        opensearch: OpenSearchClient,
        embedding_client: EmbeddingClient,
        llm_client: BaseLLMClient,
        opensearch_settings: OpenSearchSettings,
        agent_settings: AgentSettings,
    ):
        self._search = SearchService(
            opensearch=opensearch,
            embedding_client=embedding_client,
            settings=opensearch_settings,
        )
        self._llm = llm_client
        self._settings = agent_settings

    @tracer.span("agentic_rag")
    async def ask(self, question: str) -> AgentState:
        """Run the full agentic RAG pipeline."""
        state = AgentState(question=question, current_query=question)

        # Step 1: Guardrail
        if not self._settings.skip_guardrail:
            state = await guardrail(state, self._llm)
            if state.answer:
                return state
        else:
            state.reasoning_steps.append("Guardrail: skipped")

        # Step 2: Route (decide search strategy)
        state = await route(state, self._llm)

        # Step 3-4: Retrieve + Grade (with retry loop)
        while state.rewrite_count <= self._settings.max_rewrites:
            state = await self._retrieve(state)

            if not state.chunks:
                state.reasoning_steps.append("Retrieve: no results found")
                break

            if self._settings.skip_grading:
                state.graded_chunks = state.chunks
                state.reasoning_steps.append("Grader: skipped")
                break

            state = await grade(state, self._llm)

            if len(state.graded_chunks) >= self._settings.min_relevant_chunks:
                break

            if state.rewrite_count >= self._settings.max_rewrites:
                state.reasoning_steps.append("Max rewrites reached, using best available chunks")
                state.graded_chunks = state.chunks
                break

            state = await rewrite(state, self._llm)

        # Step 5: Generate
        state = await generate(state, self._llm)

        return state

    async def ask_stream(self, question: str):
        """Run the agentic pipeline, yielding reasoning steps as they complete.

        Yields dicts: {"step": "..."} for progress, then {"state": AgentState} at the end.
        """
        state = AgentState(question=question, current_query=question)

        # Step 1: Guardrail
        if not self._settings.skip_guardrail:
            state = await guardrail(state, self._llm)
            yield {"step": state.reasoning_steps[-1]}
            if state.answer:
                yield {"state": state}
                return
        else:
            state.reasoning_steps.append("Guardrail: skipped")
            yield {"step": "Guardrail: skipped"}

        # Step 2: Route
        state = await route(state, self._llm)
        yield {"step": state.reasoning_steps[-1]}

        # Step 3-4: Retrieve + Grade loop
        while state.rewrite_count <= self._settings.max_rewrites:
            state = await self._retrieve(state)
            yield {"step": state.reasoning_steps[-1]}

            if not state.chunks:
                break

            if self._settings.skip_grading:
                state.graded_chunks = state.chunks
                state.reasoning_steps.append("Grader: skipped")
                yield {"step": "Grader: skipped"}
                break

            state = await grade(state, self._llm)
            yield {"step": state.reasoning_steps[-1]}

            if len(state.graded_chunks) >= self._settings.min_relevant_chunks:
                break

            if state.rewrite_count >= self._settings.max_rewrites:
                state.reasoning_steps.append("Max rewrites reached, using best available chunks")
                state.graded_chunks = state.chunks
                yield {"step": state.reasoning_steps[-1]}
                break

            state = await rewrite(state, self._llm)
            yield {"step": state.reasoning_steps[-1]}

        # Step 5: Generate
        state = await generate(state, self._llm)
        yield {"step": state.reasoning_steps[-1]}

        yield {"state": state}

    async def _retrieve(self, state: AgentState) -> AgentState:
        """Execute search using the routing decision."""
        params = state.search_params
        query = state.current_query or state.question

        results = await self._search.search(
            query=query,
            mode=params.mode if params else None,
            size=params.num_chunks if params else 5,
            tags=params.tags if params else None,
        )

        state.chunks = [
            ChunkHit(**hit) if isinstance(hit, dict) else hit for hit in results.get("hits", [])
        ]
        state.reasoning_steps.append(f"Retrieve: found {len(state.chunks)} chunks")

        return state
