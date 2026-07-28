from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Identity,
    Index,
    String,
    func,
    text,
)
from sqlalchemy import (
    Enum as SQLAlchemyEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import UserRole

if TYPE_CHECKING:
    from app.models.audit_log import AuditLog
    from app.models.comment import IncidentComment
    from app.models.history import IncidentHistory
    from app.models.incident import Incident


class User(Base):
    """Compte utilisateur de la plateforme."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(),
        primary_key=True,
    )

    email: Mapped[str] = mapped_column(
        String(320),
        nullable=False,
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    full_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    role: Mapped[UserRole] = mapped_column(
        SQLAlchemyEnum(
            UserRole,
            name="user_role",
            native_enum=True,
            values_callable=lambda enum_class: [member.value for member in enum_class],
        ),
        nullable=False,
        default=UserRole.USER,
        server_default=UserRole.USER.value,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
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

    created_incidents: Mapped[list["Incident"]] = relationship(
        "Incident",
        foreign_keys="Incident.created_by_id",
        back_populates="created_by",
    )

    assigned_incidents: Mapped[list["Incident"]] = relationship(
        "Incident",
        foreign_keys="Incident.assigned_to_id",
        back_populates="assigned_to",
    )

    incident_comments: Mapped[list["IncidentComment"]] = relationship(
        "IncidentComment",
        foreign_keys="IncidentComment.author_id",
        back_populates="author",
    )

    incident_history_entries: Mapped[list["IncidentHistory"]] = relationship(
        "IncidentHistory",
        back_populates="actor",
    )

    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog",
        back_populates="user",
    )

    __table_args__ = (
        CheckConstraint(
            "char_length(btrim(full_name)) > 0",
            name="full_name_not_blank",
        ),
        Index(
            "uq_users_email_lower",
            func.lower(email),
            unique=True,
        ),
    )
