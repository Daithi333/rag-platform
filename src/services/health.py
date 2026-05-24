import structlog
from typing import Literal
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.db.base import BaseDatabase
from src.schemas.api.health import HealthResponse, ServiceStatus
from src.services.cache.client import CacheClient
from src.services.embeddings.client import EmbeddingClient
from src.services.llm.base import BaseLLMClient
from src.services.opensearch.client import OpenSearchClient

logger = structlog.getLogger(__name__)


async def get_health(
    database: BaseDatabase,
    opensearch: OpenSearchClient,
    embedding_client: EmbeddingClient,
    llm_client: BaseLLMClient,
    cache: CacheClient | None,
    version: str,
    environment: str,
    service_name: str,
) -> HealthResponse:
    """Run all health checks and return the aggregated response."""
    services = {}

    with database.get_session() as session:
        services["database"] = _check_database(session)

    services["opensearch"] = _check_opensearch(opensearch)
    services["embeddings"] = _check_embedding_client(embedding_client)
    services["llm"] = await _check_llm(llm_client)
    services["cache"] = _check_cache(cache)
    services["tracing"] = _check_tracing()

    any_unhealthy = any(s.status == "unhealthy" for s in services.values())
    any_degraded = any(s.status == "degraded" for s in services.values())

    status: Literal["ok", "degraded", "error"] = "ok"
    if any_unhealthy:
        status = "error"
    elif any_degraded:
        status = "degraded"

    return HealthResponse(
        status=status,
        version=version,
        environment=environment,
        service_name=service_name,
        services=services,
    )


def _check_database(session: Session) -> ServiceStatus:
    try:
        session.execute(text("SELECT 1"))
        return ServiceStatus(status="healthy", message=None)
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        return ServiceStatus(status="unhealthy", message=str(e))


def _check_opensearch(client: OpenSearchClient) -> ServiceStatus:
    result = client.health_check()
    if result["healthy"]:
        return ServiceStatus(status="healthy", message=f"cluster: {result['status']}")
    if result.get("error"):
        return ServiceStatus(status="unhealthy", message=result["error"])
    return ServiceStatus(status="degraded", message=f"cluster: {result['status']}")


def _check_embedding_client(client: EmbeddingClient) -> ServiceStatus:
    if client._settings.api_key and client._settings.api_key != "your_jina_api_key_here":
        return ServiceStatus(status="healthy", message=f"model: {client._settings.model}")
    return ServiceStatus(status="degraded", message="API key not configured")


async def _check_llm(client: BaseLLMClient) -> ServiceStatus:
    result = await client.health_check()
    if result["status"] == "healthy":
        detail = result.get("version") or result.get("provider") or "connected"
        return ServiceStatus(status="healthy", message=detail)
    return ServiceStatus(status="unhealthy", message=result.get("error", "unreachable"))


def _check_cache(client: CacheClient | None) -> ServiceStatus:
    if client is None:
        return ServiceStatus(status="degraded", message="not configured")
    try:
        client._redis.ping()
        return ServiceStatus(status="healthy", message="connected")
    except Exception as e:
        return ServiceStatus(status="degraded", message=str(e))


def _check_tracing() -> ServiceStatus:
    from src.services.tracing import tracer

    if tracer.enabled:
        return ServiceStatus(status="healthy", message="enabled")
    return ServiceStatus(status="degraded", message="disabled")
