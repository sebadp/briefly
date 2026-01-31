"""Article schemas for API request/response validation."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class ArticleBase(BaseModel):
    """Base article schema with shared fields."""

    title: str = Field(..., min_length=1, max_length=500)
    summary: str = Field(..., min_length=1, max_length=2000)
    url: HttpUrl = Field(..., description="URL to the original article")
    source_url: HttpUrl = Field(..., description="URL of the source website")
    source_name: str = Field(..., min_length=1, max_length=100)


class ArticleResponse(ArticleBase):
    """Schema for article responses."""

    id: str  # DynamoDB uses string IDs
    feed_id: UUID
    published_at: datetime | None = None
    scraped_at: datetime
    thumbnail_url: HttpUrl | None = None

    class Config:
        from_attributes = True


class ArticleListResponse(BaseModel):
    """Schema for paginated article list response."""

    articles: list[ArticleResponse]
    total: int
    limit: int
    offset: int
