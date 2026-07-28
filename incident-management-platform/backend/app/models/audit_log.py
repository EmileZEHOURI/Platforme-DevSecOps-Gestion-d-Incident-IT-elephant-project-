from datetime import datetime
from typing import TYPE_CHECKING, Any

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
    text,
)
from sqlalchemy import (
    Enum as SQLAlchemyEnum,
)
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import AuditResult

if TYPE_CHECKING:
    from app.models.user import User


class AuditLog(Base):
    """Événement sensible enregistré dans le journal d’audit."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(),
        primary_key=True,
    )

    user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
            name="fk_audit_logs_user_id_users",
        ),
        nullable=True,
    )

    event_type: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
    )

    resource_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    resource_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    result: Mapped[AuditResult] = mapped_column(
        SQLAlchemyEnum(
            AuditResult,
            name="audit_result",
            native_enum=True,
            values_callable=lambda enum_class: [member.value for member in enum_class],
        ),
        nullable=False,
    )

    ip_address: Mapped[str | None] = mapped_column(
        INET,
        nullable=True,
    )

    user_agent: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    details: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    user: Mapped["User | None"] = relationship(
        "User",
        back_populates="audit_logs",
    )

    __table_args__ = (
        CheckConstraint(
            "char_length(btrim(event_type)) BETWEEN 1 AND 80",
            name="event_type_length",
        ),
        CheckConstraint(
            """
            resource_type IS NULL
            OR char_length(btrim(resource_type)) BETWEEN 1 AND 50
            """,
            name="resource_type_length",
        ),
    )


Index(
    "ix_audit_logs_created_at",
    AuditLog.created_at.desc(),
)

Index(
    "ix_audit_logs_user_created_at",
    AuditLog.user_id,
    AuditLog.created_at.desc(),
)

Index(
    "ix_audit_logs_event_type",
    AuditLog.event_type,
)
