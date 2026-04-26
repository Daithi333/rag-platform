"""Fetch full article bodies from the Dev.to single-article endpoint."""

import asyncio
from datetime import datetime

import structlog
from sqlalchemy import select

from src.models.article import Article
from src.repositories.article import ArticleRepository

from .common import get_cached_services

logger = structlog.getLogger(__name__)


async def _fetch_bodies(database, devto_client, articles: list[Article]) -> dict:
    """Fetch body_markdown for a list of articles and update Postgres."""
    counts = {"fetched": 0, "skipped": 0, "errors": 0}

    with database.get_session() as session:
        repo = ArticleRepository(session)

        for i, article in enumerate(articles):
            if article.body_markdown:
                counts["skipped"] += 1
                continue

            try:
                body = await devto_client.fetch_article_body(int(article.source_id))

                if body:
                    article.body_markdown = body
                    repo.update(article)
                    counts["fetched"] += 1
                else:
                    counts["skipped"] += 1

            except Exception as e:
                logger.warning(
                    "Failed to fetch body, continuing",
                    source_id=article.source_id,
                    error=str(e),
                )
                counts["errors"] += 1

            await asyncio.sleep(devto_client._settings.rate_limit_delay)

            if (i + 1) % 50 == 0:
                logger.info("Body fetch progress", processed=i + 1, **counts)

    logger.info("Body fetch complete", total=len(articles), **counts)
    return counts


def fetch_bodies_for_changed() -> dict:
    """Fetch bodies for articles created/updated in the current DAG run."""
    from airflow.sdk import get_current_context

    context = get_current_context()
    ti = context["ti"]
    fetch_stats = ti.xcom_pull(task_ids="fetch_and_store_articles") or {}
    article_ids = fetch_stats.get("changed_article_ids", [])

    if not article_ids:
        logger.info("No changed articles to fetch bodies for")
        return {"fetched": 0, "skipped": 0, "errors": 0}

    database, devto_client = get_cached_services()

    with database.get_session() as session:
        articles = list(session.scalars(select(Article).where(Article.id.in_(article_ids))))

    logger.info("Fetching bodies for changed articles", count=len(articles))
    return asyncio.run(_fetch_bodies(database, devto_client, articles))


def fetch_bodies_by_date(
    start_date: str | None = None,
    end_date: str | None = None,
    only_missing: bool = True,
) -> dict:
    """Fetch bodies for articles, optionally filtered by date and/or missing body."""
    database, devto_client = get_cached_services()

    stmt = select(Article).where(Article.source == "devto")

    if only_missing:
        stmt = stmt.where(Article.body_markdown.is_(None))

    if start_date:
        stmt = stmt.where(Article.created_at >= datetime.fromisoformat(start_date))

    if end_date:
        stmt = stmt.where(Article.created_at <= datetime.fromisoformat(end_date))

    with database.get_session() as session:
        articles = list(session.scalars(stmt))

    logger.info(
        "Backfill body fetch",
        total=len(articles),
        only_missing=only_missing,
    )
    return asyncio.run(_fetch_bodies(database, devto_client, articles))
