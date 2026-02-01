"""Sources API endpoints."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.schemas.source import SourceCreate, SourceListResponse, SourceResponse

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
    from datetime import UTC, datetime
    from uuid import uuid4

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


@router.post("/add-and-scrape", response_model=dict, status_code=status.HTTP_201_CREATED)
async def add_source_and_scrape(url: str, name: str = "") -> dict:
    """
    Add a new source URL and immediately scrape it.

    Returns the scraped article content and creates the source.
    """
    from datetime import UTC, datetime
    from uuid import uuid4

    from app.agents import get_scraper_agent

    # Create source entry
    source_id = uuid4()

    # Scrape the URL
    scraper = get_scraper_agent()
    try:
        article = await scraper.scrape_article(url, name or "")

        # Save source with scraped data preview
        source = {
            "id": source_id,
            "feed_id": None,  # Can be associated later
            "url": url,
            "name": name or article.source_name,
            "source_type": "website",
            "created_at": datetime.now(UTC),
            "is_active": True,
            "last_scraped_at": datetime.now(UTC),
            "last_article_title": article.title,
            "last_article_summary": article.summary[:200] if article.summary else "",
        }
        _sources_db[source_id] = source

        return {
            "source": source,
            "scraped_article": {
                "title": article.title,
                "summary": article.summary,
                "url": article.url,
                "source_name": article.source_name,
                "published_at": article.published_at.isoformat() if article.published_at else None,
                "author": article.author,
                "image_url": article.image_url,
            },
            "message": "Source added and scraped successfully",
        }
    except Exception as e:
        # Still create source even if scraping fails
        source = {
            "id": source_id,
            "feed_id": None,
            "url": url,
            "name": name or url.split("//")[-1].split("/")[0],
            "source_type": "website",
            "created_at": datetime.now(UTC),
            "is_active": True,
            "scrape_error": str(e),
        }
        _sources_db[source_id] = source

        return {
            "source": source,
            "scraped_article": None,
            "message": f"Source added but scraping failed: {e}",
        }
    finally:
        await scraper.close()


@router.post("/add-and-scrape-multiple", response_model=dict, status_code=status.HTTP_201_CREATED)
async def add_source_and_scrape_multiple(url: str, name: str = "", article_count: int = 5) -> dict:
    """
    Add a new source URL and immediately scrape multiple articles from it.

    Args:
        url: URL of the news source homepage/section
        name: Optional name for the source
        article_count: Number of articles to scrape (default 5, max 20)

    Returns:
        Source object and list of scraped articles
    """
    from datetime import UTC, datetime
    from uuid import uuid4

    from app.agents import get_scraper_agent

    # Validate count
    if article_count < 1:
        article_count = 1
    if article_count > 20:
        article_count = 20

    # Create source entry (or update if I had persistence, but MVP is in-memory)
    # Check if exists first? MVP simplifies to just creating new ID most likely,
    # but let's check by URL to be nicer
    existing_id = None
    for sid, s in _sources_db.items():
        if s["url"] == url:
            existing_id = sid
            break

    source_id = existing_id or uuid4()

    # Scrape the URL
    scraper = get_scraper_agent()
    try:
        articles = await scraper.scrape_multiple_from_homepage(url, limit=article_count)

        # Convert to dicts for response
        scraped_data = []
        last_article = None

        for art in articles:
            # Handle both ExtractedArticle (Claude) and ScrapedArticle (Gemini) types
            # They have slightly different fields but compatible enough
            art_dict = {
                "title": art.title,
                "summary": art.summary,
                "url": art.url,
                "source_name": getattr(art, "source_name", name),
                "published_at": art.published_at.isoformat() if art.published_at else None,
                "author": art.author,
                "image_url": getattr(art, "image_url", getattr(art, "thumbnail_url", None)),
            }
            scraped_data.append(art_dict)
            last_article = art

        # Update/Create source
        if existing_id:
            source = _sources_db[existing_id]
        else:
            source = {
                "id": source_id,
                "feed_id": None,
                "url": url,
                "name": name or (last_article.source_name if last_article else url),
                "source_type": "website",
                "created_at": datetime.now(UTC),
                "is_active": True,
            }

        # Update scrape stats
        source["last_scraped_at"] = datetime.now(UTC)
        if last_article:
            source["last_article_title"] = last_article.title
            source["last_article_summary"] = (
                last_article.summary[:200] if last_article.summary else ""
            )
            if not source["name"] and getattr(last_article, "source_name", None):
                source["name"] = last_article.source_name

        _sources_db[source_id] = source

        return {
            "source": source,
            "scraped_articles": scraped_data,
            "count": len(scraped_data),
            "message": f"Source added/updated and {len(scraped_data)} articles scraped successfully",
        }
    except Exception as e:
        # Fallback if scraping fails completely
        print(f"Scrape failed: {e}")
        source = {
            "id": source_id,
            "feed_id": None,
            "url": url,
            "name": name or url,
            "source_type": "website",
            "created_at": datetime.now(UTC),
            "is_active": True,
            "scrape_error": str(e),
        }
        _sources_db[source_id] = source

        return {
            "source": source,
            "scraped_articles": [],
            "count": 0,
            "message": f"Source added but scraping failed: {e}",
        }
    finally:
        await scraper.close()
