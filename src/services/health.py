import structlog
from opensearchpy import OpenSearch
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.schemas.api.health import ServiceStatus

logger = structlog.getLogger(__name__)


def check_database(session: Session) -> ServiceStatus:
    """Check database connectivity."""
    try:
        session.execute(text("SELECT 1"))
        return ServiceStatus(status="healthy", message=None)
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        return ServiceStatus(status="unhealthy", message=str(e))


def check_opensearch(client: OpenSearch) -> ServiceStatus:
    """Check OpenSearch cluster health."""
    try:
        health = client.cluster.health()
        cluster_status = health.get("status", "unknown")
        if cluster_status in ("green", "yellow"):
            return ServiceStatus(status="healthy", message=f"cluster: {cluster_status}")
        return ServiceStatus(status="degraded", message=f"cluster: {cluster_status}")
    except Exception as e:
        logger.error("OpenSearch health check failed", error=str(e))
        return ServiceStatus(status="unhealthy", message=str(e))
