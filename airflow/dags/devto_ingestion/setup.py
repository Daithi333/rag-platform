import asyncio

import structlog
from sqlalchemy import text

from .common import get_cached_services

logger = structlog.getLogger(__name__)


def setup_environment() -> dict:
    """Setup environment and verify dependencies."""
    logger.info("Setting up environment for Dev.to article ingestion")

    try:
        database, devto_client = get_cached_services()

        with database.get_session() as session:
            session.execute(text("SELECT 1"))
            logger.info("Database connection verified")

        devto_health = asyncio.run(devto_client.health_check())
        logger.info("Dev.to client ready", authenticated=devto_health["authenticated"])

        return {"status": "success", "message": "Environment setup completed"}

    except Exception as e:
        logger.error("Environment setup failed", error=str(e))
        raise
