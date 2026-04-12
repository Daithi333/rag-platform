import pytest
from pydantic import ValidationError
from src.schemas.devto.article import DevToArticle


class TestDevToArticle:
    def test_tags_from_comma_separated_string(self):
        article = DevToArticle(
            id=1,
            title="Test",
            url="https://dev.to/test",
            published_at="2026-01-01T00:00:00Z",
            user={"name": "Author"},
            tags="python, webdev, testing",
        )
        assert article.tags == ["python", "webdev", "testing"]

    def test_tags_from_list(self):
        article = DevToArticle(
            id=1,
            title="Test",
            url="https://dev.to/test",
            published_at="2026-01-01T00:00:00Z",
            user={"name": "Author"},
            tags=["python", "webdev"],
        )
        assert article.tags == ["python", "webdev"]

    def test_tags_from_empty_string(self):
        article = DevToArticle(
            id=1,
            title="Test",
            url="https://dev.to/test",
            published_at="2026-01-01T00:00:00Z",
            user={"name": "Author"},
            tags="",
        )
        assert article.tags == []

    def test_tags_default_empty_list(self):
        article = DevToArticle(
            id=1,
            title="Test",
            url="https://dev.to/test",
            published_at="2026-01-01T00:00:00Z",
            user={"name": "Author"},
        )
        assert article.tags == []

    def test_tags_strips_whitespace(self):
        article = DevToArticle(
            id=1,
            title="Test",
            url="https://dev.to/test",
            published_at="2026-01-01T00:00:00Z",
            user={"name": "Author"},
            tags="  python ,  webdev  , testing  ",
        )
        assert article.tags == ["python", "webdev", "testing"]

    def test_missing_required_fields(self):
        with pytest.raises(ValidationError):
            DevToArticle(title="Test")

    def test_optional_fields_default_none(self):
        article = DevToArticle(
            id=1,
            title="Test",
            url="https://dev.to/test",
            published_at="2026-01-01T00:00:00Z",
            user={"name": "Author"},
        )
        assert article.description is None
        assert article.body_markdown is None
        assert article.reading_time_minutes is None
