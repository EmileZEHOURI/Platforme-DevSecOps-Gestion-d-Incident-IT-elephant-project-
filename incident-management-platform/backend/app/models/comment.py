from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.incident import Incident
    from app.models.user import User
    from app.models.history import IncidentHistory
    from app.models.audit_log import AuditLog


class IncidentComment(Base):
    """Commentaire ajouté à un incident."""

    __tablename__ = "incident_comments"

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(),
        primary_key=True,
    )

    incident_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "incidents.id",
            ondelete="CASCADE",
            name="fk_incident_comments_incident_id_incidents",
        ),
        nullable=False,
    )

    author_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
            name="fk_incident_comments_author_id_users",
        ),
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
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

    incident: Mapped["Incident"] = relationship(
        "Incident",
        back_populates="comments",
    )

    author: Mapped["User"] = relationship(
        "User",
        back_populates="incident_comments",
    )

    __table_args__ = (
        CheckConstraint(
            "char_length(btrim(content)) BETWEEN 1 AND 5000",
            name="content_length",
        ),
        Index(
            "ix_incident_comments_incident_created_at",
            "incident_id",
            "created_at",
        ),
    )