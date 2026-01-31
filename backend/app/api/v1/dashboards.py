"""Dashboard API endpoints."""

from uuid import UUID, uuid4
from datetime import datetime, UTC

from fastapi import APIRouter, HTTPException, status
from app.schemas.dashboard import DashboardCreate, DashboardResponse
from app.api.v1.sources import _sources_db  # Shared in-memory DB for MVP linkage

router = APIRouter()

# In-memory storage for MVP
_dashboards_db: dict[UUID, dict] = {}
# Link table for Dashboard -> Sources
_dashboard_sources: dict[UUID, list[UUID]] = {}

@router.get("", response_model=list[DashboardResponse])
async def list_dashboards():
    """List all dashboards."""
    results = []
    for d in _dashboards_db.values():
        d_id = d["id"]
        count = len(_dashboard_sources.get(d_id, []))
        results.append(DashboardResponse(**d, source_count=count))
    return results

@router.get("/{dashboard_id}", response_model=DashboardResponse)
async def get_dashboard(dashboard_id: UUID):
    """Get dashboard by ID."""
    if dashboard_id not in _dashboards_db:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    
    d = _dashboards_db[dashboard_id]
    count = len(_dashboard_sources.get(dashboard_id, []))
    return DashboardResponse(**d, source_count=count)

@router.post("", response_model=DashboardResponse, status_code=status.HTTP_201_CREATED)
async def create_dashboard(dashboard_in: DashboardCreate):
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
        "research_results": {"original_sources": dashboard_in.sources}
    }
    _dashboards_db[dashboard_id] = dashboard
    _dashboard_sources[dashboard_id] = []
    
    # Create Sources
    from app.api.v1.sources import create_source
    from app.schemas.source import SourceCreate
    
    for src in dashboard_in.sources:
        try:
            # We use a dummy UUID for feed_id since this isn't a "Feed" model 
            # In a real DB we'd have a dashboard_id FK on Source or a many-to-many
            # For this MVP, we'll tag them in our link table
            
            # Simple source creation
            s_id = uuid4()
            source = {
                "id": s_id,
                "feed_id": None, # Unassociated
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
            
    return DashboardResponse(**dashboard, source_count=len(_dashboard_sources[dashboard_id]))

@router.get("/{dashboard_id}/sources")
async def get_dashboard_sources(dashboard_id: UUID):
    """Get all sources for a specific dashboard."""
    if dashboard_id not in _dashboards_db:
        raise HTTPException(status_code=404, detail="Dashboard not found")
        
    source_ids = _dashboard_sources.get(dashboard_id, [])
    sources = []
    
    for sid in source_ids:
        if sid in _sources_db:
            sources.append(_sources_db[sid])
            
    return {"sources": sources, "total": len(sources)}
