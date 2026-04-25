from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.schemas.devto.article import ArticleCreate


def _defaults(**overrides) -> dict:
    base = {
        "source": "devto",
        "source_id": "123",
        "title": "Test Article",
        "description": "A description",
        "body_markdown": "# Content",
        "url": "https://dev.to/test/article",
        "published_at": datetime(2026, 1, 15, tzinfo=timezone.utc),
        "reading_time_minutes": 5,
        "tags": ["python"],
        "author": "Test Author",
        "content_hash": "abc123",
    }
    base.update(overrides)
    return base


class TestArticleCreate:
    def test_valid_article(self):
        article = ArticleCreate(**_defaults())

        assert article.source == "devto"
        assert article.source_id == "123"
        assert article.tags == ["python"]

    def test_optional_fields_default_none(self):
        article = ArticleCreate(
            **_defaults(
                description=None,
                body_markdown=None,
                reading_time_minutes=None,
                content_hash=None,
            )
        )

        assert article.description is None
        assert article.body_markdown is None
        assert article.reading_time_minutes is None
        assert article.content_hash is None

    def test_tags_default_empty_list(self):
        data = _defaults()
        del data["tags"]
        article = ArticleCreate(**data)

        assert article.tags == []

    def test_missing_required_source_raises(self):
        data = _defaults()
        del data["source"]

        with pytest.raises(ValidationError) as exc_info:
            ArticleCreate(**data)

        assert "source" in str(exc_info.value)

    def test_missing_required_title_raises(self):
        data = _defaults()
        del data["title"]

        with pytest.raises(ValidationError) as exc_info:
            ArticleCreate(**data)

        assert "title" in str(exc_info.value)

    def test_missing_required_url_raises(self):
        data = _defaults()
        del data["url"]

        with pytest.raises(ValidationError) as exc_info:
            ArticleCreate(**data)

        assert "url" in str(exc_info.value)
