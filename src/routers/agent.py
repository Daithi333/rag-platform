import json

import structlog
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from src.dependencies import CacheDep, EmbeddingDep, LLMDep, OpenSearchDep, SettingsDep
from src.schemas.api.agent import AgentAskRequest, AgentAskResponse
from src.services.agents.orchestrator import AgenticRAGService
from src.services.tracing import tracer

logger = structlog.getLogger(__name__)

router = APIRouter()


@router.post("/ask/agent", response_model=AgentAskResponse, tags=["Agentic RAG"])
async def ask_agent(
    request: AgentAskRequest,
    settings: SettingsDep,
    opensearch: OpenSearchDep,
    embedding_client: EmbeddingDep,
    llm_client: LLMDep,
    cache: CacheDep,
) -> AgentAskResponse:
    """Ask a question using the agentic RAG pipeline with guardrails, routing, and grading."""
    service = AgenticRAGService(
        opensearch=opensearch,
        embedding_client=embedding_client,
        llm_client=llm_client,
        opensearch_settings=settings.opensearch,
        agent_settings=settings.agent,
    )

    async with tracer.start_trace("agentic_rag_ask", metadata={"question": request.question}):
        state = await service.ask(question=request.question)

    return AgentAskResponse(
        question=state.question,
        answer=state.answer or "Unable to generate an answer.",
        sources=state.sources,
        chunks_used=len(state.graded_chunks),
        reasoning_steps=state.reasoning_steps,
        rewritten_query=state.current_query if state.current_query != state.question else None,
        model=state.model,
        duration_ms=state.duration_ms,
    )


@router.post("/ask/agent/stream", tags=["Agentic RAG"])
async def ask_agent_stream(
    request: AgentAskRequest,
    settings: SettingsDep,
    opensearch: OpenSearchDep,
    embedding_client: EmbeddingDep,
    llm_client: LLMDep,
    cache: CacheDep,
):
    """Stream agentic RAG reasoning steps and final answer via SSE."""
    service = AgenticRAGService(
        opensearch=opensearch,
        embedding_client=embedding_client,
        llm_client=llm_client,
        opensearch_settings=settings.opensearch,
        agent_settings=settings.agent,
    )

    async def generate_sse():
        try:
            async with tracer.start_trace(
                "agentic_rag_stream", metadata={"question": request.question}
            ):
                async for event in service.ask_stream(question=request.question):
                    if "step" in event:
                        yield f"data: {json.dumps({'step': event['step']})}\n\n"
                    elif "state" in event:
                        state = event["state"]
                        yield f"data: {
                            json.dumps(
                                {
                                    'answer': state.answer or 'Unable to generate an answer.',
                                    'sources': [s.model_dump() for s in state.sources],
                                    'chunks_used': len(state.graded_chunks),
                                    'model': state.model,
                                    'done': True,
                                }
                            )
                        }\n\n"
        except Exception as e:
            logger.exception("Agent stream error")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        generate_sse(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
