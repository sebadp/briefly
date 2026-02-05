"""Articles API endpoints with hybrid PostgreSQL + DynamoDB storage."""

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dynamodb import dynamodb
from app.db.postgres import get_session as get_db
from app.models import Article, Source
from app.schemas.article import ArticleListResponse, ArticleResponse

router = APIRouter()


@router.get("", response_model=ArticleListResponse)
async def list_articles(
    feed_id: UUID | None = None,
    source_id: UUID | None = None,
    dashboard_id: UUID | None = None,
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> ArticleListResponse:
    """
    List articles with optional filters.
    
    - feed_id: Filter by feed (for DynamoDB cache)
    - source_id: Filter by source (PostgreSQL)
    - dashboard_id: Filter by dashboard sources (PostgreSQL)
    """
    # Try DynamoDB for feed-based queries (optimized for this)
    if feed_id:
        try:
            articles = await dynamodb.get_articles_by_feed(feed_id, limit=limit)
            return ArticleListResponse(
                articles=[
                    ArticleResponse(
                        id=a["id"],
                        feed_id=feed_id,
                        title=a["title"],
                        summary=a["summary"],
                        url=a["url"],
                        source_url=a["source_url"],
                        source_name=a["source_name"],
                        published_at=datetime.fromisoformat(a["published_at"]) if a.get("published_at") else None,
                        scraped_at=datetime.fromisoformat(a["scraped_at"]) if a.get("scraped_at") else None,
                        thumbnail_url=a.get("thumbnail_url"),
                    )
                    for a in articles
                ],
                total=len(articles),
                limit=limit,
                offset=offset,
            )
        except Exception as e:
            print(f"DynamoDB query failed, falling back to PostgreSQL: {e}")

    # PostgreSQL fallback / source-based queries
    query = select(Article).where(Article.is_active == True)
    
    if source_id:
        query = query.where(Article.source_id == source_id)
    
    if dashboard_id:
        # Get sources for this dashboard and filter articles
        from app.models import DashboardSource
        subquery = select(DashboardSource.source_id).where(
            DashboardSource.dashboard_id == dashboard_id
        )
        query = query.where(Article.source_id.in_(subquery))
    
    query = query.order_by(Article.scraped_at.desc()).offset(offset).limit(limit)
    
    result = await db.execute(query)
    articles = result.scalars().all()
    
    return ArticleListResponse(
        articles=[
            ArticleResponse(
                id=str(a.id),
                feed_id=UUID("00000000-0000-0000-0000-000000000000"),  # No feed for PG articles
                title=a.title,
                summary=a.summary or "",
                url=a.url,
                source_url=a.url,
                source_name="",
                published_at=a.published_at,
                scraped_at=a.scraped_at,
                thumbnail_url=a.image_url,
            )
            for a in articles
        ],
        total=len(articles),
        limit=limit,
        offset=offset,
    )


@router.get("/{article_id}", response_model=ArticleResponse)
async def get_article(
    article_id: str,
    db: AsyncSession = Depends(get_db),
) -> ArticleResponse:
    """Get a specific article by ID."""
    # Try PostgreSQL first
    try:
        article_uuid = UUID(article_id)
        result = await db.execute(select(Article).where(Article.id == article_uuid))
        article = result.scalar_one_or_none()
        
        if article:
            return ArticleResponse(
                id=str(article.id),
                feed_id=UUID("00000000-0000-0000-0000-000000000000"),
                title=article.title,
                summary=article.summary or "",
                url=article.url,
                source_url=article.url,
                source_name="",
                published_at=article.published_at,
                scraped_at=article.scraped_at,
                thumbnail_url=article.image_url,
            )
    except ValueError:
        pass  # Not a valid UUID, try DynamoDB

    raise HTTPException(status_code=404, detail="Article not found")


@router.post("/scrape")
async def trigger_scrape(
    feed_id: UUID | None = None,
    source_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Trigger a manual scrape for sources.
    
    This will use the AI scraper to extract articles from sources.
    """
    if not feed_id and not source_id:
        raise HTTPException(
            status_code=400,
            detail="Either feed_id or source_id must be provided"
        )
    
    # For now, return queued status
    # The actual scraping is done via the sources API
    return {
        "feed_id": str(feed_id) if feed_id else None,
        "source_id": str(source_id) if source_id else None,
        "status": "queued",
        "message": "Use /sources/{id}/scrape for scraping",
    }
