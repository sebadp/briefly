"""Feeds API endpoints."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres import get_session as get_db
from app.schemas.feed import (
    FeedCreate,
    FeedCreateFromNL,
    FeedListResponse,
    FeedResponse,
)

router = APIRouter()


# In-memory storage for MVP (will be replaced with PostgreSQL)
_feeds_db: dict[UUID, dict[str, Any]] = {}


@router.get("", response_model=FeedListResponse)
async def list_feeds() -> FeedListResponse:
    """List all feeds for the current user."""
    feeds = list(_feeds_db.values())
    return FeedListResponse(feeds=[FeedResponse.model_validate(feed) for feed in feeds], total=len(feeds))


@router.post("", response_model=FeedResponse, status_code=status.HTTP_201_CREATED)
async def create_feed(feed_in: FeedCreate, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Create a new feed with explicit configuration."""
    from datetime import UTC, datetime
    from uuid import uuid4

    feed_id = uuid4()
    feed = {
        "id": feed_id,
        "name": feed_in.name,
        "natural_language_query": feed_in.natural_language_query,
        "refresh_interval_minutes": feed_in.refresh_interval_minutes,
        "created_at": datetime.now(UTC),
        "sources": [],
    }
    _feeds_db[feed_id] = feed
    return FeedResponse.model_validate(feed).model_dump()


@router.post(
    "/from-natural-language",
    response_model=FeedResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_feed_from_natural_language(request: FeedCreateFromNL) -> FeedResponse:
    """
    Create a feed from a natural language description.

    Example: "Noticias de tecnología e IA en español"

    The AI agent will interpret the query and suggest relevant sources.
    """
    from datetime import UTC, datetime
    from uuid import uuid4

    # TODO: Use Strands agent to interpret the query
    # For now, create a basic feed
    feed_id = uuid4()
    feed = {
        "id": feed_id,
        "name": f"Feed: {request.query[:30]}...",
        "natural_language_query": request.query,
        "refresh_interval_minutes": 60,
        "created_at": datetime.now(UTC),
        "sources": [],
        "ai_interpretation": {
            "status": "pending",
            "message": "AI interpretation will be implemented with Strands",
        },
    }
    _feeds_db[feed_id] = feed
    return FeedResponse.model_validate(feed)


@router.get("/{feed_id}", response_model=FeedResponse)
async def get_feed(feed_id: UUID) -> FeedResponse:
    """Get a specific feed by ID."""
    if feed_id not in _feeds_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feed {feed_id} not found",
        )
    return FeedResponse.model_validate(_feeds_db[feed_id])


@router.delete("/{feed_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_feed(feed_id: UUID) -> None:
    """Delete a feed."""
    if feed_id not in _feeds_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feed {feed_id} not found",
        )
    del _feeds_db[feed_id]
