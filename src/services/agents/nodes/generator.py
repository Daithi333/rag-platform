"""Generator node: produces the final answer from graded chunks."""

import structlog

from src.services.agents.state import AgentState
from src.schemas.api.rag import Source
from src.services.llm.base import BaseLLMClient
from src.services.llm.prompts import build_rag_prompt

logger = structlog.getLogger(__name__)


async def generate(state: AgentState, llm: BaseLLMClient) -> AgentState:
    """Generate the final answer using graded chunks as context."""
    if not state.graded_chunks:
        state.answer = "I couldn't find relevant information to answer your question."
        state.reasoning_steps.append("Generator: no relevant chunks, returning fallback")
        return state

    prompt = build_rag_prompt(state.question, state.graded_chunks)
    response = await llm.generate(prompt)

    state.answer = response.text
    state.model = response.model
    state.duration_ms = response.total_duration_ms
    state.sources = _extract_sources(state.graded_chunks)
    state.reasoning_steps.append(
        f"Generator: produced answer from {len(state.graded_chunks)} chunks"
    )

    return state


def _extract_sources(chunks) -> list[Source]:
    seen: set[str] = set()
    sources: list[Source] = []
    for chunk in chunks:
        if chunk.url and chunk.url not in seen:
            seen.add(chunk.url)
            sources.append(Source(title=chunk.title, url=chunk.url, author=chunk.author))
    return sources
