import time
import uuid
from typing import Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all HTTP requests with timing and context."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())
        start_time = time.time()

        # Bind context for this request
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else None,
        )

        request.state.request_id = request_id

        # Process request
        status_code = 200
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception as exc:
            logger.exception("Unhandled Exception", exception=exc.__class__.__name__)
            status_code = 500
            raise  # re-raise for exception handler to format
        finally:
            duration_ms = round((time.time() - start_time) * 1000, 2)

            if status_code >= 500:
                logger.error(
                    "request", status_code=status_code, duration_ms=duration_ms
                )
            elif status_code >= 400:
                logger.warning(
                    "request", status_code=status_code, duration_ms=duration_ms
                )
            else:
                logger.info("request", status_code=status_code, duration_ms=duration_ms)
