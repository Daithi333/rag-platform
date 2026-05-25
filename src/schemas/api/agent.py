from pydantic import BaseModel, Field

from src.schemas.api.rag import Source


class AgentAskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)


class AgentAskResponse(BaseModel):
    question: str
    answer: str
    sources: list[Source]
    chunks_used: int
    reasoning_steps: list[str]
    rewritten_query: str | None = None
    model: str | None = None
    duration_ms: float | None = None
