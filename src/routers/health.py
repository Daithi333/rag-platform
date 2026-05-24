from fastapi import APIRouter

from src.dependencies import CacheDep, DatabaseDep, EmbeddingDep, LLMDep, OpenSearchDep, SettingsDep
from src.schemas.api.health import HealthResponse
from src.services.health import get_health

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check(
    settings: SettingsDep,
    database: DatabaseDep,
    opensearch: OpenSearchDep,
    embedding_client: EmbeddingDep,
    llm_client: LLMDep,
    cache: CacheDep,
) -> HealthResponse:
    """Health check endpoint with liveness status of backing services."""
    return await get_health(
        database=database,
        opensearch=opensearch,
        embedding_client=embedding_client,
        llm_client=llm_client,
        cache=cache,
        version=settings.app_version,
        environment=settings.environment,
        service_name=settings.service_name,
    )
