"""Dashboard schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class DashboardBase(BaseModel):
    topic: str
    name: str
    description: str | None = None


class DashboardCreate(DashboardBase):
    sources: list[dict[str, Any]]  # List of found sources to be added


class ManualDashboardCreate(BaseModel):
    """Schema for creating a dashboard manually with URLs."""

    name: str
    urls: list[str]  # List of URLs to add as sources


class AddSourceRequest(BaseModel):
    """Schema for adding a source to an existing dashboard."""

    url: str
    name: str | None = None


class DashboardResponse(DashboardBase):
    id: UUID
    created_at: datetime
    is_active: bool
    source_count: int = 0

