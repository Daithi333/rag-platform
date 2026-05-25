"""Rewriter node: rewrites the query when retrieval results are poor."""

import json

import structlog

from src.services.agents.prompts import REWRITER_PROMPT
from src.services.agents.state import AgentState
from src.services.llm.base import BaseLLMClient

logger = structlog.getLogger(__name__)


async def rewrite(state: AgentState, llm: BaseLLMClient) -> AgentState:
    """Rewrite the query for better retrieval on the next attempt."""
    query = state.current_query or state.question
    prompt = REWRITER_PROMPT.format(question=query)
    response = await llm.generate(prompt)

    try:
        result = json.loads(response.text)
        rewritten = result.get("rewritten_query", query)
    except (json.JSONDecodeError, KeyError):
        rewritten = query

    state.current_query = rewritten
    state.rewrite_count += 1
    state.reasoning_steps.append(f"Rewriter: '{query}' -> '{rewritten}'")

    return state
