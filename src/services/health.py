import structlog
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.schemas.api.health import ServiceStatus
from src.services.opensearch.client import OpenSearchClient

logger = structlog.getLogger(__name__)


def check_database(session: Session) -> ServiceStatus:
    """Check database connectivity."""
    try:
        session.execute(text("SELECT 1"))
        return ServiceStatus(status="healthy", message=None)
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        return ServiceStatus(status="unhealthy", message=str(e))


def check_opensearch(client: OpenSearchClient) -> ServiceStatus:
    """Check OpenSearch cluster health."""
    result = client.health_check()
    if result["healthy"]:
        return ServiceStatus(status="healthy", message=f"cluster: {result['status']}")
    if result.get("error"):
        return ServiceStatus(status="unhealthy", message=result["error"])
    return ServiceStatus(status="degraded", message=f"cluster: {result['status']}")
