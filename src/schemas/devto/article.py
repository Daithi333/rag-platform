from datetime import datetime

from pydantic import BaseModel


class DevToArticle(BaseModel):
    """Schema for Dev.to API article response."""

    id: int
    title: str
    description: str | None = None
    body_markdown: str | None = None
    url: str
    published_at: datetime
    reading_time_minutes: int | None = None
    tags: list[str] = []
    user: dict


class ArticleCreate(BaseModel):
    """Schema for creating an article in the database."""

    source: str
    source_id: str
    title: str
    description: str | None = None
    body_markdown: str | None = None
    url: str
    published_at: datetime
    reading_time_minutes: int | None = None
    tags: list[str] = []
    author: str
