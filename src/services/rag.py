"""RAG service: search -> build context -> generate answer."""

from collections.abc import AsyncIterator

import structlog

from src.config import OpenSearchSettings
from src.schemas.api.search import ChunkHit, SearchMode
from src.services.embeddings.client import EmbeddingClient
from src.services.llm.client import LLMClient
from src.services.llm.prompts import build_rag_prompt
from src.services.opensearch.client import OpenSearchClient
from src.services.search import SearchService

logger = structlog.getLogger(__name__)


class RAGService:
    def __init__(
        self,
        opensearch: OpenSearchClient,
        embedding_client: EmbeddingClient,
        llm_client: LLMClient,
        opensearch_settings: OpenSearchSettings,
    ):
        self._search = SearchService(
            opensearch=opensearch,
            embedding_client=embedding_client,
            settings=opensearch_settings,
        )
        self._llm = llm_client

    async def ask(
        self,
        question: str,
        mode: SearchMode = SearchMode.HYBRID,
        num_chunks: int = 5,
        tags: list[str] | None = None,
    ) -> dict:
        """Answer a question using RAG: retrieve context then generate."""
        results = await self._search.search(
            query=question,
            mode=mode,
            size=num_chunks,
            tags=tags,
        )

        chunks: list[ChunkHit] = results["hits"]

        if not chunks:
            return {
                "answer": "I couldn't find any relevant articles to answer your question.",
                "sources": [],
                "chunks_used": 0,
            }

        prompt = build_rag_prompt(question, chunks)

        logger.info("Generating RAG answer", question=question, chunks_used=len(chunks))

        response = await self._llm.generate(prompt)

        sources = _extract_sources(chunks)

        return {
            "answer": response["text"],
            "sources": sources,
            "chunks_used": len(chunks),
            "model": response.get("model"),
            "duration_ms": response.get("total_duration_ms"),
        }

    async def ask_stream(
        self,
        question: str,
        mode: SearchMode = SearchMode.HYBRID,
        num_chunks: int = 5,
        tags: list[str] | None = None,
    ) -> AsyncIterator[str]:
        """Stream a RAG answer token by token."""
        results = await self._search.search(
            query=question,
            mode=mode,
            size=num_chunks,
            tags=tags,
        )

        chunks: list[ChunkHit] = results["hits"]

        if not chunks:
            yield "I couldn't find any relevant articles to answer your question."
            return

        prompt = build_rag_prompt(question, chunks)

        logger.info("Streaming RAG answer", question=question, chunks_used=len(chunks))

        async for token in self._llm.generate_stream(prompt):
            yield token


def _extract_sources(chunks: list[ChunkHit]) -> list[dict]:
    """Extract unique article sources from chunks."""
    seen = set()
    sources = []
    for chunk in chunks:
        if chunk.url and chunk.url not in seen:
            seen.add(chunk.url)
            sources.append(
                {
                    "title": chunk.title,
                    "url": chunk.url,
                    "author": chunk.author,
                }
            )
    return sources
