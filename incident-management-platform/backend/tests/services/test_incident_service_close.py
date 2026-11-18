
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.models.enums import (
    AuditEventType,
    AuditResult,
    IncidentCategory,
    IncidentHistoryAction,
    IncidentPriority,
    IncidentStatus,
    UserRole,
)
from app.models.incident import Incident
from app.models.user import User

from app.repositories.incident_repository import IncidentRepository
from app.repositories.incident_history_repository import (
    IncidentHistoryRepository,
)
from app.repositories.audit_repository import AuditRepository
from app.repositories.user_repository import UserRepository

from app.services.incident_service import (
    IncidentService,
    IncidentNotFoundError,
    UserNotFoundError,
    NotEnoughAuthorization,
    IncidentStatusClosedError,
    InvalidStatusTransitionError,
)


# ==========================================================
# HELPER : CONSTRUIRE LE CONTEXTE DE TEST
# ==========================================================


def build_close_context(
    *,
    actor_role: UserRole = UserRole.USER,
    created_by_id: int = 12,
    assigned_to_id: int | None = 99,
    incident_status: IncidentStatus = IncidentStatus.RESOLVED,
    actor_exists: bool = True,
    incident_exists: bool = True,
):
    incident_repository = MagicMock(spec=IncidentRepository)
    incident_history_repository = MagicMock(
        spec=IncidentHistoryRepository
    )
    audit_repository = MagicMock(spec=AuditRepository)
    user_repository = MagicMock(spec=UserRepository)

    actor = User(
        id=12,
        email="actor@example.com",
        password_hash="password_hash",
        full_name="Acteur de test",
        role=actor_role,
        is_active=True,
    )

    # Un incident RESOLVED possède déjà sa résolution
    # et sa date de résolution.
    resolved_at = datetime(
        2026, 1, 10, 14, 30, tzinfo=timezone.utc
    )

    closed_at = datetime(
        2026, 1, 11, 9, 15, tzinfo=timezone.utc
    )

    is_resolved_or_closed = incident_status in (
        IncidentStatus.RESOLVED,
        IncidentStatus.CLOSED,
    )

    incident = Incident(
        id=42,
        title="Incident à clôturer",
        description="Problème de connexion au serveur.",
        category=IncidentCategory.ANOMALY,
        priority=IncidentPriority.MEDIUM,
        status=incident_status,
        created_by_id=created_by_id,
        assigned_to_id=assigned_to_id,
        resolution=(
            "Le service a été redémarré."
            if is_resolved_or_closed
            else None
        ),
        resolved_at=(
            resolved_at if is_resolved_or_closed else None
        ),
        closed_at=(
            closed_at
            if incident_status == IncidentStatus.CLOSED
            else None
        ),
    )

    incident_repository.get_by_id.return_value = (
        incident if incident_exists else None
    )

    user_repository.get_by_id.return_value = (
        actor if actor_exists else None
    )

    service = IncidentService(
        incident_repository,
        incident_history_repository,
        audit_repository,
        user_repository,
    )

    return (
        service,
        incident,
        actor,
        incident_repository,
        user_repository,
        incident_history_repository,
        audit_repository,
    )


# ==========================================================
# HELPER : VÉRIFIER L'ABSENCE DE MODIFICATIONS
# ==========================================================


def assert_no_close_side_effects(
    *,
    incident: Incident,
    old_status: IncidentStatus,
    old_closed_at: datetime | None,
    old_resolution: str | None,
    old_resolved_at: datetime | None,
    old_assignee: int | None,
    old_priority: IncidentPriority,
    incident_history_repository: MagicMock,
    audit_repository: MagicMock,
) -> None:

    assert incident.status == old_status
    assert incident.closed_at == old_closed_at
    assert incident.resolution == old_resolution
    assert incident.resolved_at == old_resolved_at
    assert incident.assigned_to_id == old_assignee
    assert incident.priority == old_priority

    incident_history_repository.create.assert_not_called()
    audit_repository.create.assert_not_called()


# ==========================================================
# 1. CLÔTURE AUTORISÉE : CRÉATEUR OU ADMINISTRATEUR
# ==========================================================


