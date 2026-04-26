import logging
from contextlib import contextmanager
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.config import Settings
from src.dependencies import get_database, get_opensearch, get_settings
from src.main import app, create_lifespan


def _mock_database_factory():
    db = MagicMock()
    session = MagicMock()

    @contextmanager
    def fake_session():
        yield session

    db.get_session = fake_session
    return db


def _mock_opensearch_factory():
    client = MagicMock()
    client.health_check.return_value = {"status": "green", "healthy": True}
    client.close.return_value = None
    return client


# Replace the lifespan with one that uses mock factories
app.router.lifespan_context = create_lifespan(
    database_factory=_mock_database_factory,
    opensearch_factory=_mock_opensearch_factory,
)


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Configure test environment."""
    logging.disable(logging.CRITICAL)
    yield
    logging.disable(logging.NOTSET)


@pytest.fixture
def base_url():
    """Base URL for API endpoints."""
    return "/api/v1"


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    return Settings(
        app_version="0.1.0",
        environment="development",
        service_name="rag-platform-api",
    )


@pytest.fixture
def mock_database():
    """Mock database for dependency override."""
    return _mock_database_factory()


@pytest.fixture
def mock_opensearch():
    """Mock OpenSearchClient for dependency override."""
    return _mock_opensearch_factory()


@pytest.fixture
def client(mock_settings, mock_database, mock_opensearch):
    """Test client with mocked dependencies."""
    app.dependency_overrides[get_settings] = lambda: mock_settings
    app.dependency_overrides[get_database] = lambda: mock_database
    app.dependency_overrides[get_opensearch] = lambda: mock_opensearch

    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client

    app.dependency_overrides.clear()
