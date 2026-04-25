import hashlib
import json

from src.schemas.devto.article import DevToArticle


def compute_content_hash(article: DevToArticle) -> str:
    """Compute a deterministic hash of the content fields that affect search/retrieval."""
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
