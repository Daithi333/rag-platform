"""Smoke tests for external services. Require real API connectivity."""

import pytest

from src.services.devto.factory import make_devto_client
from src.services.embeddings.factory import make_embedding_client
from src.services.llm.base import LLMResponse
from src.services.llm.factory import make_llm_client


@pytest.mark.asyncio
async def test_devto_client_fetch():
    client = make_devto_client()
    articles = await client.fetch_articles(tag="python", page=1)
    assert isinstance(articles, list)


@pytest.mark.asyncio
async def test_devto_client_health_check():
    client = make_devto_client()
    result = await client.health_check()
    assert result["status"] == "ok"


@pytest.mark.asyncio
async def test_jina_embed_single():
    """Embed a single text via the Jina API (requires valid API key)."""
    client = make_embedding_client()
    embedding = await client.embed_single("Python error handling best practices")
    assert isinstance(embedding, list)
    assert len(embedding) > 0
    assert all(isinstance(v, float) for v in embedding)


@pytest.mark.asyncio
async def test_llm_health_check():
    """Check LLM provider is reachable (requires valid API key or running Ollama)."""
    client = make_llm_client()
    result = await client.health_check()
    assert result["status"] == "healthy"


@pytest.mark.asyncio
async def test_llm_generate():
    """Generate a short response from the configured LLM provider."""
    client = make_llm_client()
    response = await client.generate("Reply with exactly: hello")
    assert isinstance(response, LLMResponse)
    assert len(response.text) > 0


@pytest.mark.asyncio
async def test_llm_generate_stream():
    """Stream tokens from the configured LLM provider."""
    client = make_llm_client()
    stream = await client.generate_stream("Reply with exactly: hello")
    tokens = []
    async for token in stream:
        tokens.append(token)
    assert len(tokens) > 0
    assert all(isinstance(t, str) for t in tokens)


def test_langfuse_auth():
    """Verify Langfuse credentials are valid (requires running Langfuse instance)."""
    from langfuse import Langfuse

    from src.config import get_settings

    settings = get_settings()
    if not settings.langfuse.enabled:
        pytest.skip("Langfuse not enabled")

    client = Langfuse(
        public_key=settings.langfuse.public_key,
        secret_key=settings.langfuse.secret_key,
        host=settings.langfuse.host,
    )
    assert client.auth_check(), "Langfuse auth check failed — verify keys and host"
