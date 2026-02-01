"""Dashboard API endpoints."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres import get_session as get_db
from typing import Any

from app.api.v1.sources import _sources_db  # Shared in-memory DB for MVP linkage
from app.schemas.dashboard import DashboardCreate, DashboardResponse

router = APIRouter()

# In-memory storage for MVP
_dashboards_db: dict[UUID, dict[str, Any]] = {}
# Link table for Dashboard -> Sources
_dashboard_sources: dict[UUID, list[UUID]] = {}


@router.get("", response_model=list[DashboardResponse])
async def list_dashboards(db: AsyncSession = Depends(get_db)) -> list[DashboardResponse]:
    """List all dashboards."""
    results = []
    for d in _dashboards_db.values():
        d_id = d["id"]
        count = len(_dashboard_sources.get(d_id, []))
        results.append(DashboardResponse(**d, source_count=count))
    return results


@router.get("/{dashboard_id}", response_model=DashboardResponse)
async def get_dashboard(dashboard_id: UUID, db: AsyncSession = Depends(get_db)) -> DashboardResponse:
    """Get dashboard by ID."""
    if dashboard_id not in _dashboards_db:
        raise HTTPException(status_code=404, detail="Dashboard not found")

    d = _dashboards_db[dashboard_id]
    count = len(_dashboard_sources.get(dashboard_id, []))
    return DashboardResponse(**d, source_count=count)


@router.post("", response_model=DashboardResponse, status_code=status.HTTP_201_CREATED)
async def create_dashboard(dashboard_in: DashboardCreate, db: AsyncSession = Depends(get_db)) -> DashboardResponse:
    """
    Create a new dashboard from research results.
    Automatically creates the associated sources.
    """
    dashboard_id = uuid4()

    # Create Dashboard
    dashboard = {
        "id": dashboard_id,
        "topic": dashboard_in.topic,
        "name": dashboard_in.name,
        "description": dashboard_in.description,
        "created_at": datetime.now(UTC),
        "is_active": True,
        "research_results": {"original_sources": dashboard_in.sources},
    }
    _dashboards_db[dashboard_id] = dashboard
    _dashboard_sources[dashboard_id] = []

    # Create Sources

    for src in dashboard_in.sources:
        try:
            # We use a dummy UUID for feed_id since this isn't a "Feed" model
            # In a real DB we'd have a dashboard_id FK on Source or a many-to-many
            # For this MVP, we'll tag them in our link table

            # Simple source creation
            s_id = uuid4()
            source = {
                "id": s_id,
                "feed_id": None,  # Unassociated
                "url": src["url"],
                "name": src["name"],
                "source_type": "website",
                "created_at": datetime.now(UTC),
                "is_active": True,
            }
            # Add to global sources DB
            _sources_db[s_id] = source

            # Link to dashboard
            _dashboard_sources[dashboard_id].append(s_id)

        except Exception as e:
            print(f"Error creating source for dashboard: {e}")

    # Add source_count to the dashboard dictionary before validation
    dashboard["source_count"] = len(_dashboard_sources[dashboard_id])
    return DashboardResponse.model_validate(dashboard)


@router.get("/{dashboard_id}/sources")
async def get_dashboard_sources(dashboard_id: UUID) -> dict[str, Any]:
    """Get all sources for a specific dashboard."""
    if dashboard_id not in _dashboards_db:
        raise HTTPException(status_code=404, detail="Dashboard not found")

    source_ids = _dashboard_sources.get(dashboard_id, [])
    sources = []

    for sid in source_ids:
        if sid in _sources_db:
            sources.append(_sources_db[sid])

    return {"sources": sources, "total": len(sources)}
