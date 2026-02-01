"""Articles API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Query

from app.schemas.article import ArticleListResponse, ArticleResponse

router = APIRouter()


@router.get("", response_model=ArticleListResponse)
async def list_articles(
    feed_id: UUID | None = None,
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
) -> ArticleListResponse:
    """
    List articles, optionally filtered by feed.

    Articles are stored in DynamoDB and retrieved in reverse chronological order.
    """
    # TODO: Implement DynamoDB query
    # For now, return empty list
    return ArticleListResponse(
        articles=[],
        total=0,
        limit=limit,
        offset=offset,
    )


@router.get("/{article_id}", response_model=ArticleResponse)
async def get_article(article_id: str) -> ArticleResponse:
    """Get a specific article by ID."""
    # TODO: Implement DynamoDB get_item
    # For now, return mock data
    from datetime import UTC, datetime

    return ArticleResponse(
        id=article_id,
        feed_id=UUID("00000000-0000-0000-0000-000000000000"),
        title="Sample Article",
        summary="This is a placeholder article. DynamoDB integration pending.",
        url="https://example.com/article",
        source_url="https://example.com",
        source_name="Example",
        published_at=datetime.now(UTC),
        scraped_at=datetime.now(UTC),
        thumbnail_url=None,
    )


@router.post("/scrape")
async def trigger_scrape(feed_id: UUID) -> dict:
    """
    Trigger a manual scrape for all sources in a feed.

    This will use Claude to extract articles from each source.
    """
    # TODO: Implement scraping with Claude
    return {
        "feed_id": str(feed_id),
        "status": "queued",
        "message": "Scraping will be implemented with Claude SDK",
    }
