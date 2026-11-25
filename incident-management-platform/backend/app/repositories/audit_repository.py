from datetime import datetime
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.enums import AuditEventType, AuditResult


class AuditRepository:
    """Accès aux journaux d'audit."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        event_type: AuditEventType,
        result: AuditResult,
        user_id: int | None = None,
        resource_type: str | None = None,
        resource_id: int | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuditLog:
        """Ajoute un événement d'audit à la transaction."""

        audit_log = AuditLog(
            user_id=user_id,
            event_type=event_type.value,
            result=result,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details or {},
        )

        self.db.add(audit_log)
        self.db.flush()

        return audit_log

    def get_by_id(self, user_id: int) -> AuditLog | None:
        """Recherche un utilisateur par sa clé primaire."""

        return self.db.get(AuditLog, user_id)

    def list_all(
        self,
        *,
        user_id: int | None = None,
        event_type: AuditEventType | None = None,
        result: AuditResult | None = None,
        limit: int | None = None,
        offset: int = 0,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> list[AuditLog]:

        statement = select(AuditLog)

        statement = self._apply_filters(
            statement,
            user_id=user_id,
            event_type=event_type,
            result=result,
            date_from=date_from,
            date_to=date_to,
        )

        statement = statement.order_by(
            AuditLog.created_at.desc(),
            AuditLog.id.desc(),
        )

        if limit is not None:
            statement = statement.limit(limit)

        statement = statement.offset(offset)

        return list(self.db.scalars(statement).all())

    def count_all(
        self,
        *,
        user_id: int | None = None,
        event_type: AuditEventType | None = None,
        result: AuditResult | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> int:
        statement = select(AuditLog)

        statement = self._apply_filters(
            statement,
            user_id=user_id,
            event_type=event_type,
            result=result,
            date_from=date_from,
            date_to=date_to,
        )

        statement = statement.with_only_columns(
            func.count(AuditLog.id),
            maintain_column_froms=True,
        )

        return self.db.scalar(statement) or 0

    def _apply_filters(
        self,
        statement: Select[tuple[AuditLog]],
        *,
        user_id: int | None = None,
        event_type: AuditEventType | None = None,
        result: AuditResult | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> Select[tuple[AuditLog]]:

        if event_type is not None:
            statement = statement.where(AuditLog.event_type == event_type.value)

        if result is not None:
            statement = statement.where(AuditLog.result == result)

        if user_id is not None:
            statement = statement.where(AuditLog.user_id == user_id)

        if date_from is not None:
            statement = statement.where(AuditLog.created_at >= date_from)

        if date_to is not None:
            statement = statement.where(AuditLog.created_at <= date_to)

        return statement
