from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from src.dependencies import EmbeddingDep, LLMDep, OpenSearchDep, SettingsDep
from src.schemas.api.rag import AskRequest, AskResponse, Source
from src.services.rag import RAGService

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

    result = await service.ask(
        question=request.question,
        mode=request.mode,
        num_chunks=request.num_chunks,
        tags=request.tags,
    )

    return AskResponse(
        question=request.question,
        answer=result["answer"],
        sources=[Source(**s) for s in result["sources"]],
        chunks_used=result["chunks_used"],
        model=result.get("model"),
        duration_ms=result.get("duration_ms"),
    )


@router.post("/ask/stream", tags=["RAG"])
async def ask_stream(
    request: AskRequest,
    settings: SettingsDep,
    opensearch: OpenSearchDep,
    embedding_client: EmbeddingDep,
    llm_client: LLMDep,
):
    """Stream a RAG-generated answer token by token."""
    service = _make_rag_service(opensearch, embedding_client, llm_client, settings)

    async def generate():
        async for token in service.ask_stream(
            question=request.question,
            mode=request.mode,
            num_chunks=request.num_chunks,
            tags=request.tags,
        ):
            yield token

    return StreamingResponse(generate(), media_type="text/plain")
