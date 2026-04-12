from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, field_validator, BeforeValidator


def parse_tags(v: str | list[str]) -> list[str]:
    if isinstance(v, str):
        return [t.strip() for t in v.split(",") if t.strip()]
    return v or []


Tags = Annotated[list[str], BeforeValidator(parse_tags)]


class DevToArticle(BaseModel):
    """Schema for Dev.to API article response."""

    id: int
    title: str
    description: str | None = None
    body_markdown: str | None = None
    url: str
    published_at: datetime
    reading_time_minutes: int | None = None
    tags: Tags = []
    user: dict

    @field_validator("tags", mode="before")
    @classmethod
    def parse_tags(cls, v):
        if isinstance(v, str):
            return [t.strip() for t in v.split(",") if t.strip()]
        return v or []


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
    content_hash: str | None = None
