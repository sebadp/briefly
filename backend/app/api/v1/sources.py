"""Sources API endpoints."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.schemas.source import SourceCreate, SourceResponse, SourceListResponse

router = APIRouter()

# In-memory storage for MVP
_sources_db: dict[UUID, dict] = {}


@router.get("", response_model=SourceListResponse)
async def list_sources(feed_id: UUID | None = None) -> SourceListResponse:
    """List all sources, optionally filtered by feed."""
    sources = list(_sources_db.values())
    if feed_id:
        sources = [s for s in sources if s.get("feed_id") == feed_id]
    return SourceListResponse(sources=sources, total=len(sources))


@router.post("", response_model=SourceResponse, status_code=status.HTTP_201_CREATED)
async def create_source(source_in: SourceCreate) -> SourceResponse:
    """Add a new source to a feed."""
    from uuid import uuid4
    from datetime import datetime, UTC

    source_id = uuid4()
    source = {
        "id": source_id,
        "feed_id": source_in.feed_id,
        "url": str(source_in.url),
        "name": source_in.name,
        "source_type": source_in.source_type,
        "created_at": datetime.now(UTC),
        "is_active": True,
    }
    _sources_db[source_id] = source
    return SourceResponse(**source)


@router.get("/{source_id}", response_model=SourceResponse)
async def get_source(source_id: UUID) -> SourceResponse:
    """Get a specific source by ID."""
    if source_id not in _sources_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source {source_id} not found",
        )
    return SourceResponse(**_sources_db[source_id])


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source(source_id: UUID) -> None:
    """Remove a source."""
    if source_id not in _sources_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source {source_id} not found",
        )
    del _sources_db[source_id]


@router.post("/{source_id}/validate", response_model=dict)
async def validate_source(source_id: UUID) -> dict:
    """Validate that a source URL is accessible and can be scraped."""
    if source_id not in _sources_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source {source_id} not found",
        )
    
    source = _sources_db[source_id]
    
    # TODO: Actually validate the URL with httpx
    return {
        "source_id": source_id,
        "url": source["url"],
        "is_valid": True,
        "message": "Source validation will be implemented",
    }
