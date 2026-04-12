import pytest

from src.services.devto.factory import make_devto_client


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
