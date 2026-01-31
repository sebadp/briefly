"""Dashboard schemas."""

from datetime import datetime
from uuid import UUID
from typing import Optional, Any
from pydantic import BaseModel

class DashboardBase(BaseModel):
    topic: str
    name: str
    description: Optional[str] = None

class DashboardCreate(DashboardBase):
    sources: list[dict[str, Any]] # List of found sources to be added

class DashboardResponse(DashboardBase):
    id: UUID
    created_at: datetime
    is_active: bool
    source_count: int = 0
