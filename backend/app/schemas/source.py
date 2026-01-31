"""Source schemas for API request/response validation."""

from datetime import datetime
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field, HttpUrl


class SourceType(str, Enum):
    """Type of news source."""

    WEBSITE = "website"
    RSS = "rss"
    ATOM = "atom"


class SourceBase(BaseModel):
    """Base source schema with shared fields."""

    url: HttpUrl = Field(..., description="URL of the news source")
    name: str = Field(..., min_length=1, max_length=100)
    source_type: SourceType = Field(default=SourceType.WEBSITE)


class SourceCreate(SourceBase):
    """Schema for creating a source."""

    feed_id: UUID = Field(..., description="ID of the feed this source belongs to")


class SourceResponse(SourceBase):
    """Schema for source responses."""

    id: UUID
    feed_id: UUID
    created_at: datetime
    is_active: bool = True

    class Config:
        from_attributes = True


class SourceListResponse(BaseModel):
    """Schema for source list response."""

    sources: list[SourceResponse]
    total: int
