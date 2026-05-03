from typing import Literal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.db.base import BaseRepository
from src.models.article import Article
from src.schemas.devto.article import ArticleCreate


class ArticleRepository(BaseRepository[Article, ArticleCreate]):
    def __init__(self, session: Session):
        super().__init__(session)

    def create(self, data: ArticleCreate) -> Article:
        db_article = Article(**data.model_dump())
        self.session.add(db_article)
        self.session.commit()
        self.session.refresh(db_article)
        return db_article

    def get_by_id(self, record_id: UUID) -> Article | None:
        return self.session.scalar(select(Article).where(Article.id == record_id))

    def get_by_source_id(self, source: str, source_id: str) -> Article | None:
        return self.session.scalar(
            select(Article).where(Article.source == source, Article.source_id == source_id)
        )

    def get_by_source(self, source: str, limit: int = 100, offset: int = 0) -> list[Article]:
        stmt = (
            select(Article)
            .where(Article.source == source)
            .order_by(Article.published_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(stmt))

    def update(self, record: Article) -> Article:
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def delete(self, record_id: UUID) -> bool:
        article = self.get_by_id(record_id)
        if not article:
            return False
        self.session.delete(article)
        self.session.commit()
        return True

    def list(self, limit: int = 100, offset: int = 0) -> list[Article]:
        stmt = select(Article).order_by(Article.published_at.desc()).limit(limit).offset(offset)
        return list(self.session.scalars(stmt))

    def get_count(self, source: str | None = None) -> int:
        stmt = select(func.count(Article.id))
        if source:
            stmt = stmt.where(Article.source == source)
        return self.session.scalar(stmt) or 0

    def upsert(
        self, data: ArticleCreate
    ) -> tuple[Article, Literal["created", "updated", "unchanged"]]:
        existing = self.get_by_source_id(data.source, data.source_id)
        if not existing:
            return self.create(data), "created"

        # Both null or both equal: no change detected
        if existing.edited_at == data.edited_at:
            return existing, "unchanged"

        # Backfill: existing has no timestamp, incoming does
        if not existing.edited_at and data.edited_at:
            existing.edited_at = data.edited_at
            self.update(existing)
            return existing, "unchanged"

        # Existing has timestamp, incoming doesn't: no change signal
        if existing.edited_at and not data.edited_at:
            return existing, "unchanged"

        # Both have timestamps: only update if incoming is newer
        if existing.edited_at >= data.edited_at:
            return existing, "unchanged"

        for key, value in data.model_dump().items():
            setattr(existing, key, value)
        return self.update(existing), "updated"
