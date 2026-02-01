"""User model for PostgreSQL."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    """User account model."""

    __tablename__ = "users"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(unique=True, index=True, max_length=255)
    name: str | None = Field(default=None, max_length=100)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    is_active: bool = Field(default=True)

    # User settings stored as JSON
    settings: dict[str, Any] = Field(
        default_factory=lambda: {
            "llm_provider": "gemini",
            "language": "es",
            "theme": "dark",
            "articles_per_source": 5,
            "max_sources_per_briefing": 8,
            "min_relevance_score": 7,
        },
        sa_column=Column(JSONB, default={}),
    )
