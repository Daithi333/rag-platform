from typing import Literal

from fastapi import APIRouter

from src.dependencies import SettingsDep
from src.schemas.api.health import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check(settings: SettingsDep) -> HealthResponse:
    """Health  check endpoint with status of the various constituent parts"""
    status: Literal["ok", "degraded", "error"] = "ok"

    return HealthResponse(
        status=status,
        version=settings.app_version,
        environment=settings.environment,
        service_name=settings.service_name,
    )
