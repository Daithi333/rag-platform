"""Index articles from Postgres into OpenSearch as chunks with embeddings."""

import asyncio

import structlog
from datetime import datetime
from sqlalchemy import select

from airflow.sdk import get_current_context

from src.config import get_settings
from src.models.article import Article
from src.services.chunking import chunk_text
from src.services.embeddings.factory import make_embedding_client
from src.services.opensearch.documents import build_chunk_doc
from src.services.opensearch.factory import make_opensearch_client
from src.services.opensearch.index_config import (
    DEVTO_CHUNKS_MAPPING,
    HYBRID_RRF_PIPELINE,
    get_chunk_index_name,
)

from .common import get_cached_services

logger = structlog.getLogger(__name__)

BATCH_SIZE = 50


def setup_opensearch_index() -> dict:
    """Create the chunk index and RRF pipeline if they don't exist."""
    settings = get_settings()
    os_client = make_opensearch_client()
    index_name = get_chunk_index_name(settings.opensearch)

    index_created = os_client.create_index(index_name, DEVTO_CHUNKS_MAPPING)
    pipeline_created = os_client.create_search_pipeline(
        settings.opensearch.rrf_pipeline_name, HYBRID_RRF_PIPELINE
    )

    return {
        "index_name": index_name,
        "index_created": index_created,
        "pipeline_created": pipeline_created,
    }


def index_articles() -> dict:
    """Index changed articles (from XCom) into OpenSearch as chunks."""
    context = get_current_context()
    ti = context["ti"]
    fetch_stats = ti.xcom_pull(task_ids="fetch_and_store_articles") or {}
    article_ids = fetch_stats.get("changed_article_ids", [])

    if not article_ids:
        logger.info("No changed articles to index")
        return {"articles_processed": 0, "chunks_indexed": 0, "errors": 0}

    settings = get_settings()
    database, _ = get_cached_services()
    os_client = make_opensearch_client()
    index_name = get_chunk_index_name(settings.opensearch)

    counts = {"articles_processed": 0, "chunks_indexed": 0, "errors": 0}

    with database.get_session() as session:
        articles = list(session.scalars(select(Article).where(Article.id.in_(article_ids))))

    logger.info("Starting indexing", total_articles=len(articles))

    asyncio.run(_index_article_batch(articles, os_client, index_name, settings, counts))

    logger.info("Indexing complete", **counts)
    return counts


def index_articles_by_date(
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """Index articles with bodies. Deletes old chunks before re-indexing."""
    settings = get_settings()
    database, _ = get_cached_services()
    os_client = make_opensearch_client()
    index_name = get_chunk_index_name(settings.opensearch)

    counts = {"articles_processed": 0, "chunks_indexed": 0, "errors": 0}

    stmt = select(Article).where(
        Article.source == "devto",
        Article.body_markdown.isnot(None),
    )

    if start_date:
        stmt = stmt.where(Article.created_at >= datetime.fromisoformat(start_date))

    if end_date:
        stmt = stmt.where(Article.created_at <= datetime.fromisoformat(end_date))

    with database.get_session() as session:
        articles = list(session.scalars(stmt))

    logger.info("Starting backfill indexing", total_articles=len(articles))

    asyncio.run(_index_article_batch(articles, os_client, index_name, settings, counts))

    logger.info("Backfill indexing complete", **counts)
    return counts


async def _index_article_batch(articles, os_client, index_name, settings, counts) -> None:
    """Chunk, embed, and index a list of articles."""
    embedding_client = make_embedding_client()
    has_api_key = bool(settings.jina.api_key and settings.jina.api_key != "your_jina_api_key_here")

    for i in range(0, len(articles), BATCH_SIZE):
        batch = articles[i : i + BATCH_SIZE]
        chunk_texts: list[str] = []
        chunk_article_map: list[tuple[Article, dict]] = []

        for article in batch:
            os_client.delete_by_query(index_name, {"term": {"article_id": str(article.id)}})

            content = article.body_markdown or article.description or ""
            chunks = chunk_text(content, settings.chunking)

            if not chunks:
                continue

            for chunk in chunks:
                chunk_texts.append(chunk["chunk_text"])
                chunk_article_map.append((article, chunk))

            counts["articles_processed"] += 1

        if not chunk_texts:
            continue

        embeddings: list[list[float]] | None = None
        if has_api_key:
            try:
                embeddings = await embedding_client.embed_texts(chunk_texts)
            except Exception as e:
                logger.error("Embedding generation failed, indexing without vectors", error=str(e))

        docs = []
        for idx, (article, chunk) in enumerate(chunk_article_map):
            embedding = embeddings[idx] if embeddings else None
            docs.append(build_chunk_doc(article, chunk, embedding=embedding))

        try:
            result = os_client.bulk_index(index_name, docs)
            counts["chunks_indexed"] += result["success"]
            counts["errors"] += result["failed"]
        except Exception as e:
            logger.error("Bulk index batch failed", error=str(e))
            counts["errors"] += len(docs)

        if (i + BATCH_SIZE) % 200 == 0:
            logger.info("Indexing progress", **counts)
