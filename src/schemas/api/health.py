from typing import Literal

from pydantic import BaseModel, ConfigDict


class ServiceStatus(BaseModel):
    """Individual service status."""

    status: str
    message: str | None


class HealthResponse(BaseModel):
    """Health check response model."""

    status: Literal["ok", "degraded", "error"]
    version: str
    environment: str
    service_name: str
    services: dict[str, ServiceStatus] | None

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "status": "ok",
                    "version": "0.1.0",
                    "environment": "development",
                    "service_name": "rag-platform-api",
                    "services": {
                        "database": {
                            "status": "healthy",
                            "message": "Connected successfully",
                        },
                    },
                }
            ]
        }
    )
