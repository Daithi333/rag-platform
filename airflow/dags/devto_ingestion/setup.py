import asyncio
import logging

from sqlalchemy import text

from .common import get_cached_services

logger = logging.getLogger(__name__)


def setup_environment():
    """Setup environment and verify dependencies."""
    logger.info("Setting up environment for Dev.To article ingestion")

    try:
        database, devto_client = get_cached_services()

        with database.get_session() as session:
            session.execute(text("SELECT 1"))
            logger.info("Database connection verified")

        devto_health = asyncio.run(devto_client.health_check())
        logger.info(f"Dev.To client ready (authenticated: {devto_health['authenticated']})")

        return {"status": "success", "message": "Environment setup completed"}

    except Exception as e:
        error_msg = f"Environment setup failed: {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg)
