from pydantic import BaseModel, Field

from src.schemas.api.search import SearchMode


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    mode: SearchMode = SearchMode.HYBRID
    num_chunks: int = Field(default=5, ge=1, le=20)
    tags: list[str] | None = None


class Source(BaseModel):
    title: str
    url: str
    author: str | None = None


class AskResponse(BaseModel):
    question: str
    answer: str
    sources: list[Source]
    chunks_used: int
    model: str | None = None
    duration_ms: float | None = None
