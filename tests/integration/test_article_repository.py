from datetime import datetime, timezone

from sqlalchemy.orm import Session

from src.repositories.article import ArticleRepository
from src.schemas.devto.article import ArticleCreate


def _make_article_data(
    source_id: str = "100",
    title: str = "Test Article",
    **overrides,
) -> ArticleCreate:
    defaults = {
        "source": "devto",
        "source_id": source_id,
        "title": title,
        "description": "A test article",
        "body_markdown": "# Hello",
        "url": f"https://dev.to/test/article-{source_id}",
        "published_at": datetime(2026, 1, 15, tzinfo=timezone.utc),
        "edited_at": datetime(2026, 1, 15, tzinfo=timezone.utc),
        "reading_time_minutes": 5,
        "tags": ["python", "testing"],
        "author": "Test Author",
    }
    defaults.update(overrides)
    return ArticleCreate(**defaults)


class TestArticleCreate:
    def test_create_returns_article(self, session: Session):
        repo = ArticleRepository(session)
        data = _make_article_data()

        article = repo.create(data)

        assert article.id is not None
        assert article.title == "Test Article"
        assert article.source == "devto"
        assert article.source_id == "100"
        assert article.author == "Test Author"
        assert article.created_at is not None


class TestArticleGetById:
    def test_found(self, session: Session):
        repo = ArticleRepository(session)
        created = repo.create(_make_article_data())

        found = repo.get_by_id(created.id)

        assert found is not None
        assert found.id == created.id

    def test_not_found(self, session: Session):
        import uuid

        repo = ArticleRepository(session)

        assert repo.get_by_id(uuid.uuid4()) is None


class TestArticleGetBySourceId:
    def test_found(self, session: Session):
        repo = ArticleRepository(session)
        repo.create(_make_article_data(source_id="200"))

        found = repo.get_by_source_id("devto", "200")

        assert found is not None
        assert found.source_id == "200"

    def test_not_found(self, session: Session):
        repo = ArticleRepository(session)

        assert repo.get_by_source_id("devto", "nonexistent") is None

    def test_different_source_not_found(self, session: Session):
        repo = ArticleRepository(session)
        repo.create(_make_article_data(source_id="300"))

        assert repo.get_by_source_id("stackoverflow", "300") is None


class TestArticleUpsert:
    def test_creates_new_article(self, session: Session):
        repo = ArticleRepository(session)
        data = _make_article_data(source_id="400")

        article, status = repo.upsert(data)

        assert status == "created"
        assert article.source_id == "400"

    def test_unchanged_when_edited_at_same(self, session: Session):
        repo = ArticleRepository(session)
        edited = datetime(2026, 2, 1, tzinfo=timezone.utc)
        data = _make_article_data(source_id="500", edited_at=edited)
        repo.create(data)

        article, status = repo.upsert(data)

        assert status == "unchanged"

    def test_unchanged_when_edited_at_older(self, session: Session):
        repo = ArticleRepository(session)
        repo.create(
            _make_article_data(source_id="501", edited_at=datetime(2026, 2, 1, tzinfo=timezone.utc))
        )

        older = _make_article_data(
            source_id="501", edited_at=datetime(2026, 1, 1, tzinfo=timezone.utc)
        )
        _, status = repo.upsert(older)

        assert status == "unchanged"

    def test_updated_when_edited_at_newer(self, session: Session):
        repo = ArticleRepository(session)
        repo.create(
            _make_article_data(
                source_id="600",
                edited_at=datetime(2026, 1, 1),
                title="Original",
            )
        )

        updated_data = _make_article_data(
            source_id="600",
            edited_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
            title="Updated",
        )
        article, status = repo.upsert(updated_data)

        assert status == "updated"
        assert article.title == "Updated"

    def test_unchanged_when_both_edited_at_null(self, session: Session):
        repo = ArticleRepository(session)
        data = _make_article_data(source_id="698", edited_at=None)
        repo.create(data)

        _, status = repo.upsert(data)

        assert status == "unchanged"

    def test_unchanged_backfills_edited_at(self, session: Session):
        repo = ArticleRepository(session)
        repo.create(_make_article_data(source_id="700", edited_at=None))

        backfill_data = _make_article_data(
            source_id="700", edited_at=datetime(2026, 1, 1, tzinfo=timezone.utc)
        )
        article, status = repo.upsert(backfill_data)

        assert status == "unchanged"
        assert article.edited_at == datetime(2026, 1, 1, tzinfo=timezone.utc)

    def test_unchanged_when_incoming_has_no_edited_at(self, session: Session):
        repo = ArticleRepository(session)
        repo.create(
            _make_article_data(source_id="701", edited_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
        )

        data = _make_article_data(source_id="701", edited_at=None)
        _, status = repo.upsert(data)

        assert status == "unchanged"


class TestArticleUpdate:
    def test_update_persists_changes(self, session: Session):
        repo = ArticleRepository(session)
        article = repo.create(_make_article_data(source_id="800"))

        article.title = "Updated Title"
        updated = repo.update(article)

        assert updated.title == "Updated Title"
        assert repo.get_by_id(article.id).title == "Updated Title"


class TestArticleDelete:
    def test_delete_existing(self, session: Session):
        repo = ArticleRepository(session)
        article = repo.create(_make_article_data(source_id="900"))

        assert repo.delete(article.id) is True
        assert repo.get_by_id(article.id) is None

    def test_delete_nonexistent(self, session: Session):
        import uuid

        repo = ArticleRepository(session)

        assert repo.delete(uuid.uuid4()) is False


class TestArticleList:
    def test_list_returns_ordered_by_published_at(self, session: Session):
        repo = ArticleRepository(session)
        repo.create(
            _make_article_data(
                source_id="1001",
                published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            )
        )
        repo.create(
            _make_article_data(
                source_id="1002",
                published_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
            )
        )
        repo.create(
            _make_article_data(
                source_id="1003",
                published_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
            )
        )

        articles = repo.list(limit=10)

        assert [a.source_id for a in articles] == ["1002", "1003", "1001"]

    def test_list_respects_limit_and_offset(self, session: Session):
        repo = ArticleRepository(session)
        for i in range(5):
            repo.create(
                _make_article_data(
                    source_id=f"110{i}",
                    published_at=datetime(2026, 1, i + 1, tzinfo=timezone.utc),
                )
            )

        page = repo.list(limit=2, offset=1)

        assert len(page) == 2


class TestArticleGetBySource:
    def test_filters_by_source(self, session: Session):
        repo = ArticleRepository(session)
        repo.create(_make_article_data(source_id="1200", source="devto"))
        repo.create(_make_article_data(source_id="1201", source="stackoverflow"))

        devto_articles = repo.get_by_source("devto")

        assert all(a.source == "devto" for a in devto_articles)


class TestArticleGetCount:
    def test_count_all(self, session: Session):
        repo = ArticleRepository(session)
        repo.create(_make_article_data(source_id="1300"))
        repo.create(_make_article_data(source_id="1301"))

        assert repo.get_count() == 2

    def test_count_by_source(self, session: Session):
        repo = ArticleRepository(session)
        repo.create(_make_article_data(source_id="1400", source="devto"))
        repo.create(_make_article_data(source_id="1401", source="stackoverflow"))

        assert repo.get_count(source="devto") == 1
        assert repo.get_count(source="stackoverflow") == 1
