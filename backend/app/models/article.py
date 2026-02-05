"""Article model for caching scraped articles."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class Article(SQLModel, table=True):
    """
    Cached article model - stores scraped article content.
    Articles belong to a source and can be displayed in dashboards.
    """

    __tablename__ = "articles"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    source_id: UUID = Field(foreign_key="sources.id", index=True)

    # Article content
    title: str = Field(max_length=500)
    summary: str | None = Field(default=None)
    url: str = Field(max_length=2048, unique=True, index=True)
    
    # Metadata
    author: str | None = Field(default=None, max_length=200)
    published_at: datetime | None = Field(default=None)
    image_url: str | None = Field(default=None, max_length=2048)

    # Scraping info
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Status
    is_active: bool = Field(default=True)
