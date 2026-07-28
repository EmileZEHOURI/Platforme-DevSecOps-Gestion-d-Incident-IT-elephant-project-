from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy import (
    Enum as SQLAlchemyEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import (
    IncidentCategory,
    IncidentPriority,
    IncidentStatus,
)

if TYPE_CHECKING:
    from app.models.comment import IncidentComment
    from app.models.history import IncidentHistory
    from app.models.user import User


def generate_incident_reference() -> str:
    """Génère une référence métier unique et lisible."""

    return f"INC-{uuid4().hex[:12].upper()}"


class Incident(Base):
    """Incident informatique ou de sécurité déclaré sur la plateforme."""

    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(),
        primary_key=True,
    )

    reference: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        unique=True,
        default=generate_incident_reference,
    )

    title: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    category: Mapped[IncidentCategory] = mapped_column(
        SQLAlchemyEnum(
            IncidentCategory,
            name="incident_category",
            native_enum=True,
            values_callable=lambda enum_class: [member.value for member in enum_class],
        ),
        nullable=False,
    )

    priority: Mapped[IncidentPriority] = mapped_column(
        SQLAlchemyEnum(
            IncidentPriority,
            name="incident_priority",
            native_enum=True,
            values_callable=lambda enum_class: [member.value for member in enum_class],
        ),
        nullable=False,
        default=IncidentPriority.MEDIUM,
        server_default=IncidentPriority.MEDIUM.value,
    )

    status: Mapped[IncidentStatus] = mapped_column(
        SQLAlchemyEnum(
            IncidentStatus,
            name="incident_status",
            native_enum=True,
            values_callable=lambda enum_class: [member.value for member in enum_class],
        ),
        nullable=False,
        default=IncidentStatus.OPEN,
        server_default=IncidentStatus.OPEN.value,
    )

    created_by_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
            name="fk_incidents_created_by_id_users",
        ),
        nullable=False,
    )

    assigned_to_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
            name="fk_incidents_assigned_to_id_users",
        ),
        nullable=True,
    )

    resolution: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_by: Mapped["User"] = relationship(
        "User",
        foreign_keys=[created_by_id],
        back_populates="created_incidents",
    )

    assigned_to: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[assigned_to_id],
        back_populates="assigned_incidents",
    )

    comments: Mapped[list["IncidentComment"]] = relationship(
        "IncidentComment",
        back_populates="incident",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    history_entries: Mapped[list["IncidentHistory"]] = relationship(
        "IncidentHistory",
        back_populates="incident",
        order_by="IncidentHistory.created_at.desc()",
    )

    __table_args__ = (
        CheckConstraint(
            "char_length(btrim(title)) BETWEEN 5 AND 150",
            name="title_length",
        ),
        CheckConstraint(
            "char_length(btrim(description)) BETWEEN 10 AND 5000",
            name="description_length",
        ),
        CheckConstraint(
            """
            resolution IS NULL
            OR char_length(btrim(resolution)) BETWEEN 1 AND 5000
            """,
            name="resolution_length",
        ),
        CheckConstraint(
            """
            status = 'OPEN'
            OR assigned_to_id IS NOT NULL
            """,
            name="assignment_before_processing",
        ),
        CheckConstraint(
            """
            (
                status IN ('OPEN', 'IN_PROGRESS')
                AND resolution IS NULL
                AND resolved_at IS NULL
                AND closed_at IS NULL
            )
            OR
            (
                status = 'RESOLVED'
                AND resolution IS NOT NULL
                AND char_length(btrim(resolution)) > 0
                AND resolved_at IS NOT NULL
                AND closed_at IS NULL
            )
            OR
            (
                status = 'CLOSED'
                AND resolution IS NOT NULL
                AND char_length(btrim(resolution)) > 0
                AND resolved_at IS NOT NULL
                AND closed_at IS NOT NULL
            )
            """,
            name="status_dates",
        ),
        CheckConstraint(
            """
            resolved_at IS NULL
            OR resolved_at >= created_at
            """,
            name="resolved_after_creation",
        ),
        CheckConstraint(
            """
            closed_at IS NULL
            OR (
                resolved_at IS NOT NULL
                AND closed_at >= resolved_at
            )
            """,
            name="closed_after_resolution",
        ),
    )


Index(
    "ix_incidents_created_by_created_at",
    Incident.created_by_id,
    Incident.created_at.desc(),
)

Index(
    "ix_incidents_assigned_status_priority",
    Incident.assigned_to_id,
    Incident.status,
    Incident.priority.desc(),
    Incident.created_at.asc(),
)
