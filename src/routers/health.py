from typing import Literal

from fastapi import APIRouter

from src.dependencies import DatabaseDep, OpenSearchDep, SettingsDep
from src.schemas.api.health import HealthResponse
from src.services.health import check_database, check_opensearch

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check(
    settings: SettingsDep,
    database: DatabaseDep,
    opensearch: OpenSearchDep,
) -> HealthResponse:
    """Health check endpoint with liveness status of backing services."""
    services = {}

    with database.get_session() as session:
        services["database"] = check_database(session)

    services["opensearch"] = check_opensearch(opensearch)

    any_unhealthy = any(s.status == "unhealthy" for s in services.values())
    any_degraded = any(s.status == "degraded" for s in services.values())

    status: Literal["ok", "degraded", "error"] = "ok"
    if any_unhealthy:
        status = "error"
    elif any_degraded:
        status = "degraded"

    return HealthResponse(
        status=status,
        version=settings.app_version,
        environment=settings.environment,
        service_name=settings.service_name,
        services=services,
    )
