from datetime import UTC, datetime

from app.models.enums import (
    AuditEventType,
    AuditResult,
    IncidentCategory,
    IncidentHistoryAction,
    IncidentPriority,
    IncidentStatus,
    UserRole,
)
from app.models.history import IncidentHistory
from app.models.incident import Incident
from app.repositories.audit_repository import AuditRepository
from app.repositories.incident_history_repository import IncidentHistoryRepository
from app.repositories.incident_repository import IncidentRepository
from app.repositories.user_repository import UserRepository
from app.schemas.incident import IncidentCreate


class IncidentNotFoundError(Exception):
    """Incident Not Found"""


class IncidentStatusClosedError(Exception):
    """Incident Closed"""


class NotEnoughAuthorization(Exception):
    """Not Enough Authorization"""


class UserNotFoundError(Exception):
    """User Not Found"""


class PaginationError(Exception):
    """Invalid pagination parameters"""


class UserInactiveError(Exception):
    """User Inactive"""


class InvalidAssignmentTargetError(Exception):
    """Interdit"""


class IncidentWithoutAssignmentError(Exception):
    """Incident Without Assignment"""


class IncidentStatusResolvedError(Exception):
    """Incident Resolved"""


class IncidentResolutionIsEmpty(Exception):
    """Incident Resolution Is Empty"""


class InvalidStatusTransitionError(Exception):
    """Incident Status Transition Invalid"""


