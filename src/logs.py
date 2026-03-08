import logging
import sys
from typing import cast

import structlog
from structlog.typing import Processor

from src.config import get_settings


def setup_logging() -> None:
    """Configure logging based on environment."""
    settings = get_settings()

    # Shared processors for both formats
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.environment == "development":
        # Human-readable for local dev
        processors = shared_processors + [structlog.dev.ConsoleRenderer(colors=True)]
    else:
        # JSON for production (CloudWatch, Datadog, etc.)
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]

    structlog.configure(
        processors=cast(list[Processor], processors),
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure stdlib logging (for third-party libraries)
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )

    # Disable uvicorn access logs as we have custom logging middleware
    logging.getLogger("uvicorn.access").disabled = True

    # Optional: Keep uvicorn error logs
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
