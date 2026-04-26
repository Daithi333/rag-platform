import pytest

from src.services.devto.factory import make_devto_client
from src.services.embeddings.factory import make_embedding_client


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
    """Smoke test: embed a single text via the Jina API (requires valid API key)."""
    client = make_embedding_client()
    embedding = await client.embed_single("Python error handling best practices")
    assert isinstance(embedding, list)
    assert len(embedding) > 0
    assert all(isinstance(v, float) for v in embedding)
