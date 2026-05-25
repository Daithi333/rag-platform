"""Guardrail node: validates question is in scope before retrieval."""

import json

import structlog

from src.services.agents.prompts import GUARDRAIL_PROMPT
from src.services.agents.state import AgentState
from src.services.llm.base import BaseLLMClient

logger = structlog.getLogger(__name__)


async def guardrail(state: AgentState, llm: BaseLLMClient) -> AgentState:
    """Check if the question is in scope. Updates state with reasoning."""
    prompt = GUARDRAIL_PROMPT.format(question=state.question)
    response = await llm.generate(prompt)

    try:
        result = json.loads(response.text)
        in_scope = result.get("in_scope", True)
        reason = result.get("reason", "")
    except (json.JSONDecodeError, KeyError):
        in_scope = True
        reason = "Could not parse guardrail response, proceeding."

    state.reasoning_steps.append(
        f"Guardrail: {'in scope' if in_scope else 'out of scope'} ({reason})"
    )

    if not in_scope:
        state.answer = (
            "I can only answer questions about software development and programming topics."
        )

    return state
