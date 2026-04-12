import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSON, UUID

from src.db.postgres import Base


class Article(Base):
    __tablename__ = "articles"
    __table_args__ = (UniqueConstraint("source", "source_id", name="uq_article_source"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source = Column(String, nullable=False, index=True)
    source_id = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    body_markdown = Column(Text, nullable=True)
    url = Column(String, nullable=False)
    published_at = Column(DateTime, nullable=False)
    reading_time_minutes = Column(Integer, nullable=True)
    tags = Column(JSON, nullable=False, default=list)
    author = Column(String, nullable=False)
    content_hash = Column(String, nullable=True, index=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
