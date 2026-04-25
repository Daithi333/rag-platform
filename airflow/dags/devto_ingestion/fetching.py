import asyncio

import structlog

from src.repositories.article import ArticleRepository
from src.schemas.devto.article import ArticleCreate
from src.services.devto.hashing import compute_content_hash

from .common import get_cached_services

logger = structlog.getLogger(__name__)

SOURCE = "devto"


def fetch_and_store_articles() -> dict:
    database, devto_client = get_cached_services()

    articles = asyncio.run(devto_client.fetch_all_articles())
    logger.info("Fetched articles from Dev.to", count=len(articles))

    counts = {"created": 0, "updated": 0, "unchanged": 0}

    with database.get_session() as session:
        repo = ArticleRepository(session)

        for i, article in enumerate(articles, 1):
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
                content_hash=compute_content_hash(article),
            )
            _, status = repo.upsert(data)
            counts[status] += 1

            if i % 50 == 0:
                logger.info(
                    "Upsert progress",
                    processed=i,
                    total=len(articles),
                    created=counts["created"],
                    updated=counts["updated"],
                    unchanged=counts["unchanged"],
                )

        logger.info(
            "Ingestion complete",
            total=len(articles),
            created=counts["created"],
            updated=counts["updated"],
            unchanged=counts["unchanged"],
        )
        return {**counts, "total": len(articles)}
