from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.models.enums import (
    IncidentCategory,
    IncidentHistoryAction,
    IncidentPriority,
    IncidentStatus,
)


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


class IncidentAssignmentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    assigned_to_id: int

class IncidentPriorityUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    priority: IncidentPriority

class IncidentStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: IncidentStatus

class IncidentResolveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resolution: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True,
            min_length=1,
        ),
    ]

class IncidentHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    incident_id: int
    actor_id: int
    action: IncidentHistoryAction
    field_name: str | None
    old_value: str | None
    new_value: str | None
    created_at: datetime