@pytest.mark.parametrize(
    "actor_role, created_by_id",
    [
        pytest.param(
            UserRole.USER,
            12,
            id="user-creator",
        ),
        pytest.param(
            UserRole.ADMIN,
            99,
            id="admin-not-creator",
        ),
        pytest.param(
            UserRole.TECHNICIAN,
            12,
            id="technician-creator",
        ),
    ],
)
def test_authorized_actor_can_close_incident(
    actor_role: UserRole,
    created_by_id: int,
) -> None:

    (
        service,
        incident,
        actor,
        incident_repository,
        user_repository,
        incident_history_repository,
        audit_repository,
    ) = build_close_context(
        actor_role=actor_role,
        created_by_id=created_by_id,
    )

    old_status = incident.status
    old_resolution = incident.resolution
    old_resolved_at = incident.resolved_at
    old_assignee = incident.assigned_to_id
    old_priority = incident.priority
    old_creator = incident.created_by_id

    assert old_status == IncidentStatus.RESOLVED
    assert incident.closed_at is None

    before = datetime.now(timezone.utc)

    result = service.close_incident(
        incident_id=incident.id,
        actor_id=actor.id,
    )

    after = datetime.now(timezone.utc)

    # L'objet retourné est bien l'incident modifié
    assert result is incident

    # Transition RESOLVED -> CLOSED
    assert result.status == IncidentStatus.CLOSED

    # Date de clôture générée en UTC
    assert result.closed_at is not None
    assert result.closed_at.tzinfo is not None
    assert before <= result.closed_at <= after

    # Les données de résolution restent inchangées
    assert result.resolution == old_resolution
    assert result.resolved_at == old_resolved_at

    # Aucune modification des autres propriétés
    assert result.assigned_to_id == old_assignee
    assert result.priority == old_priority
    assert result.created_by_id == old_creator

    # Vérification des appels aux repositories
    incident_repository.get_by_id.assert_called_once_with(
        incident_id=incident.id
    )

    user_repository.get_by_id.assert_called_once_with(
        user_id=actor.id
    )

    # Historique métier
    incident_history_repository.create.assert_called_once_with(
        incident_id=incident.id,
        actor_id=actor.id,
        action=IncidentHistoryAction.CLOSED,
        field_name="status",
        old_value=IncidentStatus.RESOLVED.value,
        new_value=IncidentStatus.CLOSED.value,
    )

    # Audit applicatif
    audit_repository.create.assert_called_once_with(
        event_type=AuditEventType.INCIDENT_CLOSED,
        result=AuditResult.SUCCESS,
        user_id=actor.id,
    )


# ==========================================================
# 2. UTILISATEURS NON AUTORISÉS
# ==========================================================


@pytest.mark.parametrize(
    "actor_role, created_by_id, assigned_to_id",
    [
        pytest.param(
            UserRole.USER,
            99,
            88,
            id="user-not-creator",
        ),
        pytest.param(
            UserRole.TECHNICIAN,
            99,
            12,
            id="technician-assigned-but-not-creator",
        ),
        pytest.param(
            UserRole.TECHNICIAN,
            99,
            88,
            id="technician-not-assigned-not-creator",
        ),
    ],
)
def test_unauthorized_actor_cannot_close_incident(
    actor_role: UserRole,
    created_by_id: int,
    assigned_to_id: int,
) -> None:

    (
        service,
        incident,
        actor,
        incident_repository,
        user_repository,
        incident_history_repository,
        audit_repository,
    ) = build_close_context(
        actor_role=actor_role,
        created_by_id=created_by_id,
        assigned_to_id=assigned_to_id,
    )

    old_status = incident.status
    old_closed_at = incident.closed_at
    old_resolution = incident.resolution
    old_resolved_at = incident.resolved_at
    old_assignee = incident.assigned_to_id
    old_priority = incident.priority

    with pytest.raises(NotEnoughAuthorization):
        service.close_incident(
            incident_id=incident.id,
            actor_id=actor.id,
        )

    assert_no_close_side_effects(
        incident=incident,
        old_status=old_status,
        old_closed_at=old_closed_at,
        old_resolution=old_resolution,
        old_resolved_at=old_resolved_at,
        old_assignee=old_assignee,
        old_priority=old_priority,
        incident_history_repository=incident_history_repository,
        audit_repository=audit_repository,
    )


# ==========================================================
# 3. INCIDENT OPEN OU IN_PROGRESS : TRANSITION INTERDITE
# ==========================================================


