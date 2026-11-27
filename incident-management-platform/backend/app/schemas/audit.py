
from datetime import datetime
from ipaddress import IPv4Address, IPv6Address
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.enums import AuditResult


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    @field_validator("ip_address", mode="before")
    @classmethod
    def normalize_ip_address(cls, value: object) -> object:
        if isinstance(value, (IPv4Address, IPv6Address)):
            return str(value)

        return value

    id: int
    user_id: int | None
    event_type: str
    resource_type: str | None
    resource_id: int | None
    result: AuditResult
    ip_address: str | None
    user_agent: str | None
    details: dict[str, Any]
    created_at: datetime


class PaginatedAuditLogsResponse(BaseModel):
    items: list[AuditLogResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool
