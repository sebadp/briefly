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
    # Also save any initial articles found during research
    from app.services.article_service import save_scraped_articles_batch

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
            
            # Persist initial articles if present
            # ResearchAgent returns them in 'articles' key
            if "articles" in src and isinstance(src["articles"], list):
                await save_scraped_articles_batch(
                    db=db,
                    source_id=source.id,
                    articles_data=src["articles"],
                    source_name=source.name,
                    # We don't have a feed_id here since it's a dashboard source, 
                    # but we can try to save to DynamoDB using a dummy feed ID or just leave it for now.
                    # Actually, our architecture links sources to dashboards via feed-like mechanism?
                    # No, DashboardSource is many-to-many. 
                    # But save_scraped_articles_batch expects feed_id for DynamoDB.
                    # We should probably pass the dashboard_id as feed_id equivalent for caching?
                    # Or better: generate a feed_id for this dashboard?
                    # Wait, DynamoDB Articles are keyed by FEED_ID.
                    # If we want to view them in the dashboard, we query by... what?
                    # The get_articles endpoint queries by feed_id OR falls back to postgres.
                    # If we use dashboard_id as feed_id for now, it matches how we might query it.
                    feed_id=dashboard.id
                )

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


@router.post("/{dashboard_id}/refresh", status_code=status.HTTP_200_OK)
async def refresh_dashboard(
    dashboard_id: UUID, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """
    Manually trigger a re-scrape of all sources in this dashboard.
    Fetches new articles and updates the database.
    """
    from app.agents import get_scraper_agent
    from app.services.article_service import save_scraped_articles_batch
    from app.services.search_service import SearchService
    
    # 1. Get Dashboard and Sources
    result = await db.execute(select(Dashboard).where(Dashboard.id == dashboard_id))
    dashboard = result.scalar_one_or_none()
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")

    query = (
        select(Source)
        .join(DashboardSource, DashboardSource.source_id == Source.id)
        .where(DashboardSource.dashboard_id == dashboard_id)
    )
    result = await db.execute(query)
    sources = result.scalars().all()
    
    if not sources:
        return {"message": "No sources to refresh", "articles_processed": 0, "errors": []}

    # 2. Scrape each source
    scraper = get_scraper_agent()
    total_new_articles = 0
    errors = []

    try:
        for source in sources:
            try:
                # Scrape generic "news" from homepage
                articles = await scraper.scrape_multiple_from_homepage(source.url, limit=5)
                
                # Fallback site-search logic
                if not articles:
                    searchor = SearchService()
                    try:
                         # Clean URL for site: query
                         domain_only = source.url.replace("https://", "").replace("http://", "").rstrip("/").replace("www.", "")
                         fallback_query = f"site:{domain_only}"
                         fallback_results = await searchor.search(fallback_query, num_results=3)
                         if fallback_results:
                             links_to_scrape = [r["link"] for r in fallback_results if r.get("link")]
                             if links_to_scrape:
                                 articles = await scraper.scrape_articles(links_to_scrape, source_name=source.name)
                    except Exception as e:
                        print(f"Fallback search failed for {source.url}: {e}")
                    finally:
                        await searchor.close()

                # Save articles if found
                if articles:
                    articles_data = [
                        {
                            "title": a.title,
                            "url": a.url,
                            "summary": a.summary,
                            "published_at": a.published_at.isoformat() if a.published_at else None,
                            "image_url": a.image_url,
                            "author": a.author,
                        }
                        for a in articles
                    ]
                    
                    saved = await save_scraped_articles_batch(
                        db=db,
                        source_id=source.id,
                        articles_data=articles_data,
                        source_name=source.name,
                        feed_id=dashboard.id  # Use Dashboard ID as Feed ID for DynamoDB
                    )
                    total_new_articles += len(saved)
                    
                    # Optional: Update timestamps on source if we had that field
                    # source.updated_at = datetime.now(UTC)
                    # db.add(source)
                
            except Exception as e:
                print(f"Error scraping {source.url}: {e}")
                errors.append(f"{source.name}: {str(e)}")
                
        await db.commit()
    finally:
        if hasattr(scraper, "close"):
            await scraper.close()

    return {
        "message": f"Refreshed {len(sources)} sources.",
        "articles_processed": total_new_articles,
        "errors": errors
    }
