"""State for the agentic RAG workflow."""

from dataclasses import dataclass, field

from src.schemas.api.rag import Source
from src.schemas.api.search import ChunkHit, SearchMode


@dataclass
class SearchParams:
    """Routing decision from the router node."""

    tags: list[str] | None = None
    mode: SearchMode = SearchMode.HYBRID
    num_chunks: int = 5


@dataclass
class AgentState:
    """Mutable state passed through the agentic RAG pipeline."""

    question: str
    search_params: SearchParams | None = None
    chunks: list[ChunkHit] = field(default_factory=list)
    graded_chunks: list[ChunkHit] = field(default_factory=list)
    rewrite_count: int = 0
    current_query: str | None = None
    answer: str | None = None
    sources: list[Source] = field(default_factory=list)
    reasoning_steps: list[str] = field(default_factory=list)
    model: str | None = None
    duration_ms: float | None = None
