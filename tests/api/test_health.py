import pytest
from contextlib import contextmanager
from unittest.mock import MagicMock

from fastapi import APIRouter
from fastapi.testclient import TestClient

from src.dependencies import (
    get_database,
    get_embedding_client,
    get_llm_client,
    get_opensearch,
    get_settings,
)
from src.main import app


def _make_client(
    mock_settings, mock_database, mock_opensearch, mock_embedding_client=None, mock_llm_client=None
):
    from tests.api.conftest import _mock_embedding_factory, _mock_llm_factory

    app.dependency_overrides[get_settings] = lambda: mock_settings
    app.dependency_overrides[get_database] = lambda: mock_database
    app.dependency_overrides[get_opensearch] = lambda: mock_opensearch
    app.dependency_overrides[get_embedding_client] = lambda: (
        mock_embedding_client or _mock_embedding_factory()
    )
    app.dependency_overrides[get_llm_client] = lambda: mock_llm_client or _mock_llm_factory()
    return TestClient(app, raise_server_exceptions=False)


def test_health_success(client, base_url):
    """Test health endpoint returns correct response with service statuses."""
    response = client.get(f"{base_url}/health")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"

    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.1.0"
    assert data["environment"] == "development"
    assert data["service_name"] == "rag-platform-api"
    assert data["services"]["database"]["status"] == "healthy"
    assert data["services"]["opensearch"]["status"] == "healthy"
    assert data["services"]["embeddings"]["status"] == "healthy"


def test_health_degraded_when_opensearch_red(mock_settings, mock_database, base_url):
    """Test health returns degraded when OpenSearch cluster is red."""
    os_client = MagicMock()
    os_client.health_check.return_value = {"status": "red", "healthy": False}

    with _make_client(mock_settings, mock_database, os_client) as c:
        response = c.get(f"{base_url}/health")

    data = response.json()
    assert data["status"] == "degraded"
    assert data["services"]["opensearch"]["status"] == "degraded"
    assert data["services"]["database"]["status"] == "healthy"


def test_health_error_when_database_down(mock_settings, mock_opensearch, base_url):
    """Test health returns error when database is unreachable."""
    db = MagicMock()
    session = MagicMock()
    session.execute.side_effect = Exception("Connection refused")

    @contextmanager
    def failing_session():
        yield session

    db.get_session = failing_session

    with _make_client(mock_settings, db, mock_opensearch) as c:
        response = c.get(f"{base_url}/health")

    data = response.json()
    assert data["status"] == "error"
    assert data["services"]["database"]["status"] == "unhealthy"
    assert "Connection refused" in data["services"]["database"]["message"]


def test_health_error_when_opensearch_unreachable(mock_settings, mock_database, base_url):
    """Test health returns error when OpenSearch is unreachable."""
    os_client = MagicMock()
    os_client.health_check.return_value = {
        "status": "unreachable",
        "healthy": False,
        "error": "Connection refused",
    }

    with _make_client(mock_settings, mock_database, os_client) as c:
        response = c.get(f"{base_url}/health")

    data = response.json()
    assert data["status"] == "error"
    assert data["services"]["opensearch"]["status"] == "unhealthy"


def test_invalid_route(client, base_url):
    """Test invalid route returns 404."""
    response = client.get(f"{base_url}/nonexistent")

    assert response.status_code == 404
    data = response.json()
    assert data == {"error": "HTTP_ERROR", "message": "Not Found", "details": {}}


def test_invalid_route_no_base(client):
    """Test route without /api/v1 prefix returns 404."""
    response = client.get("/health")

    assert response.status_code == 404
    data = response.json()
    assert data == {"error": "HTTP_ERROR", "message": "Not Found", "details": {}}


def test_health_invalid_method(client, base_url):
    """Test health endpoint rejects POST method with 405."""
    response = client.post(f"{base_url}/health")

    assert response.status_code == 405
    data = response.json()
    assert data == {
        "error": "HTTP_ERROR",
        "message": "Method Not Allowed",
        "details": {},
    }


@pytest.fixture(scope="module")
def app_with_error_route():
    """Add test routes that trigger errors."""
    from src.main import app

    test_router = APIRouter(prefix="/api/v1/test")

    @test_router.get("/error")
    def trigger_error():
        raise ValueError("Test unhandled exception")

    app.include_router(test_router)
    return app


def test_unhandled_exception_returns_json(client, app_with_error_route):
    """Test unhandled exception returns 500 with JSON format."""
    response = client.get("/api/v1/test/error")

    assert response.status_code == 500
    assert response.headers["content-type"] == "application/json"

    data = response.json()

    assert data == {
        "error": "INTERNAL_ERROR",
        "message": "An unexpected error occurred",
        "details": {},
    }