@pytest.mark.parametrize(
    "actor_role, created_by_id, incident_status",
    [
        pytest.param(
            UserRole.USER,
            12,
            IncidentStatus.OPEN,
            id="creator-open",
        ),
        pytest.param(
            UserRole.USER,
            12,
            IncidentStatus.IN_PROGRESS,
            id="creator-in-progress",
        ),
        pytest.param(
            UserRole.ADMIN,
            99,
            IncidentStatus.OPEN,
            id="admin-open",
        ),
        pytest.param(
            UserRole.ADMIN,
            99,
            IncidentStatus.IN_PROGRESS,
            id="admin-in-progress",
        ),
    ],
)
def test_cannot_close_incident_before_resolution(
    actor_role: UserRole,
    created_by_id: int,
    incident_status: IncidentStatus,
) -> None:

    (
        service,
        incident,
        actor,
        incident_repository,
        user_repository,
        incident_history_repository,
        audit_repository,
    ) = build_close_context(
        actor_role=actor_role,
        created_by_id=created_by_id,
        incident_status=incident_status,
    )

    old_status = incident.status
    old_closed_at = incident.closed_at
    old_resolution = incident.resolution
    old_resolved_at = incident.resolved_at
    old_assignee = incident.assigned_to_id
    old_priority = incident.priority

    with pytest.raises(InvalidStatusTransitionError):
        service.close_incident(
            incident_id=incident.id,
            actor_id=actor.id,
        )

    assert_no_close_side_effects(
        incident=incident,
        old_status=old_status,
        old_closed_at=old_closed_at,
        old_resolution=old_resolution,
        old_resolved_at=old_resolved_at,
        old_assignee=old_assignee,
        old_priority=old_priority,
        incident_history_repository=incident_history_repository,
        audit_repository=audit_repository,
    )


# ==========================================================
# 4. INCIDENT DÉJÀ CLOSED
# ==========================================================


@pytest.mark.parametrize(
    "actor_role, created_by_id",
    [
        pytest.param(
            UserRole.USER,
            12,
            id="creator-already-closed",
        ),
        pytest.param(
            UserRole.ADMIN,
            99,
            id="admin-already-closed",
        ),
    ],
)
def test_cannot_close_incident_twice(
    actor_role: UserRole,
    created_by_id: int,
) -> None:

    (
        service,
        incident,
        actor,
        incident_repository,
        user_repository,
        incident_history_repository,
        audit_repository,
    ) = build_close_context(
        actor_role=actor_role,
        created_by_id=created_by_id,
        incident_status=IncidentStatus.CLOSED,
    )

    old_status = incident.status
    old_closed_at = incident.closed_at
    old_resolution = incident.resolution
    old_resolved_at = incident.resolved_at
    old_assignee = incident.assigned_to_id
    old_priority = incident.priority

    assert incident.closed_at is not None

    with pytest.raises(IncidentStatusClosedError):
        service.close_incident(
            incident_id=incident.id,
            actor_id=actor.id,
        )

    # La date de clôture précédente ne doit pas être écrasée.
    assert_no_close_side_effects(
        incident=incident,
        old_status=old_status,
        old_closed_at=old_closed_at,
        old_resolution=old_resolution,
        old_resolved_at=old_resolved_at,
        old_assignee=old_assignee,
        old_priority=old_priority,
        incident_history_repository=incident_history_repository,
        audit_repository=audit_repository,
    )


# ==========================================================
# 5. INCIDENT INEXISTANT
# ==========================================================


def test_close_incident_not_found() -> None:

    (
        service,
        incident,
        actor,
        incident_repository,
        user_repository,
        incident_history_repository,
        audit_repository,
    ) = build_close_context(
        incident_exists=False,
    )

    with pytest.raises(IncidentNotFoundError):
        service.close_incident(
            incident_id=9999999,
            actor_id=actor.id,
        )

    incident_repository.get_by_id.assert_called_once_with(
        incident_id=9999999
    )

    user_repository.get_by_id.assert_called_once_with(
        user_id=actor.id
    )

    incident_history_repository.create.assert_not_called()
    audit_repository.create.assert_not_called()


# ==========================================================
# 6. ACTEUR INEXISTANT
# ==========================================================


def test_close_incident_actor_not_found() -> None:

    (
        service,
        incident,
        actor,
        incident_repository,
        user_repository,
        incident_history_repository,
        audit_repository,
    ) = build_close_context(
        actor_exists=False,
    )

    old_status = incident.status
    old_closed_at = incident.closed_at
    old_resolution = incident.resolution
    old_resolved_at = incident.resolved_at
    old_assignee = incident.assigned_to_id
    old_priority = incident.priority

    with pytest.raises(UserNotFoundError):
        service.close_incident(
            incident_id=incident.id,
            actor_id=9999999,
        )

    incident_repository.get_by_id.assert_called_once_with(
        incident_id=incident.id
    )

    user_repository.get_by_id.assert_called_once_with(
        user_id=9999999
    )

    assert_no_close_side_effects(
        incident=incident,
        old_status=old_status,
        old_closed_at=old_closed_at,
        old_resolution=old_resolution,
        old_resolved_at=old_resolved_at,
        old_assignee=old_assignee,
        old_priority=old_priority,
        incident_history_repository=incident_history_repository,
        audit_repository=audit_repository,
    )
