"""RAG service: search -> build context -> generate answer."""

from dataclasses import dataclass

import structlog

from src.config import OpenSearchSettings
from src.schemas.api.rag import AskResponse, Source
from src.schemas.api.search import ChunkHit, SearchMode
from src.services.embeddings.client import EmbeddingClient
from src.services.llm.base import BaseLLMClient, StreamResponse
from src.services.llm.prompts import build_rag_prompt
from src.services.opensearch.client import OpenSearchClient
from src.services.search import SearchService

from src.services.tracing import tracer

logger = structlog.getLogger(__name__)


@dataclass
class RAGContext:
    """Intermediate result from retrieval, used by both ask and ask_stream."""

    prompt: str
    sources: list[Source]
    chunks_used: int


class RAGService:
    def __init__(
        self,
        opensearch: OpenSearchClient,
        embedding_client: EmbeddingClient,
        llm_client: BaseLLMClient,
        opensearch_settings: OpenSearchSettings,
    ):
        self._search = SearchService(
            opensearch=opensearch,
            embedding_client=embedding_client,
            settings=opensearch_settings,
        )
        self._llm = llm_client

    @tracer.span("retrieve")
    async def _retrieve(
        self,
        question: str,
        mode: SearchMode,
        num_chunks: int,
        tags: list[str] | None,
    ) -> RAGContext | None:
        """Retrieve relevant chunks and build the prompt. Returns None if no results."""
        results = await self._search.search(
            query=question,
            mode=mode,
            size=num_chunks,
            tags=tags,
        )

        chunks: list[ChunkHit] = results["hits"]

        if not chunks:
            return None

        prompt = build_rag_prompt(question, chunks)
        sources = _extract_sources(chunks)

        logger.info("RAG context prepared", question=question, chunks_used=len(chunks))

        return RAGContext(prompt=prompt, sources=sources, chunks_used=len(chunks))

    async def ask(
        self,
        question: str,
        mode: SearchMode = SearchMode.HYBRID,
        num_chunks: int = 5,
        tags: list[str] | None = None,
    ) -> AskResponse:
        """Answer a question using RAG: retrieve context then generate."""
        context = await self._retrieve(question, mode, num_chunks, tags)

        if context is None:
            return AskResponse(
                question=question,
                answer="I couldn't find any relevant articles to answer your question.",
                sources=[],
                chunks_used=0,
            )

        response = await self._llm.generate(context.prompt)

        return AskResponse(
            question=question,
            answer=response.text,
            sources=context.sources,
            chunks_used=context.chunks_used,
            model=response.model,
            duration_ms=response.total_duration_ms,
        )

    async def ask_stream(
        self,
        question: str,
        mode: SearchMode = SearchMode.HYBRID,
        num_chunks: int = 5,
        tags: list[str] | None = None,
    ) -> tuple[RAGContext | None, StreamResponse | None]:
        """Retrieve context and return metadata + a token stream.

        Returns a tuple of (context, stream). If context is None,
        no results were found and the stream will be None.
        After iterating the stream, stream.usage contains token counts.
        """
        context = await self._retrieve(question, mode, num_chunks, tags)

        if context is None:
            return None, None

        stream = await self._llm.generate_stream(context.prompt)
        return context, stream


def _extract_sources(chunks: list[ChunkHit]) -> list[Source]:
    """Extract unique article sources from chunks."""
    seen: set[str] = set()
    sources: list[Source] = []
    for chunk in chunks:
        if chunk.url and chunk.url not in seen:
            seen.add(chunk.url)
            sources.append(
                Source(
                    title=chunk.title,
                    url=chunk.url,
                    author=chunk.author,
                )
            )
    return sources
