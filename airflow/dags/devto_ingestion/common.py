from dataclasses import dataclass
from functools import lru_cache

import structlog

from src.db.base import BaseDatabase
from src.db.factory import make_database
from src.services.devto.client import DevToClient
from src.services.devto.factory import make_devto_client
from src.services.embeddings.client import EmbeddingClient
from src.services.embeddings.factory import make_embedding_client
from src.services.opensearch.client import OpenSearchClient
from src.services.opensearch.factory import make_opensearch_client

logger = structlog.getLogger(__name__)


@dataclass(frozen=True)
class Services:
    database: BaseDatabase
    devto: DevToClient
    opensearch: OpenSearchClient
    embeddings: EmbeddingClient


@lru_cache(maxsize=1)
def get_cached_services() -> Services:
    """Get cached services."""
    logger.info("Initializing services")

    services = Services(
        database=make_database(),
        devto=make_devto_client(),
        opensearch=make_opensearch_client(),
        embeddings=make_embedding_client(),
    )

    logger.info("All services initialized and cached")
    return services
