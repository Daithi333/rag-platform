from unittest.mock import MagicMock

from src.services.devto.hashing import compute_content_hash


class TestComputeContentHash:
    def _make_article(self, **overrides) -> MagicMock:
        defaults = {
            "title": "Test Article",
            "description": "A description",
            "body_markdown": "# Content",
            "tags": ["python", "testing"],
        }
        defaults.update(overrides)
        return MagicMock(**defaults)

    def test_deterministic(self):
        article = self._make_article()

        assert compute_content_hash(article) == compute_content_hash(article)

    def test_same_input_same_hash(self):
        a = self._make_article()
        b = self._make_article()

        assert compute_content_hash(a) == compute_content_hash(b)

    def test_different_title_different_hash(self):
        a = self._make_article(title="Title A")
        b = self._make_article(title="Title B")

        assert compute_content_hash(a) != compute_content_hash(b)

    def test_different_body_different_hash(self):
        a = self._make_article(body_markdown="# Version 1")
        b = self._make_article(body_markdown="# Version 2")

        assert compute_content_hash(a) != compute_content_hash(b)

    def test_tag_order_does_not_matter(self):
        a = self._make_article(tags=["python", "testing"])
        b = self._make_article(tags=["testing", "python"])

        assert compute_content_hash(a) == compute_content_hash(b)
