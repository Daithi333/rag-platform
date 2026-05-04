from unittest.mock import AsyncMock, MagicMock, patch


MOCK_OS_RESULTS = {
    "total": 2,
    "hits": [
        {
            "chunk_id": "chunk-1",
            "article_id": "art-1",
            "source_id": "123",
            "chunk_index": 0,
            "chunk_text": "Python error handling with try except",
            "chunk_word_count": 6,
            "title": "Error Handling in Python",
            "description": "A guide to exceptions",
            "author": "Test Author",
            "tags": ["python"],
            "url": "https://dev.to/test/article",
            "published_date": "2026-01-15T00:00:00+00:00",
            "_score": 1.5,
            "_id": "doc-1",
            "_highlights": {"chunk_text": ["<mark>Python</mark> error handling"]},
        },
        {
            "chunk_id": "chunk-2",
            "article_id": "art-2",
            "source_id": "456",
            "chunk_index": 0,
            "chunk_text": "Exception management patterns",
            "chunk_word_count": 3,
            "title": "Python Exceptions",
            "author": "Another Author",
            "tags": ["python"],
            "url": "https://dev.to/test/article-2",
            "_score": 1.2,
            "_id": "doc-2",
        },
    ],
}

MOCK_EMBEDDING = [0.1] * 1024


def _mock_embedding_client():
    client = MagicMock()
    client.embed_single = AsyncMock(return_value=MOCK_EMBEDDING)
    return client


def _patch_embedding():
    return patch(
        "src.routers.search.make_embedding_client",
        return_value=_mock_embedding_client(),
    )


def test_search_bm25(client, mock_opensearch, base_url):
    """Test BM25 search flows through service to OpenSearch client."""
    mock_opensearch.search.return_value = MOCK_OS_RESULTS

    with _patch_embedding():
        response = client.post(
            f"{base_url}/search",
            json={"query": "python errors", "mode": "bm25"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "python errors"
    assert data["mode"] == "bm25"
    assert data["total"] == 2
    assert len(data["hits"]) == 2
    assert data["hits"][0]["score"] == 1.5
    assert data["hits"][0]["title"] == "Error Handling in Python"

    # BM25 should not pass a pipeline
    call_kwargs = mock_opensearch.search.call_args
    assert call_kwargs[1].get("pipeline") is None


def test_search_hybrid_uses_pipeline(client, mock_opensearch, base_url):
    """Test hybrid search passes the RRF pipeline."""
    mock_opensearch.search.return_value = {"total": 0, "hits": []}

    with _patch_embedding():
        response = client.post(
            f"{base_url}/search",
            json={"query": "async programming", "mode": "hybrid"},
        )

    assert response.status_code == 200
    assert response.json()["mode"] == "hybrid"

    call_kwargs = mock_opensearch.search.call_args
    assert call_kwargs[1].get("pipeline") == "hybrid-rrf-pipeline"


def test_search_hybrid_is_default(client, mock_opensearch, base_url):
    """Test default search mode is hybrid."""
    mock_opensearch.search.return_value = {"total": 0, "hits": []}

    with _patch_embedding():
        response = client.post(
            f"{base_url}/search",
            json={"query": "python"},
        )

    assert response.status_code == 200
    assert response.json()["mode"] == "hybrid"


def test_search_bm25_skips_embedding(client, mock_opensearch, base_url):
    """Test BM25 mode does not call the embedding client."""
    mock_opensearch.search.return_value = {"total": 0, "hits": []}

    with _patch_embedding() as mock_factory:
        response = client.post(
            f"{base_url}/search",
            json={"query": "python", "mode": "bm25"},
        )

    assert response.status_code == 200
    mock_client = mock_factory.return_value
    mock_client.embed_single.assert_not_called()


def test_search_with_tags(client, mock_opensearch, base_url):
    """Test tag filter is passed through to the query."""
    mock_opensearch.search.return_value = {"total": 0, "hits": []}

    with _patch_embedding():
        response = client.post(
            f"{base_url}/search",
            json={"query": "fastapi", "tags": ["python", "webdev"]},
        )

    assert response.status_code == 200
    query_body = mock_opensearch.search.call_args[0][1]
    # Tags should appear somewhere in the query body as a filter
    assert "python" in str(query_body)


def test_search_pagination(client, mock_opensearch, base_url):
    """Test pagination is calculated correctly."""
    mock_opensearch.search.return_value = {"total": 0, "hits": []}

    with _patch_embedding():
        response = client.post(
            f"{base_url}/search",
            json={"query": "python", "size": 5, "page": 3},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 3
    assert data["size"] == 5


def test_search_highlights_included(client, mock_opensearch, base_url):
    """Test highlights are passed through in the response."""
    mock_opensearch.search.return_value = MOCK_OS_RESULTS

    with _patch_embedding():
        response = client.post(
            f"{base_url}/search",
            json={"query": "python", "mode": "bm25"},
        )

    data = response.json()
    assert data["hits"][0]["highlights"] is not None
    assert "chunk_text" in data["hits"][0]["highlights"]


def test_search_empty_query_rejected(client, base_url):
    """Test empty query returns validation error."""
    response = client.post(
        f"{base_url}/search",
        json={"query": ""},
    )
    assert response.status_code == 422


def test_search_invalid_mode_rejected(client, base_url):
    """Test invalid search mode returns validation error."""
    response = client.post(
        f"{base_url}/search",
        json={"query": "python", "mode": "invalid"},
    )
    assert response.status_code == 422
