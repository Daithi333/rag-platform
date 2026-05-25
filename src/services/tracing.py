"""Request-scoped tracing with automatic hierarchy via contextvars.

Usage:
    # In the router — starts a new trace
    async with tracer.start_trace("rag_ask", metadata={...}):
        response = await service.ask(...)

    # In the service — automatically nests under the active trace
    @tracer.span("search")
    async def _retrieve(self, ...):
        ...

    # On the LLM client — records as a generation with token tracking
    @tracer.generation("llm_generate")
    async def generate(self, prompt):
        ...

The tracer no-ops when disabled (no Langfuse keys configured).
Uses Langfuse Python SDK v4 (get_client + start_as_current_observation).
"""

import functools
import time
from contextlib import asynccontextmanager
from typing import Any

from langfuse import Langfuse
import structlog

from src.config import LangfuseSettings

logger = structlog.getLogger(__name__)


class Tracer:
    """Thin tracing abstraction backed by Langfuse v4. No-ops when disabled."""

    def __init__(self):
        self._client = None
        self._enabled = False

    def configure(self, settings: LangfuseSettings) -> None:
        """Initialise the backing Langfuse client. Call once at app startup."""
        if self._enabled:
            return

        if not settings.enabled or not settings.public_key or not settings.secret_key:
            logger.info("Tracing disabled")
            return

        try:
            self._client = Langfuse(
                public_key=settings.public_key,
                secret_key=settings.secret_key,
                host=settings.host,
                flush_at=settings.flush_at,
                flush_interval=settings.flush_interval,
                debug=settings.debug,
            )
            self._enabled = True
            logger.info("Tracing enabled", host=settings.host)
        except Exception as e:
            logger.error("Failed to initialise tracing", error=str(e))

    @property
    def enabled(self) -> bool:
        return self._enabled

    @asynccontextmanager
    async def start_trace(self, name: str, metadata: dict[str, Any] | None = None):
        """Start a top-level trace (root span). Child spans nest automatically."""
        if not self._enabled:
            yield None
            return

        with self._client.start_as_current_observation(
            as_type="span",
            name=name,
            metadata=metadata or {},
        ) as root:
            yield root

        self._client.flush()

    def span(self, name: str):
        """Decorator that wraps an async function as a span under the active trace."""

        def decorator(fn):
            @functools.wraps(fn)
            async def wrapper(*args, **kwargs):
                if not self._enabled:
                    return await fn(*args, **kwargs)

                with self._client.start_as_current_observation(
                    as_type="span",
                    name=name,
                    input=_safe_input(args, kwargs),
                ) as span:
                    result = await fn(*args, **kwargs)
                    span.update(output=_safe_output(result))
                    return result

            return wrapper

        return decorator

    def generation(self, name: str):
        """Decorator that wraps an async function as an LLM generation span.

        Expects the decorated function to return an LLMResponse with
        text, model, prompt_tokens, completion_tokens attributes.
        """

        def decorator(fn):
            @functools.wraps(fn)
            async def wrapper(*args, **kwargs):
                if not self._enabled:
                    return await fn(*args, **kwargs)

                # First positional arg after self is typically the prompt
                prompt = args[1] if len(args) > 1 else kwargs.get("prompt", "")

                with self._client.start_as_current_observation(
                    as_type="generation",
                    name=name,
                    input=prompt,
                ) as gen:
                    start = time.time()
                    result = await fn(*args, **kwargs)
                    duration_ms = round((time.time() - start) * 1000, 2)

                    if hasattr(result, "text"):
                        gen.update(
                            output=result.text,
                            model=result.model,
                            usage_details={
                                "input": result.prompt_tokens,
                                "output": result.completion_tokens,
                            },
                            metadata={"duration_ms": duration_ms},
                        )

                    return result

            return wrapper

        return decorator

    def shutdown(self) -> None:
        if self._client:
            try:
                self._client.shutdown()
            except Exception:
                pass
            self._client = None
            self._enabled = False


def _safe_input(args, kwargs) -> dict[str, Any] | None:
    """Extract a safe representation of function inputs for tracing."""
    try:
        meaningful_args = args[1:] if args and hasattr(args[0], "__class__") else args
        if meaningful_args:
            return {"args": [str(a)[:200] for a in meaningful_args]}
        if kwargs:
            return {k: str(v)[:200] for k, v in kwargs.items()}
    except Exception:
        pass
    return None


def _safe_output(result) -> Any:
    """Extract a safe representation of function output for tracing."""
    try:
        if result is None:
            return None
        if hasattr(result, "model_dump"):
            return result.model_dump()
        if isinstance(result, dict):
            return result
        return str(result)[:500]
    except Exception:
        return None


# Module-level singleton — configured once at app startup
tracer = Tracer()
