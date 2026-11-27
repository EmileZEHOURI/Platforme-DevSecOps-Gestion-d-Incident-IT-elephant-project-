from app.models.enums import AuditEventType, AuditResult
from app.models.user import User, UserRole
from app.repositories.audit_repository import AuditRepository
from app.repositories.incident_repository import IncidentRepository
from app.repositories.user_repository import UserRepository


class NotEnoughAuthorization(Exception):
    """Not Enough Authorization"""


class UserNotFoundError(Exception):
    """User Not Found"""


class DesactivateAdminError(Exception):
    """Cannot deactivate an administrator"""


class NotEmptyListIncident(Exception):
    """Cannot deactivate a user with assigned incidents"""


class UserService:
    def __init__(
        self,
        user_repository: UserRepository,
        incident_repository: IncidentRepository,
        audit_repository: AuditRepository,
    ) -> None:

        self.user_repository = user_repository
        self.incident_repository = incident_repository
        self.audit_repository = audit_repository

    def list_users(
        self,
        *,
        actor_id: int,
        is_active: bool | None = None,
        role: UserRole | None = None,
    ) -> list[User]:

        actor = self.user_repository.get_by_id(user_id=actor_id)

        if actor is None:
            raise UserNotFoundError("Utilisateur n'existe pas")

        if actor.role is not UserRole.ADMIN:
            raise NotEnoughAuthorization("Rôle d'admin nécessaire")

        return self.user_repository.list_all(is_active=is_active, role=role)

    def user_activation(
        self,
        *,
        actor_id: int,
        target_id: int,
        is_active: bool,
    ) -> User:
        actor = self.user_repository.get_by_id(user_id=actor_id)

        if actor is None:
            raise UserNotFoundError("Utilisateur n'existe pas")

        if actor.role is not UserRole.ADMIN:
            raise NotEnoughAuthorization("Rôle d'admin nécessaire")

        target = self.user_repository.get_by_id(user_id=target_id)

        if target is None:
            raise UserNotFoundError("Utilisateur cible inexistant")

        if target.role is UserRole.ADMIN and is_active is False:
            raise DesactivateAdminError("Impossible de désactiver un administrateur")

        if target.is_active == is_active:
            return target

        if target.role is UserRole.TECHNICIAN and is_active is False:

            active_incident_count = self.incident_repository.count_active_by_assignee(
                assignee_id=target_id
            )

            if active_incident_count > 0:
                raise NotEmptyListIncident(
                    "Incident assigné restant, le compte ne peux pas être désactivé"
                )

        event_type = (
            AuditEventType.USER_ACTIVATED
            if is_active
            else AuditEventType.USER_DEACTIVATED
        )

        updated_user = self.user_repository.update_is_active(
            user=target,
            is_active=is_active,
        )

        self.audit_repository.create(
            event_type=event_type,
            result=AuditResult.SUCCESS,
            user_id=actor_id,
            resource_type="user",
            resource_id=target_id,
        )

        return updated_user
