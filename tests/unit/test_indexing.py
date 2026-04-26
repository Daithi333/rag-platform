from datetime import datetime, timezone
from unittest.mock import MagicMock

from src.services.opensearch.documents import build_chunk_doc


class TestBuildChunkDoc:
    def _make_article(self, **overrides):
        defaults = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "source_id": "12345",
            "title": "Test Article",
            "description": "A test description",
            "author": "Test Author",
            "tags": ["python", "testing"],
            "url": "https://dev.to/test/article",
            "published_at": datetime(2026, 1, 15, tzinfo=timezone.utc),
        }
        defaults.update(overrides)
        return MagicMock(**defaults)

    def test_maps_article_fields(self):
        article = self._make_article()
        chunk = {"chunk_text": "some content", "chunk_index": 0, "chunk_word_count": 2}

        doc = build_chunk_doc(article, chunk)

        assert doc["article_id"] == str(article.id)
        assert doc["source_id"] == "12345"
        assert doc["title"] == "Test Article"
        assert doc["author"] == "Test Author"
        assert doc["tags"] == ["python", "testing"]
        assert doc["url"] == "https://dev.to/test/article"

    def test_maps_chunk_fields(self):
        article = self._make_article()
        chunk = {"chunk_text": "hello world", "chunk_index": 2, "chunk_word_count": 2}

        doc = build_chunk_doc(article, chunk)

        assert doc["chunk_text"] == "hello world"
        assert doc["chunk_index"] == 2
        assert doc["chunk_word_count"] == 2

    def test_generates_unique_chunk_id(self):
        article = self._make_article()
        chunk = {"chunk_text": "text", "chunk_index": 0, "chunk_word_count": 1}

        doc1 = build_chunk_doc(article, chunk)
        doc2 = build_chunk_doc(article, chunk)

        assert doc1["chunk_id"] != doc2["chunk_id"]

    def test_handles_none_description(self):
        article = self._make_article(description=None)
        chunk = {"chunk_text": "text", "chunk_index": 0, "chunk_word_count": 1}

        doc = build_chunk_doc(article, chunk)

        assert doc["description"] == ""

    def test_handles_none_tags(self):
        article = self._make_article(tags=None)
        chunk = {"chunk_text": "text", "chunk_index": 0, "chunk_word_count": 1}

        doc = build_chunk_doc(article, chunk)

        assert doc["tags"] == []

    def test_published_date_iso_format(self):
        article = self._make_article()
        chunk = {"chunk_text": "text", "chunk_index": 0, "chunk_word_count": 1}

        doc = build_chunk_doc(article, chunk)

        assert doc["published_date"] == "2026-01-15T00:00:00+00:00"