class IncidentService:
    def __init__(
        self,
        incident_repository: IncidentRepository,
        incident_history_repository: IncidentHistoryRepository,
        audit_repository: AuditRepository,
        user_repository: UserRepository,
    ) -> None:
        self.incident_repository = incident_repository
        self.incident_history_repository = incident_history_repository
        self.audit_repository = audit_repository
        self.user_repository = user_repository

    def create_incident(
        self,
        data: IncidentCreate,
        created_by_id: int,
    ) -> Incident:
        incident = self.incident_repository.create(
            data=data,
            created_by_id=created_by_id,
        )
        self.incident_history_repository.create(
            incident_id=incident.id,
            actor_id=created_by_id,
            action=IncidentHistoryAction.INCIDENT_CREATED,
        )
        self.audit_repository.create(
            event_type=AuditEventType.INCIDENT_CREATED,
            result=AuditResult.SUCCESS,
            user_id=created_by_id,
            resource_type="incident",
            resource_id=incident.id,
        )
        return incident

    def list_user_incidents(
        self,
        created_by_id: int,
    ) -> list[Incident]:

        return self.incident_repository.list_by_creator(created_by_id=created_by_id)

    def get_incident_detail(
        self,
        *,
        incident_id: int,
        actor_id: int,
    ) -> Incident:
        actor = self.user_repository.get_by_id(user_id=actor_id)

        if actor is None:
            raise UserNotFoundError("Utilisateur introuvable")

        if not actor.is_active:
            raise UserInactiveError("Utilisateur désactivé")

        incident = self.incident_repository.get_by_id(incident_id=incident_id)

        if incident is None:
            raise IncidentNotFoundError("Incident introuvable")

        is_creator = incident.created_by_id == actor_id

        is_assigned_technician = (
            actor.role is UserRole.TECHNICIAN and incident.assigned_to_id == actor_id
        )

        is_admin = actor.role is UserRole.ADMIN

        if not (is_creator or is_assigned_technician or is_admin):
            raise IncidentNotFoundError("Incident introuvable")

        return incident

    def assign_incident(
        self,
        incident_id: int,
        assigned_to_id: int,
        actor_id: int,
    ) -> Incident:
        incident = self.incident_repository.get_by_id(incident_id=incident_id)
        actor = self.user_repository.get_by_id(user_id=actor_id)
        assigned_user = self.user_repository.get_by_id(user_id=assigned_to_id)

        if incident is None:
            raise IncidentNotFoundError("L'incident n'existe pas")

        if incident.status is IncidentStatus.CLOSED:
            raise IncidentStatusClosedError("L'incident est fermé")

        if actor is None:
            raise UserNotFoundError("Utilisateur n'existe pas")

        if actor.role is not UserRole.ADMIN:
            raise NotEnoughAuthorization("Rôle d'admin nécessaire")

        if assigned_user is None:
            raise UserNotFoundError("Utilisateur assigné n'existe pas")

        if not assigned_user.is_active:
            raise UserInactiveError("Utilisateur Inactif")

        is_technician = assigned_user.role == UserRole.TECHNICIAN

        is_admin_assigning_self = (
            assigned_user.role == UserRole.ADMIN and assigned_user.id == actor.id
        )

        if not is_technician and not is_admin_assigning_self:
            raise InvalidAssignmentTargetError("Interdit")

        old_assigned_to_id = incident.assigned_to_id

        # Aucun changement si l'incident est déjà assigné à cet utilisateur
        if old_assigned_to_id == assigned_to_id:
            return incident

        # Déterminer s'il s'agit d'une assignation ou d'une réassignation
        if old_assigned_to_id is None:
            action = IncidentHistoryAction.ASSIGNED
            audit_event = AuditEventType.INCIDENT_ASSIGNED
        else:
            action = IncidentHistoryAction.REASSIGNED
            audit_event = AuditEventType.INCIDENT_REASSIGNED

        # Modifier l'incident
        incident.assigned_to_id = assigned_to_id

        # Enregistrer l'action dans l'historique
        self.incident_history_repository.create(
            incident_id=incident.id,
            actor_id=actor_id,
            action=action,
            field_name="assigned_to_id",
            old_value=(
                str(old_assigned_to_id) if old_assigned_to_id is not None else None
            ),
            new_value=str(assigned_to_id),
        )

        self.audit_repository.create(
            event_type=audit_event, result=AuditResult.SUCCESS, user_id=actor_id
        )

        return incident

    def change_priority(
        self,
        *,
        incident_id: int,
        new_priority: IncidentPriority,
        actor_id: int,
    ) -> Incident:

        incident = self.incident_repository.get_by_id(incident_id=incident_id)
        actor = self.user_repository.get_by_id(user_id=actor_id)

        if actor is None:
            raise UserNotFoundError("Utilisateur n'existe pas")

        if actor.role is not UserRole.ADMIN:
            raise NotEnoughAuthorization("Rôle d'admin nécessaire")

        if incident is None:
            raise IncidentNotFoundError("L'incident n'existe pas")

        if incident.status is IncidentStatus.CLOSED:
            raise IncidentStatusClosedError("L'incident est fermé")

        if incident.priority == new_priority:
            return incident

        old_priority_value = incident.priority

        incident.priority = new_priority

        # Enregistrer l'action dans l'historique
        self.incident_history_repository.create(
            incident_id=incident.id,
            actor_id=actor_id,
            action=IncidentHistoryAction.PRIORITY_CHANGED,
            field_name="priority",
            old_value=(old_priority_value.value),
            new_value=incident.priority.value,
        )

        self.audit_repository.create(
            event_type=AuditEventType.INCIDENT_PRIORITY_CHANGED,
            result=AuditResult.SUCCESS,
            user_id=actor_id,
        )

        return incident

    def change_status(
        self,
        *,
        incident_id: int,
        new_status: IncidentStatus,
        actor_id: int,
    ) -> Incident:

        incident = self.incident_repository.get_by_id(incident_id=incident_id)
        actor = self.user_repository.get_by_id(user_id=actor_id)

        if actor is None:
            raise UserNotFoundError("Utilisateur n'existe pas")

        if actor.role is not UserRole.ADMIN and actor.role is not UserRole.TECHNICIAN:
            raise NotEnoughAuthorization("Rôle d'admin ou technicien nécessaire")

        if incident is None:
            raise IncidentNotFoundError("L'incident n'existe pas")

        if incident.status is IncidentStatus.RESOLVED:
            raise IncidentStatusResolvedError("L'incident est déjà résolue")

        if incident.assigned_to_id is None:
            raise IncidentWithoutAssignmentError("L'incident n'est pas assigné")

        if incident.assigned_to_id != actor.id:
            raise NotEnoughAuthorization("Vous n'êtes pas responsable de cet incident")

        if incident.status is IncidentStatus.CLOSED:
            raise IncidentStatusClosedError("L'incident est fermé")

        if (
            incident.status == IncidentStatus.IN_PROGRESS
            and new_status == IncidentStatus.IN_PROGRESS
        ):
            return incident
        if (
            incident.status != IncidentStatus.OPEN
            or new_status != IncidentStatus.IN_PROGRESS
        ):
            raise InvalidStatusTransitionError("Transition du status invalide")

        old_status_value = incident.status

        incident.status = new_status

        # Enregistrer l'action dans l'historique
        self.incident_history_repository.create(
            incident_id=incident.id,
            actor_id=actor_id,
            action=IncidentHistoryAction.STATUS_CHANGED,
            field_name="status",
            old_value=(old_status_value.value),
            new_value=new_status.value,
        )

        self.audit_repository.create(
            event_type=AuditEventType.INCIDENT_STATUS_CHANGED,
            result=AuditResult.SUCCESS,
            user_id=actor_id,
        )

        return incident

    def resolve_incident(
        self,
        *,
        incident_id: int,
        resolution: str,
        actor_id: int,
    ) -> Incident:
        incident = self.incident_repository.get_by_id(incident_id=incident_id)
        actor = self.user_repository.get_by_id(user_id=actor_id)

        if actor is None:
            raise UserNotFoundError("Utilisateur n'existe pas")

        if actor.role not in (UserRole.TECHNICIAN, UserRole.ADMIN):
            raise NotEnoughAuthorization(
                "Rôle de technicien ou administrateur nécessaire"
            )

        if incident is None:
            raise IncidentNotFoundError("L'incident n'existe pas")

        if incident.assigned_to_id is None:
            raise IncidentWithoutAssignmentError("L'incident n'est pas assigné")

        if incident.status is IncidentStatus.RESOLVED:
            raise IncidentStatusResolvedError("L'incident est déjà résolue")

        if incident.status is IncidentStatus.CLOSED:
            raise IncidentStatusClosedError("L'incident est fermé")

        if incident.assigned_to_id != actor.id:
            raise NotEnoughAuthorization("Vous n'êtes pas responsable de cet incident")

        if incident.status is not IncidentStatus.IN_PROGRESS:
            raise InvalidStatusTransitionError(
                "L'incident ne peux transitionner qu'à partir d'IN_PROGRESS"
            )

        resolution_validate = resolution.strip()

        if not resolution_validate:
            raise IncidentResolutionIsEmpty("la description est vide")

        old_status = incident.status

        incident.status = IncidentStatus.RESOLVED
        incident.resolution = resolution_validate
        incident.resolved_at = datetime.now(UTC)

        self.incident_history_repository.create(
            incident_id=incident.id,
            actor_id=actor_id,
            action=IncidentHistoryAction.RESOLVED,
            field_name="status",
            old_value=old_status.value,
            new_value="RESOLVED",
        )

        self.audit_repository.create(
            event_type=AuditEventType.INCIDENT_RESOLVED,
            result=AuditResult.SUCCESS,
            user_id=actor_id,
        )

        return incident

    def close_incident(
        self,
        *,
        incident_id: int,
        actor_id: int,
    ) -> Incident:

        incident = self.incident_repository.get_by_id(incident_id=incident_id)
        actor = self.user_repository.get_by_id(user_id=actor_id)

        if actor is None:
            raise UserNotFoundError("Utilisateur n'existe pas")

        if incident is None:
            raise IncidentNotFoundError("L'incident n'existe pas")

        if actor.role != UserRole.ADMIN and actor.id != incident.created_by_id:
            raise NotEnoughAuthorization(
                "Vous n'êtes pas autorisé à clôturer cet incident."
            )

        if incident.status is IncidentStatus.CLOSED:
            raise IncidentStatusClosedError("L'incident est déjà fermé")

        if incident.status is not IncidentStatus.RESOLVED:
            raise InvalidStatusTransitionError(
                "Seul un incident résolu peut être clôturé"
            )

        old_status = incident.status

        incident.status = IncidentStatus.CLOSED
        incident.closed_at = datetime.now(UTC)

        self.incident_history_repository.create(
            incident_id=incident.id,
            actor_id=actor_id,
            action=IncidentHistoryAction.CLOSED,
            field_name="status",
            old_value=old_status.value,
            new_value="CLOSED",
        )

        self.audit_repository.create(
            event_type=AuditEventType.INCIDENT_CLOSED,
            result=AuditResult.SUCCESS,
            user_id=actor_id,
        )

        return incident

    def list_incident_history(
        self,
        *,
        incident_id: int,
        actor_id: int,
    ) -> list[IncidentHistory]:

        incident = self.incident_repository.get_by_id(incident_id=incident_id)
        actor = self.user_repository.get_by_id(user_id=actor_id)

        if actor is None:
            raise UserNotFoundError("Utilisateur n'existe pas")

        if incident is None:
            raise IncidentNotFoundError("L'incident n'existe pas")

        is_admin = actor.role == UserRole.ADMIN

        is_creator = actor.id == incident.created_by_id

        is_assigned_technician = (
            actor.role == UserRole.TECHNICIAN and actor.id == incident.assigned_to_id
        )

        if not (is_admin or is_creator or is_assigned_technician):
            raise NotEnoughAuthorization(
                "Vous n'êtes pas autorisé à consulter l'historique de cet incident."
            )

        return self.incident_history_repository.list_by_incident(
            incident_id=incident_id
        )

    def list_assigned_incidents(
        self,
        *,
        actor_id: int,
        status: IncidentStatus | None = None,
        priority: IncidentPriority | None = None,
        category: IncidentCategory | None = None,
    ) -> list[Incident]:

        actor = self.user_repository.get_by_id(user_id=actor_id)

        if actor is None:
            raise UserNotFoundError("Utilisateur n'existe pas")

        if actor.role not in (UserRole.ADMIN, UserRole.TECHNICIAN):
            raise NotEnoughAuthorization(
                "Vous n'êtes pas autorisé à consulter cette liste d'incidents."
            )

        return self.incident_repository.list_by_assignee(
            assignee_id=actor_id,
            status=status,
            category=category,
            priority=priority,
        )

    def list_all_incidents(
        self,
        *,
        actor_id: int,
        status: IncidentStatus | None = None,
        priority: IncidentPriority | None = None,
        category: IncidentCategory | None = None,
    ) -> list[Incident]:

        actor = self.user_repository.get_by_id(user_id=actor_id)

        if actor is None:
            raise UserNotFoundError("Utilisateur n'existe pas")

        if actor.role != UserRole.ADMIN:
            raise NotEnoughAuthorization(
                "Vous n'êtes pas autorisé à consulter cette liste d'incident."
            )

        return self.incident_repository.list_all(
            status=status,
            category=category,
            priority=priority,
        )

    def paginate_assigned_incidents(
        self,
        *,
        actor_id: int,
        page: int = 1,
        page_size: int = 20,
        status: IncidentStatus | None = None,
        priority: IncidentPriority | None = None,
        category: IncidentCategory | None = None,
    ):
        actor = self.user_repository.get_by_id(user_id=actor_id)

        if actor is None:
            raise UserNotFoundError("Utilisateur n'existe pas")

        if actor.role not in (UserRole.ADMIN, UserRole.TECHNICIAN):
            raise NotEnoughAuthorization(
                "Vous n'êtes pas autorisé à consulter cette liste d'incidents."
            )

        if page < 1 or page_size < 1 or page_size > 100:
            raise PaginationError("Erreur concernant la page")

        total = self.incident_repository.count_by_assignee(
            assignee_id=actor_id, status=status, priority=priority, category=category
        )

        total_pages = (total + page_size - 1) // page_size

        incidents = self.incident_repository.list_by_assignee(
            limit=page_size,
            offset=(page - 1) * page_size,
            assignee_id=actor_id,
            status=status,
            priority=priority,
            category=category,
        )

        return {
            "items": incidents,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1,
        }

    def paginate_all_incidents(
        self,
        *,
        actor_id: int,
        page: int = 1,
        page_size: int = 20,
        status: IncidentStatus | None = None,
        priority: IncidentPriority | None = None,
        category: IncidentCategory | None = None,
    ):
        actor = self.user_repository.get_by_id(user_id=actor_id)

        if actor is None:
            raise UserNotFoundError("Utilisateur n'existe pas")

        if actor.role is not UserRole.ADMIN:
            raise NotEnoughAuthorization(
                "Vous n'êtes pas autorisé à consulter cette liste d'incidents."
            )

        if page < 1 or page_size < 1 or page_size > 100:
            raise PaginationError("Erreur concernant la page")

        total = self.incident_repository.count_all(
            status=status, priority=priority, category=category
        )

        total_pages = (total + page_size - 1) // page_size

        incidents = self.incident_repository.list_all(
            limit=page_size,
            offset=(page - 1) * page_size,
            status=status,
            priority=priority,
            category=category,
        )

        return {
            "items": incidents,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1,
        }
