"""Feed model for PostgreSQL."""

from datetime import datetime, UTC
from uuid import UUID, uuid4

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel, Relationship


class Feed(SQLModel, table=True):
    """News feed model - stores user's personalized feed configurations."""

    __tablename__ = "feeds"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    
    # Feed configuration
    name: str = Field(max_length=100)
    natural_language_query: str = Field(max_length=500)
    refresh_interval_minutes: int = Field(default=60, ge=5, le=1440)
    
    # AI interpretation results
    interpreted_topics: list[str] = Field(default=[], sa_column=Column(JSON, default=[]))
    interpreted_language: str | None = Field(default=None, max_length=10)
    
    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_scraped_at: datetime | None = Field(default=None)
    
    # Status
    is_active: bool = Field(default=True)
    
    # Relationships
    sources: list["Source"] = Relationship(back_populates="feed")


class Source(SQLModel, table=True):
    """News source model - websites/RSS feeds to scrape."""

    __tablename__ = "sources"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    feed_id: UUID = Field(foreign_key="feeds.id", index=True)
    
    # Source configuration
    url: str = Field(max_length=2048)
    name: str = Field(max_length=100)
    source_type: str = Field(default="website", max_length=20)  # website, rss, atom
    
    # Scraping configuration (for advanced use)
    selector_config: dict | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    
    # Status
    is_active: bool = Field(default=True)
    last_scraped_at: datetime | None = Field(default=None)
    last_error: str | None = Field(default=None, max_length=500)
    
    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    
    # Relationships
    feed: Feed = Relationship(back_populates="sources")
