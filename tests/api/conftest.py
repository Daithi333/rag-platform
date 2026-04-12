import logging

import pytest
from fastapi.testclient import TestClient

from src.config import Settings
from src.dependencies import get_settings
from src.main import app


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Configure test environment."""
    # Disable logging
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
        # Add other required settings with defaults
    )


@pytest.fixture
def client(mock_settings):
    """Test client with mocked dependencies."""
    app.dependency_overrides[get_settings] = lambda: mock_settings

    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
