"""DashboardSource link table for many-to-many relationship."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class DashboardSource(SQLModel, table=True):
    """
    Link table for Dashboard <-> Source many-to-many relationship.
    A dashboard can have many sources, and a source can belong to many dashboards.
    """

    __tablename__ = "dashboard_sources"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    dashboard_id: UUID = Field(foreign_key="dashboards.id", index=True)
    source_id: UUID = Field(foreign_key="sources.id", index=True)

    # When was this source added to this dashboard
    added_at: datetime = Field(default_factory=datetime.utcnow)

    # Optional: ordering within dashboard
    position: int = Field(default=0)
