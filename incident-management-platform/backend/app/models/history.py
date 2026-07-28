from datetime import datetime
from typing import TYPE_CHECKING

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
from app.models.enums import IncidentHistoryAction

if TYPE_CHECKING:
    from app.models.incident import Incident
    from app.models.user import User


class IncidentHistory(Base):
    """Événement métier enregistré dans l’historique d’un incident."""

    __tablename__ = "incident_history"

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(),
        primary_key=True,
    )

    incident_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "incidents.id",
            ondelete="RESTRICT",
            name="fk_incident_history_incident_id_incidents",
        ),
        nullable=False,
    )

    actor_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
            name="fk_incident_history_actor_id_users",
        ),
        nullable=False,
    )

    action: Mapped[IncidentHistoryAction] = mapped_column(
        SQLAlchemyEnum(
            IncidentHistoryAction,
            name="incident_history_action",
            native_enum=True,
            values_callable=lambda enum_class: [member.value for member in enum_class],
        ),
        nullable=False,
    )

    field_name: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    old_value: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    new_value: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    incident: Mapped["Incident"] = relationship(
        "Incident",
        back_populates="history_entries",
    )

    actor: Mapped["User"] = relationship(
        "User",
        back_populates="incident_history_entries",
    )

    __table_args__ = (
        CheckConstraint(
            """
            field_name IS NULL
            OR char_length(btrim(field_name)) BETWEEN 1 AND 50
            """,
            name="field_name_length",
        ),
    )


Index(
    "ix_incident_history_incident_created_at",
    IncidentHistory.incident_id,
    IncidentHistory.created_at.desc(),
)
