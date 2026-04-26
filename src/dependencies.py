from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Request

from src.config import Settings
from src.db.base import BaseDatabase
from src.services.opensearch.client import OpenSearchClient


@lru_cache
def get_settings() -> Settings:
    """Get application settings."""
    return Settings()


def get_database(request: Request) -> BaseDatabase:
    """Get database from app state."""
    return request.app.state.database


def get_opensearch(request: Request) -> OpenSearchClient:
    """Get OpenSearch client from app state."""
    return request.app.state.opensearch


# Dependency annotations
SettingsDep = Annotated[Settings, Depends(get_settings)]
DatabaseDep = Annotated[BaseDatabase, Depends(get_database)]
OpenSearchDep = Annotated[OpenSearchClient, Depends(get_opensearch)]
