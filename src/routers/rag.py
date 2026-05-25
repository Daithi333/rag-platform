import json

import structlog
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from src.dependencies import CacheDep, EmbeddingDep, LLMDep, OpenSearchDep, SettingsDep
from src.exceptions import AppError
from src.schemas.api.rag import AskRequest, AskResponse
from src.services.rag import RAGService
from src.services.tracing import tracer

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
    cache: CacheDep,
) -> AskResponse:
    """Ask a question and get a RAG-generated answer with sources."""
    if cache:
        cached = await cache.get(request)
        if cached:
            return cached

    service = _make_rag_service(opensearch, embedding_client, llm_client, settings)

    async with tracer.start_trace("rag_ask", metadata={"question": request.question}):
        response = await service.ask(
            question=request.question,
            mode=request.mode,
            num_chunks=request.num_chunks,
            tags=request.tags,
        )

    if cache:
        await cache.set(request, response)

    return response


@router.post("/ask/stream", tags=["RAG"])
async def ask_stream(
    request: AskRequest,
    settings: SettingsDep,
    opensearch: OpenSearchDep,
    embedding_client: EmbeddingDep,
    llm_client: LLMDep,
    cache: CacheDep,
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
            if cache:
                cached = await cache.get(request)
                if cached:
                    yield _sse_event(
                        {
                            "sources": [s.model_dump() for s in cached.sources],
                            "chunks_used": cached.chunks_used,
                        }
                    )
                    yield _sse_event({"chunk": cached.answer})
                    yield _sse_event({"done": True})
                    return

            async with tracer.start_trace(
                "rag_ask_stream", metadata={"question": request.question}
            ):
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

                yield _sse_event(
                    {
                        "sources": [s.model_dump() for s in context.sources],
                        "chunks_used": context.chunks_used,
                    }
                )

                full_answer = ""
                async for token in token_stream:
                    full_answer += token
                    yield _sse_event({"chunk": token})

                yield _sse_event({"done": True})

            # Report generation to Langfuse after stream completes
            if tracer.enabled and token_stream:
                with tracer._client.start_as_current_observation(
                    as_type="generation",
                    name="llm_generate_stream",
                    input=request.question,
                ) as gen:
                    update_kwargs = {
                        "output": full_answer,
                        "model": token_stream.usage.model,
                    }
                    if token_stream.usage.usage_details:
                        update_kwargs["usage_details"] = token_stream.usage.usage_details
                    gen.update(**update_kwargs)

            if cache and full_answer:
                response = AskResponse(
                    question=request.question,
                    answer=full_answer,
                    sources=context.sources,
                    chunks_used=context.chunks_used,
                )
                await cache.set(request, response)

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
