"""API tests for the RAG endpoint."""

from unittest.mock import AsyncMock, MagicMock

from src.dependencies import get_cache
from src.main import app
from src.schemas.api.rag import AskResponse, Source

MOCK_SEARCH_HITS = {
    "total": 2,
    "hits": [
        {
            "chunk_id": "c1",
            "article_id": "a1",
            "source_id": "100",
            "chunk_index": 0,
            "chunk_text": "Python uses try/except for error handling.",
            "chunk_word_count": 7,
            "title": "Error Handling Guide",
            "author": "Author A",
            "tags": ["python"],
            "url": "https://dev.to/test/error-handling",
            "_score": 1.5,
            "_id": "d1",
        },
        {
            "chunk_id": "c2",
            "article_id": "a2",
            "source_id": "200",
            "chunk_index": 0,
            "chunk_text": "Custom exceptions improve code clarity.",
            "chunk_word_count": 5,
            "title": "Custom Exceptions",
            "author": "Author B",
            "tags": ["python"],
            "url": "https://dev.to/test/custom-exceptions",
            "_score": 1.2,
            "_id": "d2",
        },
    ],
}


def test_ask_returns_answer(client, mock_opensearch, base_url):
    """Test /ask returns a generated answer with sources."""
    mock_opensearch.search.return_value = MOCK_SEARCH_HITS

    response = client.post(
        f"{base_url}/ask",
        json={"question": "How do I handle errors in Python?"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["question"] == "How do I handle errors in Python?"
    assert data["answer"] == "This is a test answer."
    assert data["chunks_used"] == 2
    assert len(data["sources"]) == 2
    assert data["sources"][0]["title"] == "Error Handling Guide"
    assert data["sources"][0]["url"] == "https://dev.to/test/error-handling"


def test_ask_no_results(client, mock_opensearch, base_url):
    """Test /ask with no search results returns a helpful message."""
    mock_opensearch.search.return_value = {"total": 0, "hits": []}

    response = client.post(
        f"{base_url}/ask",
        json={"question": "What is quantum computing?"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "couldn't find" in data["answer"].lower()
    assert data["chunks_used"] == 0
    assert data["sources"] == []


def test_ask_with_tags(client, mock_opensearch, base_url):
    """Test /ask passes tags to the search."""
    mock_opensearch.search.return_value = MOCK_SEARCH_HITS

    response = client.post(
        f"{base_url}/ask",
        json={"question": "FastAPI tips", "tags": ["python"]},
    )

    assert response.status_code == 200
    query_body = mock_opensearch.search.call_args[0][1]
    assert "python" in str(query_body)


def test_ask_empty_question_rejected(client, base_url):
    """Test empty question returns validation error."""
    response = client.post(f"{base_url}/ask", json={"question": ""})
    assert response.status_code == 422


def test_ask_includes_model_info(client, mock_opensearch, base_url):
    """Test response includes model and timing metadata."""
    mock_opensearch.search.return_value = MOCK_SEARCH_HITS

    response = client.post(
        f"{base_url}/ask",
        json={"question": "Python best practices"},
    )

    data = response.json()
    assert data["model"] == "test-model"
    assert data["duration_ms"] == 100.0


def test_ask_cache_hit_skips_llm(client, mock_opensearch, mock_llm_client, base_url):
    """Test that a cache hit returns without calling the LLM."""
    cached_response = AskResponse(
        question="cached question",
        answer="cached answer",
        sources=[Source(title="Cached Article", url="https://example.com", author="Author")],
        chunks_used=3,
        model="cached-model",
    )

    mock_cache = MagicMock()
    mock_cache.get = AsyncMock(return_value=cached_response)
    mock_cache.set = AsyncMock()
    app.dependency_overrides[get_cache] = lambda: mock_cache

    response = client.post(
        f"{base_url}/ask",
        json={"question": "cached question"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "cached answer"
    assert data["model"] == "cached-model"
    mock_llm_client.generate.assert_not_called()
    mock_opensearch.search.assert_not_called()
