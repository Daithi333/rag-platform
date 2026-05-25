"""Grader node: evaluates chunk relevance after retrieval."""

import asyncio
import json

import structlog

from src.services.agents.prompts import GRADER_PROMPT
from src.services.agents.state import AgentState
from src.schemas.api.search import ChunkHit
from src.services.llm.base import BaseLLMClient

logger = structlog.getLogger(__name__)


async def grade(state: AgentState, llm: BaseLLMClient) -> AgentState:
    """Grade all retrieved chunks for relevance in parallel."""
    query = state.current_query or state.question

    async def _grade_one(chunk: ChunkHit) -> tuple[ChunkHit, bool]:
        prompt = GRADER_PROMPT.format(question=query, chunk_text=chunk.chunk_text)
        response = await llm.generate(prompt)
        try:
            result = json.loads(response.text)
            return chunk, result.get("relevant", True)
        except (json.JSONDecodeError, KeyError):
            return chunk, True

    results = await asyncio.gather(*[_grade_one(chunk) for chunk in state.chunks])
    state.graded_chunks = [chunk for chunk, relevant in results if relevant]

    state.reasoning_steps.append(
        f"Grader: {len(state.graded_chunks)}/{len(state.chunks)} chunks relevant"
    )

    return state
