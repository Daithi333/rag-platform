import structlog
from functools import lru_cache
from typing import Tuple

from src.db.base import BaseDatabase
from src.db.factory import make_database
from src.services.devto.client import DevToClient
from src.services.devto.factory import make_devto_client

logger = structlog.getLogger(__name__)


@lru_cache(maxsize=1)
def get_cached_services() -> Tuple[BaseDatabase, DevToClient]:
    """Get cached services"""
    logger.info("Initializing services")

    database = make_database()
    devto = make_devto_client()

    logger.info("All services initialized and cached")
    return database, devto
