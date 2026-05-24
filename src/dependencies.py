from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Request

from src.config import Settings
from src.db.base import BaseDatabase
from src.services.cache.client import CacheClient
from src.services.embeddings.client import EmbeddingClient
from src.services.llm.base import BaseLLMClient
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


def get_embedding_client(request: Request) -> EmbeddingClient:
    """Get embedding client from app state."""
    return request.app.state.embedding_client


def get_llm_client(request: Request) -> BaseLLMClient:
    """Get LLM client from app state."""
    return request.app.state.llm_client


def get_cache(request: Request) -> CacheClient | None:
    """Get cache client from app state. May be None if Redis is unavailable."""
    return getattr(request.app.state, "cache", None)


# Dependency annotations
SettingsDep = Annotated[Settings, Depends(get_settings)]
DatabaseDep = Annotated[BaseDatabase, Depends(get_database)]
OpenSearchDep = Annotated[OpenSearchClient, Depends(get_opensearch)]
EmbeddingDep = Annotated[EmbeddingClient, Depends(get_embedding_client)]
LLMDep = Annotated[BaseLLMClient, Depends(get_llm_client)]
CacheDep = Annotated[CacheClient | None, Depends(get_cache)]
