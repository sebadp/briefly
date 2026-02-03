"""Dashboard API endpoints with PostgreSQL persistence."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres import get_session as get_db
from app.models import Dashboard, DashboardSource, Source
from app.schemas.dashboard import (
    AddSourceRequest,
    DashboardCreate,
    DashboardResponse,
    ManualDashboardCreate,
)

router = APIRouter()


@router.get("", response_model=list[DashboardResponse])
async def list_dashboards(db: AsyncSession = Depends(get_db)) -> list[DashboardResponse]:
    """List all dashboards."""
    # Get all dashboards
    result = await db.execute(select(Dashboard).where(Dashboard.is_active == True))
    dashboards = result.scalars().all()

    # Get source counts for each dashboard
    responses = []
    for dashboard in dashboards:
        count_result = await db.execute(
            select(func.count(DashboardSource.id)).where(
                DashboardSource.dashboard_id == dashboard.id
            )
        )
        source_count = count_result.scalar() or 0

        responses.append(
            DashboardResponse(
                id=dashboard.id,
                topic=dashboard.topic,
                name=dashboard.name,
                description=dashboard.description,
                created_at=dashboard.created_at,
                is_active=dashboard.is_active,
                source_count=source_count,
            )
        )

    return responses


@router.get("/{dashboard_id}", response_model=DashboardResponse)
async def get_dashboard(
    dashboard_id: UUID, db: AsyncSession = Depends(get_db)
) -> DashboardResponse:
    """Get dashboard by ID."""
    result = await db.execute(select(Dashboard).where(Dashboard.id == dashboard_id))
    dashboard = result.scalar_one_or_none()

    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")

    # Get source count
    count_result = await db.execute(
        select(func.count(DashboardSource.id)).where(
            DashboardSource.dashboard_id == dashboard_id
        )
    )
    source_count = count_result.scalar() or 0

    return DashboardResponse(
        id=dashboard.id,
        topic=dashboard.topic,
        name=dashboard.name,
        description=dashboard.description,
        created_at=dashboard.created_at,
        is_active=dashboard.is_active,
        source_count=source_count,
    )


@router.post("", response_model=DashboardResponse, status_code=status.HTTP_201_CREATED)
async def create_dashboard(
    dashboard_in: DashboardCreate, db: AsyncSession = Depends(get_db)
) -> DashboardResponse:
    """
    Create a new dashboard from research results.
    Automatically creates the associated sources.
    """
    # Create Dashboard
    dashboard = Dashboard(
        topic=dashboard_in.topic,
        name=dashboard_in.name,
        description=dashboard_in.description,
        research_results={"original_sources": dashboard_in.sources},
    )
    db.add(dashboard)
    await db.flush()  # Get the ID

    # Create Sources and link them
    for src in dashboard_in.sources:
        try:
            # Create source
            source = Source(
                url=src["url"],
                name=src["name"],
                source_type="website",
            )
            db.add(source)
            await db.flush()

            # Create link
            link = DashboardSource(
                dashboard_id=dashboard.id,
                source_id=source.id,
            )
            db.add(link)
        except Exception as e:
            print(f"Error creating source for dashboard: {e}")

    await db.commit()
    await db.refresh(dashboard)

    # Count sources
    count_result = await db.execute(
        select(func.count(DashboardSource.id)).where(
            DashboardSource.dashboard_id == dashboard.id
        )
    )
    source_count = count_result.scalar() or 0

    return DashboardResponse(
        id=dashboard.id,
        topic=dashboard.topic,
        name=dashboard.name,
        description=dashboard.description,
        created_at=dashboard.created_at,
        is_active=dashboard.is_active,
        source_count=source_count,
    )


@router.get("/{dashboard_id}/sources")
async def get_dashboard_sources(
    dashboard_id: UUID, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """Get all sources for a specific dashboard."""
    # Verify dashboard exists
    result = await db.execute(select(Dashboard).where(Dashboard.id == dashboard_id))
    dashboard = result.scalar_one_or_none()

    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")

    # Get sources via join
    query = (
        select(Source)
        .join(DashboardSource, DashboardSource.source_id == Source.id)
        .where(DashboardSource.dashboard_id == dashboard_id)
    )
    result = await db.execute(query)
    sources = result.scalars().all()

    return {
        "sources": [
            {
                "id": str(s.id),
                "url": s.url,
                "name": s.name,
                "source_type": s.source_type,
                "is_active": s.is_active,
                "created_at": s.created_at.isoformat(),
            }
            for s in sources
        ],
        "total": len(sources),
    }


@router.post("/manual", response_model=DashboardResponse, status_code=status.HTTP_201_CREATED)
async def create_manual_dashboard(
    dashboard_in: ManualDashboardCreate, db: AsyncSession = Depends(get_db)
) -> DashboardResponse:
    """
    Create a new dashboard manually with a list of URLs.
    Skips the research agent - directly adds URLs as sources.
    """
    # Create Dashboard
    dashboard = Dashboard(
        topic="Manual",
        name=dashboard_in.name,
        description=None,
    )
    db.add(dashboard)
    await db.flush()

    # Create Sources from URLs
    for url in dashboard_in.urls:
        try:
            # Extract domain as name
            domain = url.split("//")[-1].split("/")[0].replace("www.", "")

            source = Source(
                url=url,
                name=domain,
                source_type="website",
            )
            db.add(source)
            await db.flush()

            # Create link
            link = DashboardSource(
                dashboard_id=dashboard.id,
                source_id=source.id,
            )
            db.add(link)
        except Exception as e:
            print(f"Error creating source for URL {url}: {e}")

    await db.commit()
    await db.refresh(dashboard)

    # Count sources
    count_result = await db.execute(
        select(func.count(DashboardSource.id)).where(
            DashboardSource.dashboard_id == dashboard.id
        )
    )
    source_count = count_result.scalar() or 0

    return DashboardResponse(
        id=dashboard.id,
        topic=dashboard.topic,
        name=dashboard.name,
        description=dashboard.description,
        created_at=dashboard.created_at,
        is_active=dashboard.is_active,
        source_count=source_count,
    )


@router.post(
    "/{dashboard_id}/sources", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED
)
async def add_source_to_dashboard(
    dashboard_id: UUID, source_in: AddSourceRequest, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """
    Add a new source URL to an existing dashboard.
    """
    # Verify dashboard exists
    result = await db.execute(select(Dashboard).where(Dashboard.id == dashboard_id))
    dashboard = result.scalar_one_or_none()

    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")

    # Extract domain as name if not provided
    domain = source_in.url.split("//")[-1].split("/")[0].replace("www.", "")
    name = source_in.name or domain

    # Create source
    source = Source(
        url=source_in.url,
        name=name,
        source_type="website",
    )
    db.add(source)
    await db.flush()

    # Create link
    link = DashboardSource(
        dashboard_id=dashboard_id,
        source_id=source.id,
    )
    db.add(link)
    await db.commit()

    return {
        "source": {
            "id": str(source.id),
            "url": source.url,
            "name": source.name,
            "source_type": source.source_type,
            "is_active": source.is_active,
        },
        "message": "Source added successfully",
    }


@router.delete("/{dashboard_id}/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_source_from_dashboard(
    dashboard_id: UUID, source_id: UUID, db: AsyncSession = Depends(get_db)
) -> None:
    """Remove a source from a dashboard."""
    # Verify dashboard exists
    result = await db.execute(select(Dashboard).where(Dashboard.id == dashboard_id))
    dashboard = result.scalar_one_or_none()

    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")

    # Find the link
    result = await db.execute(
        select(DashboardSource).where(
            DashboardSource.dashboard_id == dashboard_id,
            DashboardSource.source_id == source_id,
        )
    )
    link = result.scalar_one_or_none()

    if not link:
        raise HTTPException(status_code=404, detail="Source not found in this dashboard")

    # Delete the link
    await db.delete(link)

    # Also delete the source if it's not linked to any other dashboard
    count_result = await db.execute(
        select(func.count(DashboardSource.id)).where(DashboardSource.source_id == source_id)
    )
    other_links = count_result.scalar() or 0

    if other_links == 0:
        source_result = await db.execute(select(Source).where(Source.id == source_id))
        source = source_result.scalar_one_or_none()
        if source:
            await db.delete(source)

    await db.commit()
