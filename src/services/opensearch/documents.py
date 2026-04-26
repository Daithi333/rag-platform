"""Build OpenSearch documents from domain models."""

import uuid

from src.models.article import Article


def build_chunk_doc(article: Article, chunk: dict) -> dict:
    """Map an Article + chunk dict to an OpenSearch chunk document."""
    return {
        "chunk_id": str(uuid.uuid4()),
        "article_id": str(article.id),
        "source_id": article.source_id,
        "chunk_index": chunk["chunk_index"],
        "chunk_text": chunk["chunk_text"],
        "chunk_word_count": chunk["chunk_word_count"],
        "title": article.title,
        "description": article.description or "",
        "author": article.author,
        "tags": article.tags or [],
        "url": article.url,
        "published_date": (article.published_at.isoformat() if article.published_at else None),
    }
