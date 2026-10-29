from typing import Any

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
