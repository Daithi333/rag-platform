"""Unit tests for the tracing module."""

import pytest

from src.config import LangfuseSettings
from src.services.tracing import Tracer


@pytest.fixture
def disabled_settings():
    return LangfuseSettings(
        enabled=False, public_key="", secret_key="", host="http://localhost:3001"
    )


@pytest.fixture
def enabled_settings_no_keys():
    return LangfuseSettings(
        enabled=True, public_key="", secret_key="", host="http://localhost:3001"
    )


class TestTracerConfigure:
    def test_disabled_when_enabled_false(self, disabled_settings):
        t = Tracer()
        t.configure(disabled_settings)
        assert t.enabled is False

    def test_disabled_when_keys_missing(self, enabled_settings_no_keys):
        t = Tracer()
        t.configure(enabled_settings_no_keys)
        assert t.enabled is False

    def test_does_not_reconfigure(self, disabled_settings):
        t = Tracer()
        t._enabled = True
        t.configure(disabled_settings)
        assert t.enabled is True


class TestTracerNoOp:
    @pytest.mark.asyncio
    async def test_start_trace_yields_none_when_disabled(self, disabled_settings):
        t = Tracer()
        t.configure(disabled_settings)

        async with t.start_trace("test") as trace:
            assert trace is None

    @pytest.mark.asyncio
    async def test_span_decorator_passes_through_when_disabled(self, disabled_settings):
        t = Tracer()
        t.configure(disabled_settings)

        @t.span("test_span")
        async def my_func(x):
            return x * 2

        result = await my_func(5)
        assert result == 10

    @pytest.mark.asyncio
    async def test_generation_decorator_passes_through_when_disabled(self, disabled_settings):
        t = Tracer()
        t.configure(disabled_settings)

        @t.generation("test_gen")
        async def my_generate(prompt):
            return {"text": "hello", "model": "test"}

        result = await my_generate("hi")
        assert result["text"] == "hello"

    def test_shutdown_when_not_configured(self, disabled_settings):
        t = Tracer()
        t.configure(disabled_settings)
        t.shutdown()
        assert t.enabled is False
