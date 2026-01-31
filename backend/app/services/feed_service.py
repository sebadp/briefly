"""Feed service - Business logic for feed management."""

from uuid import UUID
from datetime import datetime, UTC
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models import Feed, Source
from app.agents import interpret_feed_query, scrape_single_article
from app.db.dynamodb import dynamodb


class FeedService:
    """Service for managing news feeds."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_feed(
        self,
        user_id: UUID,
        name: str,
        natural_language_query: str,
        refresh_interval_minutes: int = 60,
    ) -> Feed:
        """Create a new feed."""
        feed = Feed(
            user_id=user_id,
            name=name,
            natural_language_query=natural_language_query,
            refresh_interval_minutes=refresh_interval_minutes,
        )
        self.session.add(feed)
        await self.session.commit()
        await self.session.refresh(feed)
        return feed

    async def create_feed_from_nl(
        self,
        user_id: UUID,
        query: str,
    ) -> tuple[Feed, dict[str, Any]]:
        """
        Create a feed from a natural language query.
        
        Uses the AI agent to interpret the query and suggest sources.
        """
        # Get AI interpretation
        config = await interpret_feed_query(query)
        
        # Create the feed
        feed = Feed(
            user_id=user_id,
            name=config.get("feed_name", f"Feed: {query[:30]}"),
            natural_language_query=query,
            refresh_interval_minutes=config.get("refresh_interval_minutes", 60),
            interpreted_topics=config.get("topics", []),
            interpreted_language=config.get("language", "es"),
        )
        self.session.add(feed)
        await self.session.commit()
        await self.session.refresh(feed)
        
        # Add suggested sources
        for source_data in config.get("sources", []):
            source = Source(
                feed_id=feed.id,
                url=source_data.get("url", ""),
                name=source_data.get("name", ""),
                source_type=source_data.get("type", "website"),
            )
            self.session.add(source)
        
        await self.session.commit()
        
        return feed, config

    async def get_feed(self, feed_id: UUID) -> Feed | None:
        """Get a feed by ID."""
        result = await self.session.get(Feed, feed_id)
        return result

    async def get_user_feeds(self, user_id: UUID) -> list[Feed]:
        """Get all feeds for a user."""
        result = await self.session.execute(
            select(Feed).where(Feed.user_id == user_id)
        )
        return list(result.scalars().all())

    async def delete_feed(self, feed_id: UUID) -> bool:
        """Delete a feed and its sources."""
        feed = await self.get_feed(feed_id)
        if not feed:
            return False
        
        await self.session.delete(feed)
        await self.session.commit()
        return True

    async def add_source(
        self,
        feed_id: UUID,
        url: str,
        name: str,
        source_type: str = "website",
    ) -> Source:
        """Add a source to a feed."""
        source = Source(
            feed_id=feed_id,
            url=url,
            name=name,
            source_type=source_type,
        )
        self.session.add(source)
        await self.session.commit()
        await self.session.refresh(source)
        return source

    async def scrape_feed(self, feed_id: UUID) -> dict[str, Any]:
        """
        Scrape all sources in a feed and store articles.
        
        Returns stats about the scraping operation.
        """
        feed = await self.get_feed(feed_id)
        if not feed:
            return {"error": "Feed not found"}
        
        # Get sources
        result = await self.session.execute(
            select(Source).where(Source.feed_id == feed_id, Source.is_active == True)
        )
        sources = list(result.scalars().all())
        
        stats = {
            "feed_id": str(feed_id),
            "sources_processed": 0,
            "articles_saved": 0,
            "errors": [],
        }
        
        for source in sources:
            try:
                # Scrape the source
                article = await scrape_single_article(source.url)
                
                if article:
                    # Save to DynamoDB
                    await dynamodb.put_article(
                        feed_id=feed_id,
                        article_id=f"{source.id}-{datetime.now(UTC).timestamp()}",
                        title=article.title,
                        summary=article.summary,
                        url=article.url,
                        source_url=source.url,
                        source_name=source.name,
                        published_at=article.published_at,
                        thumbnail_url=article.thumbnail_url,
                    )
                    stats["articles_saved"] += 1
                
                stats["sources_processed"] += 1
                
                # Update source last_scraped_at
                source.last_scraped_at = datetime.now(UTC)
                source.last_error = None
                
            except Exception as e:
                stats["errors"].append({"source": source.url, "error": str(e)})
                source.last_error = str(e)[:500]
        
        # Update feed last_scraped_at
        feed.last_scraped_at = datetime.now(UTC)
        await self.session.commit()
        
        return stats
