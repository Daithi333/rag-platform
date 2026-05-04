from enum import StrEnum

from pydantic import BaseModel, Field


class SearchMode(StrEnum):
    BM25 = "bm25"
    VECTOR = "vector"
    HYBRID = "hybrid"


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    mode: SearchMode = SearchMode.HYBRID
    tags: list[str] | None = None
    size: int = Field(default=10, ge=1, le=100)
    page: int = Field(default=1, ge=1)
    sort_by_date: bool = False


class ChunkHit(BaseModel):
    chunk_id: str
    article_id: str
    source_id: str
    chunk_index: int
    chunk_text: str
    chunk_word_count: int
    title: str
    description: str | None = None
    author: str
    tags: list[str] = []
    url: str
    published_date: str | None = None
    score: float
    highlights: dict[str, list[str]] | None = None


class SearchResponse(BaseModel):
    query: str
    mode: SearchMode
    total: int
    page: int
    size: int
    hits: list[ChunkHit]
