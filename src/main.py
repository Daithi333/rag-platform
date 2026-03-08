import os

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.logs import setup_logging
from src.middlewares import RequestLoggingMiddleware
from src.routers import health

setup_logging()

app = FastAPI(
    title="RAG Platform API",
    description="Public Data Source Ingestion and RAG querying platform",
    version=os.getenv("APP_VERSION", "0.1.0"),
)

app.include_router(health.router, prefix="/api/v1")

app.add_middleware(RequestLoggingMiddleware)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Handle unhandled exceptions and return json response. Logging handled in middleware."""
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "detail": "An unexpected error occurred",
        },
    )


if __name__ == "__main__":
    uvicorn.run(app, port=8000, host="0.0.0.0")
