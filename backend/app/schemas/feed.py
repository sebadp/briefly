"""Feed schemas for API request/response validation."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class FeedBase(BaseModel):
    """Base feed schema with shared fields."""

    name: str = Field(..., min_length=1, max_length=100)
    natural_language_query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="The natural language description of the feed",
    )
    refresh_interval_minutes: int = Field(
        default=60,
        ge=5,
        le=1440,
        description="How often to refresh the feed (5 min to 24 hours)",
    )


class FeedCreate(FeedBase):
    """Schema for creating a feed with explicit configuration."""

    pass


class FeedCreateFromNL(BaseModel):
    """Schema for creating a feed from natural language only."""

    query: str = Field(
        ...,
        min_length=3,
        max_length=500,
        examples=[
            "Noticias de tecnología e IA en español",
            "Tech startups in Latin America",
            "Climate change and sustainability news",
        ],
    )


class FeedResponse(FeedBase):
    """Schema for feed responses."""

    id: UUID
    created_at: datetime
    sources: list[dict[str, Any]] = Field(default_factory=list)
    ai_interpretation: dict[str, Any] | None = None
    details: dict[str, Any] | None = Field(default=None)
    meta: dict[str, Any] | None = Field(default=None)

    class Config:
        from_attributes = True


class FeedListResponse(BaseModel):
    """Schema for paginated feed list response."""

    feeds: list[FeedResponse]
    total: int
