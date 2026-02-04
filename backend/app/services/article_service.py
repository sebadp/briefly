"""Article service for hybrid PostgreSQL + DynamoDB storage."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.dynamodb import dynamodb
from app.models import Article


async def save_scraped_article(
    db: AsyncSession,
    source_id: UUID,
    title: str,
    summary: str | None,
    url: str,
    source_name: str,
    author: str | None = None,
    published_at: datetime | None = None,
    image_url: str | None = None,
    feed_id: UUID | None = None,
) -> Article:
    """
    Save a scraped article to both PostgreSQL and DynamoDB.
    
    PostgreSQL: Source of truth for metadata (uniqueness by URL)
    DynamoDB: Cache for fast feed-based queries
    """
    
    # Check for existing article in PostgreSQL by URL
    result = await db.execute(select(Article).where(Article.url == url))
    existing = result.scalar_one_or_none()
    
    if existing:
        article = existing
        # Even if it exists, we might want to ensure we have the ID for DynamoDB
        article_id = article.id
    else:
        article_id = uuid4()
        
        # Save to PostgreSQL
        article = Article(
            id=article_id,
            source_id=source_id,
            title=title,
            summary=summary,
            url=url,
            author=author,
            published_at=published_at,
            image_url=image_url,
        )
        db.add(article)
        # Flush to ensure this new article is visible to subsequent queries in the same transaction
        await db.flush()
    
    # Save to DynamoDB if we have a feed_id (Overwrite/Cache)
    # DynamoDB handles upserts automatically
    if feed_id:
        try:
            await dynamodb.put_article(
                feed_id=feed_id,
                article_id=str(article_id),
                title=title,
                summary=summary or "",
                url=url,
                source_url=url,
                source_name=source_name,
                published_at=published_at,
                thumbnail_url=image_url,
            )
        except Exception as e:
            print(f"Failed to save article to DynamoDB: {e}")
    
    return article


async def save_scraped_articles_batch(
    db: AsyncSession,
    source_id: UUID,
    articles_data: list[dict],
    source_name: str,
    feed_id: UUID | None = None,
) -> list[Article]:
    """
    Save multiple scraped articles to both databases.
    """
    saved = []
    
    for art in articles_data:
        try:
            # Handle potential ISO format issues with Z
            pub_date = None
            if art.get("published_at"):
                try:
                    pub_date = datetime.fromisoformat(art["published_at"].replace("Z", "+00:00"))
                except ValueError:
                    # If format is really weird, ignore date
                    pass

            article = await save_scraped_article(
                db=db,
                source_id=source_id,
                title=art.get("title", "Untitled"),
                summary=art.get("summary"),
                url=art.get("url", ""),
                source_name=source_name,
                author=art.get("author"),
                published_at=pub_date,
                image_url=art.get("image_url"),
                feed_id=feed_id,
            )
            saved.append(article)
        except Exception as e:
            print(f"Failed to save article {art.get('url')}: {e}")
    
    return saved
