"""Router node: decides search strategy based on the question."""

import json

import structlog

from src.services.agents.prompts import ROUTER_PROMPT
from src.services.agents.state import AgentState, SearchParams
from src.schemas.api.search import SearchMode
from src.services.llm.base import BaseLLMClient

logger = structlog.getLogger(__name__)

MODE_MAP = {
    "hybrid": SearchMode.HYBRID,
    "bm25": SearchMode.BM25,
    "vector": SearchMode.VECTOR,
}


async def route(state: AgentState, llm: BaseLLMClient) -> AgentState:
    """Decide search parameters based on the question."""
    query = state.current_query or state.question
    prompt = ROUTER_PROMPT.format(question=query)
    response = await llm.generate(prompt)

    try:
        result = json.loads(response.text)
        tags = result.get("tags")
        mode = MODE_MAP.get(result.get("mode", "hybrid"), SearchMode.HYBRID)
        num_chunks = min(max(result.get("num_chunks", 5), 3), 10)
    except (json.JSONDecodeError, KeyError):
        tags = None
        mode = SearchMode.HYBRID
        num_chunks = 5

    state.search_params = SearchParams(tags=tags, mode=mode, num_chunks=num_chunks)
    state.reasoning_steps.append(f"Router: mode={mode.value}, tags={tags}, chunks={num_chunks}")

    return state
