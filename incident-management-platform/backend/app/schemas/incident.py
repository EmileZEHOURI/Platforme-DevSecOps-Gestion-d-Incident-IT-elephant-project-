from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import IncidentCategory, IncidentPriority, IncidentStatus


class IncidentCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    title: str = Field(
        min_length=5,
        max_length=150,
    )

    description: str = Field(
        min_length=10,
        max_length=5000,
    )

    category: IncidentCategory

    priority: IncidentPriority = IncidentPriority.MEDIUM


class IncidentResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    reference: str
    category: IncidentCategory
    priority: IncidentPriority
    status: IncidentStatus
    created_by_id: int
    created_at: datetime
    title: str = Field(
        min_length=5,
        max_length=150,
    )

    description: str = Field(
        min_length=10,
        max_length=5000,
    )
    assigned_to_id: int | None
    resolution: str | None
    updated_at: datetime
    resolved_at: datetime | None
    closed_at: datetime | None
