import structlog
from airflow.sdk import get_current_context
from sqlalchemy import func

from src.models.article import Article

from .common import get_cached_services

logger = structlog.getLogger(__name__)


def generate_daily_report() -> dict:
    """Collect ingestion metrics from XCom and database for observability."""
    context = get_current_context()
    ti = context["ti"]

    fetch_stats = ti.xcom_pull(task_ids="fetch_and_store_articles") or {}

    database, _ = get_cached_services()

    db_stats = {}
    with database.get_session() as session:
        db_stats["total_articles"] = session.query(func.count(Article.id)).scalar() or 0
        db_stats["total_devto"] = (
            session.query(func.count(Article.id)).filter(Article.source == "devto").scalar() or 0
        )

    report = {
        "fetch": {
            "total_fetched": fetch_stats.get("total", 0),
            "created": fetch_stats.get("created", 0),
            "updated": fetch_stats.get("updated", 0),
            "unchanged": fetch_stats.get("unchanged", 0),
        },
        "database": db_stats,
        "status": "success" if fetch_stats else "no_fetch_data",
    }

    logger.info("Daily ingestion report", **report)
    return report
