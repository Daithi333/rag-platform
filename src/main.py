import os
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

import structlog
import uvicorn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from opensearchpy import OpenSearch
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.config import get_settings
from src.db.factory import make_database
from src.exceptions import AppError, ErrorCode
from src.logs import setup_logging
from src.middlewares import RequestLoggingMiddleware
from src.routers import health
from src.schemas.api.errors import ErrorResponse

setup_logging()
logger = structlog.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()

    database = make_database()
    app.state.database = database

    opensearch = OpenSearch(
        hosts=[settings.opensearch.host],
        use_ssl=False,
        verify_certs=False,
        ssl_show_warn=False,
    )
    app.state.opensearch = opensearch
    logger.info("Services initialised", opensearch_host=settings.opensearch.host)

    yield

    database.teardown()
    opensearch.close()
    logger.info("Services shut down")


app = FastAPI(
    title="RAG Platform API",
    description="Public Data Source Ingestion and RAG querying platform",
    version=os.getenv("APP_VERSION", "0.1.0"),
    lifespan=lifespan,
)

app.include_router(health.router, prefix="/api/v1")

app.add_middleware(RequestLoggingMiddleware)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    """Map domain errors to structured HTTP responses"""
    app_error_status_map = {
        ErrorCode.NOT_FOUND: 404,
        ErrorCode.CONFLICT: 409,
        ErrorCode.VALIDATION_ERROR: 422,
    }
    status_code = app_error_status_map.get(exc.code, 500)
    response = ErrorResponse(error=exc.code, message=exc.message, details=exc.details)
    return JSONResponse(status_code=status_code, content=response.model_dump())


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """Reformat Pydantic / Request Validation Errors"""
    errors = [
        {
            "field": " -> ".join(str(loc) for loc in err.get("loc", [])),
            "message": err.get("msg", ""),
            "type": err.get("type", ""),
        }
        for err in exc.errors()
    ]
    response = ErrorResponse(
        error=ErrorCode.VALIDATION_ERROR,
        message="Request validation failed",
        details={"errors": errors},
    )
    return JSONResponse(status_code=422, content=response.model_dump())


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Reformat Starlette HTTP exceptions (404 for invalid routes, 405 method not allowed, etc.)"""
    response = ErrorResponse(error=ErrorCode.HTTP_ERROR, message=str(exc.detail), details={})
    return JSONResponse(status_code=exc.status_code, content=response.model_dump())


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Handle unhandled exceptions and return JSON response. Logging handled in middleware."""
    response = ErrorResponse(
        error=ErrorCode.INTERNAL_ERROR,
        message="An unexpected error occurred",
        details={},
    )
    return JSONResponse(status_code=500, content=response.model_dump())


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
