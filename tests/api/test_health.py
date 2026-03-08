import pytest
from fastapi import APIRouter


def test_health_success(client, base_url):
    """Test health endpoint returns correct response."""
    response = client.get(f"{base_url}/health")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"

    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.1.0"
    assert data["environment"] == "development"
    assert data["service_name"] == "rag-platform-api"


def test_health_invalid_method(client, base_url):
    """Test health endpoint rejects POST method."""
    response = client.post(f"{base_url}/health")

    assert response.status_code == 405
    data = response.json()
    assert data == {"detail": "Method Not Allowed"}


def test_invalid_route(client, base_url):
    """Test invalid route returns 404."""
    response = client.get(f"{base_url}/nonexistent")

    assert response.status_code == 404
    data = response.json()
    assert data == {"detail": "Not Found"}


def test_invalid_route_no_base(client):
    """Test route without /api/v1 prefix returns 404."""
    response = client.get("/health")

    assert response.status_code == 404
    data = response.json()
    assert data == {"detail": "Not Found"}


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

    assert data == {"error": "InternalServerError", "detail": "An unexpected error occurred"}
