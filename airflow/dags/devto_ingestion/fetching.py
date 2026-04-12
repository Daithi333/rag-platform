import asyncio
import hashlib
import json
import logging

from src.repositories.article import ArticleRepository
from src.schemas.devto.article import ArticleCreate

from .common import get_cached_services

logger = logging.getLogger(__name__)

SOURCE = "devto"


def _compute_content_hash(article) -> str:
    content = json.dumps(
        {
            "title": article.title,
            "description": article.description,
            "body_markdown": article.body_markdown,
            "tags": sorted(article.tags),
        },
        sort_keys=True,
    )
    return hashlib.sha256(content.encode()).hexdigest()


def fetch_and_store_articles() -> dict:
    devto_client, database = get_cached_services()

    articles = asyncio.run(devto_client.fetch_all_articles())
    logger.info(f"Fetched {len(articles)} articles from Dev.to")

    counts = {"created": 0, "updated": 0, "unchanged": 0}

    with database.get_session() as session:
        repo = ArticleRepository(session)

        for article in articles:
            data = ArticleCreate(
                source=SOURCE,
                source_id=str(article.id),
                title=article.title,
                description=article.description,
                body_markdown=article.body_markdown,
                url=article.url,
                published_at=article.published_at,
                reading_time_minutes=article.reading_time_minutes,
                tags=article.tags,
                author=article.user.get("name", "unknown"),
                content_hash=_compute_content_hash(article),
            )
            _, status = repo.upsert(data)
            counts[status] += 1

        logger.info(
            f"Articles: {counts['created']} created, {counts['updated']} updated, {counts['unchanged']} unchanged"
        )
        return {**counts, "total": len(articles)}
