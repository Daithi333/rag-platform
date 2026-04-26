import asyncio

import structlog

from src.repositories.article import ArticleRepository
from src.schemas.devto.article import ArticleCreate, DevToArticle
from src.services.devto.hashing import compute_content_hash

from .common import get_cached_services

logger = structlog.getLogger(__name__)

SOURCE = "devto"


def _to_article_create(article: DevToArticle) -> ArticleCreate:
    return ArticleCreate(
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


def _upsert_page(
    repo: ArticleRepository,
    articles: list[DevToArticle],
    seen_ids: set[int],
    counts: dict[str, int],
    changed_ids: list[str],
) -> None:
    for article in articles:
        if article.id in seen_ids:
            continue
        seen_ids.add(article.id)

        data = _to_article_create(article)
        record, status = repo.upsert(data)
        counts[status] += 1

        if status in ("created", "updated"):
            changed_ids.append(str(record.id))


async def _fetch_and_persist(database, devto_client) -> dict:
    tags = devto_client._settings.tags
    counts = {"created": 0, "updated": 0, "unchanged": 0}
    changed_ids: list[str] = []
    seen_ids: set[int] = set()
    total_pages = 0

    with database.get_session() as session:
        repo = ArticleRepository(session)

        for tag in tags:
            async for page_articles in devto_client.fetch_articles_by_tag(tag):
                _upsert_page(repo, page_articles, seen_ids, counts, changed_ids)
                total_pages += 1

                if len(seen_ids) % 50 < len(page_articles):
                    logger.info(
                        "Ingestion progress",
                        total_seen=len(seen_ids),
                        created=counts["created"],
                        updated=counts["updated"],
                        unchanged=counts["unchanged"],
                    )

    logger.info(
        "Ingestion complete",
        total=len(seen_ids),
        pages=total_pages,
        created=counts["created"],
        updated=counts["updated"],
        unchanged=counts["unchanged"],
        changed=len(changed_ids),
    )
    return {**counts, "total": len(seen_ids), "changed_article_ids": changed_ids}


def fetch_and_store_articles() -> dict:
    database, devto_client = get_cached_services()
    return asyncio.run(_fetch_and_persist(database, devto_client))
