import logging
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.config import Settings
from src.dependencies import (
    get_database,
    get_embedding_client,
    get_llm_client,
    get_opensearch,
    get_settings,
)
from src.main import app, create_lifespan
from src.services.llm.base import LLMResponse


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


def _mock_embedding_factory():
    client = MagicMock()
    client.embed_single = AsyncMock(return_value=[0.1] * 1024)
    client.embed_texts = AsyncMock(return_value=[[0.1] * 1024])
    return client


def _mock_llm_factory():
    client = MagicMock()
    client.generate = AsyncMock(
        return_value=LLMResponse(
            text="This is a test answer.",
            model="test-model",
            total_duration_ms=100.0,
            prompt_tokens=50,
            completion_tokens=20,
        )
    )
    client.health_check = AsyncMock(
        return_value={
            "status": "healthy",
            "version": "0.5.0",
        }
    )
    return client


app.router.lifespan_context = create_lifespan(
    database_factory=_mock_database_factory,
    opensearch_factory=_mock_opensearch_factory,
    embedding_factory=_mock_embedding_factory,
    llm_factory=_mock_llm_factory,
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
    return _mock_database_factory()


@pytest.fixture
def mock_opensearch():
    return _mock_opensearch_factory()


@pytest.fixture
def mock_embedding_client():
    return _mock_embedding_factory()


@pytest.fixture
def mock_llm_client():
    return _mock_llm_factory()


@pytest.fixture
def client(mock_settings, mock_database, mock_opensearch, mock_embedding_client, mock_llm_client):
    """Test client with mocked dependencies."""
    app.dependency_overrides[get_settings] = lambda: mock_settings
    app.dependency_overrides[get_database] = lambda: mock_database
    app.dependency_overrides[get_opensearch] = lambda: mock_opensearch
    app.dependency_overrides[get_embedding_client] = lambda: mock_embedding_client
    app.dependency_overrides[get_llm_client] = lambda: mock_llm_client

    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client

    app.dependency_overrides.clear()
