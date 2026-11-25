from datetime import datetime

from app.repositories.audit_repository import AuditRepository
from app.repositories.user_repository import UserRepository
from app.models.enums import AuditEventType, AuditResult, UserRole

from app.services.user_service import (
    NotEnoughAuthorization,
    UserNotFoundError,
)

from app.services.incident_service import (
    PaginationError,
)


class InvalidAuditDateRangeError(Exception):
    pass


class AuditService:
    def __init__(
        self, audit_repository: AuditRepository, user_repository: UserRepository
    ) -> None:

        self.audit_repository = audit_repository
        self.user_repository = user_repository

    def paginate_audit_logs(
        self,
        *,
        actor_id: int,
        page: int = 1,
        page_size: int = 20,
        user_id: int | None = None,
        event_type: AuditEventType | None = None,
        result: AuditResult | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> dict:
        actor = self.user_repository.get_by_id(user_id=actor_id)

        if actor is None:
            raise UserNotFoundError("Utilisateur n'existe pas")

        if actor.role is not UserRole.ADMIN:
            raise NotEnoughAuthorization(
                "Vous n'êtes pas autorisé à consulter cette liste d'incidents."
            )

        if page < 1 or page_size < 1 or page_size > 100:
            raise PaginationError("Erreur concernant la page")

        if date_from is not None and date_to is not None and date_from > date_to:
            raise InvalidAuditDateRangeError(
                "La date de début ne peut pas être postérieure à la date de fin"
            )

        total = self.audit_repository.count_all(
            user_id=user_id,
            event_type=event_type,
            result=result,
            date_from=date_from,
            date_to=date_to,
        )

        total_pages = (total + page_size - 1) // page_size

        audit_logs = self.audit_repository.list_all(
            limit=page_size,
            offset=(page - 1) * page_size,
            user_id=user_id,
            event_type=event_type,
            result=result,
            date_from=date_from,
            date_to=date_to,
        )

        return {
            "items": audit_logs,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1,
        }
