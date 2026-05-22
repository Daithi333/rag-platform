import json

import structlog
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from src.dependencies import EmbeddingDep, LLMDep, OpenSearchDep, SettingsDep
from src.exceptions import AppError
from src.schemas.api.rag import AskRequest, AskResponse
from src.services.rag import RAGService

logger = structlog.getLogger(__name__)

router = APIRouter()


def _make_rag_service(
    opensearch: OpenSearchDep,
    embedding_client: EmbeddingDep,
    llm_client: LLMDep,
    settings: SettingsDep,
) -> RAGService:
    return RAGService(
        opensearch=opensearch,
        embedding_client=embedding_client,
        llm_client=llm_client,
        opensearch_settings=settings.opensearch,
    )


@router.post("/ask", response_model=AskResponse, tags=["RAG"])
async def ask(
    request: AskRequest,
    settings: SettingsDep,
    opensearch: OpenSearchDep,
    embedding_client: EmbeddingDep,
    llm_client: LLMDep,
) -> AskResponse:
    """Ask a question and get a RAG-generated answer with sources."""
    service = _make_rag_service(opensearch, embedding_client, llm_client, settings)

    return await service.ask(
        question=request.question,
        mode=request.mode,
        num_chunks=request.num_chunks,
        tags=request.tags,
    )


@router.post("/ask/stream", tags=["RAG"])
async def ask_stream(
    request: AskRequest,
    settings: SettingsDep,
    opensearch: OpenSearchDep,
    embedding_client: EmbeddingDep,
    llm_client: LLMDep,
):
    """Stream a RAG answer using Server-Sent Events.

    Event sequence:
      1. metadata: {sources, chunks_used}
      2. chunk (repeated): {chunk: "token"}
      3. done: {done: true}
    """
    service = _make_rag_service(opensearch, embedding_client, llm_client, settings)

    async def generate_sse():
        try:
            context, token_stream = await service.ask_stream(
                question=request.question,
                mode=request.mode,
                num_chunks=request.num_chunks,
                tags=request.tags,
            )

            if context is None:
                yield _sse_event(
                    {
                        "answer": "I couldn't find any relevant articles to answer your question.",
                        "sources": [],
                        "chunks_used": 0,
                        "done": True,
                    }
                )
                return

            # Send metadata first so the UI can render sources immediately
            yield _sse_event(
                {
                    "sources": [s.model_dump() for s in context.sources],
                    "chunks_used": context.chunks_used,
                }
            )

            # Stream LLM tokens
            async for token in token_stream:
                yield _sse_event({"chunk": token})

            # Signal completion
            yield _sse_event({"done": True})

        except AppError as e:
            logger.error("Stream error", error=e.message, code=e.code)
            yield _sse_event({"error": e.message})
        except Exception:
            logger.exception("Unexpected stream error")
            yield _sse_event({"error": "An unexpected error occurred"})

    return StreamingResponse(
        generate_sse(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


def _sse_event(data: dict) -> str:
    """Format a dict as an SSE event."""
    return f"data: {json.dumps(data)}\n\n"
