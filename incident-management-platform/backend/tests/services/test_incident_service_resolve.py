
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
from app.repositories.incident_history_repository import IncidentHistoryRepository
from app.repositories.audit_repository import AuditRepository
from app.repositories.user_repository import UserRepository

from app.services.incident_service import (
    IncidentService,
    IncidentNotFoundError,
    UserNotFoundError,
    NotEnoughAuthorization,
    IncidentWithoutAssignmentError,
    IncidentStatusClosedError,
    IncidentStatusResolvedError,
    InvalidStatusTransitionError,
    IncidentResolutionIsEmpty,
)


# ==========================================================
# HELPER : CONSTRUIRE LE CONTEXTE DE TEST
# ==========================================================


def build_resolve_context(
    *,
    actor_role: UserRole = UserRole.TECHNICIAN,
    incident_status: IncidentStatus = IncidentStatus.IN_PROGRESS,
    assigned_to_id: int | None = 12,
    incident_exists: bool = True,
    actor_exists: bool = True,
):
    incident_repository = MagicMock(spec=IncidentRepository)
    incident_history_repository = MagicMock(spec=IncidentHistoryRepository)
    audit_repository = MagicMock(spec=AuditRepository)
    user_repository = MagicMock(spec=UserRepository)

    actor = User(
        id=12,
        email="actor@gmail.com",
        password_hash="password_hash",
        full_name="SYLLA",
        role=actor_role,
        is_active=True,
    )

    incident = Incident(
        id=42,
        title="Incident à résoudre",
        description="Un incident nécessitant une correction.",
        category=IncidentCategory.ANOMALY,
        priority=IncidentPriority.MEDIUM,
        status=incident_status,
        created_by_id=10,
        assigned_to_id=assigned_to_id,
        resolution=None,
        resolved_at=None,
        closed_at=None,
    )

    # Préparer des données cohérentes pour les incidents
    # déjà résolus ou fermés.
    if incident_status in (
        IncidentStatus.RESOLVED,
        IncidentStatus.CLOSED,
    ):
        incident.resolution = "Incident déjà corrigé"
        incident.resolved_at = datetime(
            2026, 1, 1, tzinfo=timezone.utc
        )

        if incident_status == IncidentStatus.CLOSED:
            incident.closed_at = datetime(
                2026, 1, 2, tzinfo=timezone.utc
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
# 1. TECHNICIAN ET ADMIN RESPONSABLES : RÉSOLUTION OK
# ==========================================================


@pytest.mark.parametrize(
    "actor_role",
    [
        pytest.param(
            UserRole.TECHNICIAN,
            id="technician-assigned",
        ),
        pytest.param(
            UserRole.ADMIN,
            id="admin-self-assigned",
        ),
    ],
)
def test_assigned_actor_can_resolve_incident(
    actor_role: UserRole,
) -> None:
    (
        service,
        incident,
        actor,
        incident_repository,
        user_repository,
        incident_history_repository,
        audit_repository,
    ) = build_resolve_context(
        actor_role=actor_role,
    )

    old_status = incident.status
    old_priority = incident.priority
    old_assignee = incident.assigned_to_id

    assert old_status == IncidentStatus.IN_PROGRESS
    assert incident.resolution is None
    assert incident.resolved_at is None

    before = datetime.now(timezone.utc)

    result = service.resolve_incident(
        incident_id=incident.id,
        resolution="  Redémarrage du serveur et correction du bug.  ",
        actor_id=actor.id,
    )

    after = datetime.now(timezone.utc)

    # L'objet retourné est bien celui qui a été modifié
    assert result is incident

    # Statut
    assert result.status == IncidentStatus.RESOLVED

    # Description de résolution nettoyée
    assert (
        result.resolution
        == "Redémarrage du serveur et correction du bug."
    )

    # Date de résolution générée côté backend
    assert result.resolved_at is not None
    assert result.resolved_at.tzinfo is not None
    assert before <= result.resolved_at <= after

    # La résolution ne doit pas fermer l'incident
    assert result.closed_at is None

    # Les autres propriétés restent inchangées
    assert result.priority == old_priority
    assert result.assigned_to_id == old_assignee

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
        action=IncidentHistoryAction.RESOLVED,
        field_name="status",
        old_value=IncidentStatus.IN_PROGRESS.value,
        new_value=IncidentStatus.RESOLVED.value,
    )

    # Audit
    audit_repository.create.assert_called_once_with(
        event_type=AuditEventType.INCIDENT_RESOLVED,
        result=AuditResult.SUCCESS,
        user_id=actor.id,
    )


# ==========================================================
# 2. DESCRIPTION VIDE OU COMPOSÉE D'ESPACES
# ==========================================================


@pytest.mark.parametrize(
    "resolution",
    [
        pytest.param(
            "",
            id="empty-string",
        ),
        pytest.param(
            "     ",
            id="spaces-only",
        ),
        pytest.param(
            "\n\t  ",
            id="whitespace-only",
        ),
    ],
)
def test_resolve_incident_empty_resolution(
    resolution: str,
) -> None:
    (
        service,
        incident,
        actor,
        incident_repository,
        user_repository,
        incident_history_repository,
        audit_repository,
    ) = build_resolve_context()

    with pytest.raises(IncidentResolutionIsEmpty):
        service.resolve_incident(
            incident_id=incident.id,
            resolution=resolution,
            actor_id=actor.id,
        )

    # L'incident ne doit pas avoir été modifié
    assert incident.status == IncidentStatus.IN_PROGRESS
    assert incident.resolution is None
    assert incident.resolved_at is None
    assert incident.closed_at is None

    incident_repository.get_by_id.assert_called_once_with(
        incident_id=incident.id
    )

    user_repository.get_by_id.assert_called_once_with(
        user_id=actor.id
    )

    # Aucun effet secondaire
    incident_history_repository.create.assert_not_called()
    audit_repository.create.assert_not_called()


# ==========================================================
# 3. SCÉNARIOS DE REFUS
# ==========================================================


@pytest.mark.parametrize(
    "actor_role, assigned_to_id, incident_status, expected_error",
    [
        pytest.param(
            UserRole.USER,
            12,
            IncidentStatus.IN_PROGRESS,
            NotEnoughAuthorization,
            id="user-forbidden",
        ),
        pytest.param(
            UserRole.TECHNICIAN,
            99,
            IncidentStatus.IN_PROGRESS,
            NotEnoughAuthorization,
            id="technician-not-responsible",
        ),
        pytest.param(
            UserRole.ADMIN,
            99,
            IncidentStatus.IN_PROGRESS,
            NotEnoughAuthorization,
            id="admin-not-responsible",
        ),
        pytest.param(
            UserRole.TECHNICIAN,
            None,
            IncidentStatus.IN_PROGRESS,
            IncidentWithoutAssignmentError,
            id="incident-without-assignment",
        ),
        pytest.param(
            UserRole.TECHNICIAN,
            12,
            IncidentStatus.OPEN,
            InvalidStatusTransitionError,
            id="incident-open",
        ),
        pytest.param(
            UserRole.TECHNICIAN,
            12,
            IncidentStatus.RESOLVED,
            IncidentStatusResolvedError,
            id="incident-already-resolved",
        ),
        pytest.param(
            UserRole.TECHNICIAN,
            12,
            IncidentStatus.CLOSED,
            IncidentStatusClosedError,
            id="incident-closed",
        ),
    ],
)
def test_resolve_incident_rejected(
    actor_role: UserRole,
    assigned_to_id: int | None,
    incident_status: IncidentStatus,
    expected_error: type[Exception],
) -> None:
    (
        service,
        incident,
        actor,
        incident_repository,
        user_repository,
        incident_history_repository,
        audit_repository,
    ) = build_resolve_context(
        actor_role=actor_role,
        assigned_to_id=assigned_to_id,
        incident_status=incident_status,
    )

    old_status = incident.status
    old_resolution = incident.resolution
    old_resolved_at = incident.resolved_at
    old_closed_at = incident.closed_at
    old_assignee = incident.assigned_to_id
    old_priority = incident.priority

    with pytest.raises(expected_error):
        service.resolve_incident(
            incident_id=incident.id,
            resolution="Incident corrigé",
            actor_id=actor.id,
        )

    # Vérifier qu'aucune donnée métier n'a été modifiée
    assert incident.status == old_status
    assert incident.resolution == old_resolution
    assert incident.resolved_at == old_resolved_at
    assert incident.closed_at == old_closed_at
    assert incident.assigned_to_id == old_assignee
    assert incident.priority == old_priority

    incident_repository.get_by_id.assert_called_once_with(
        incident_id=incident.id
    )

    user_repository.get_by_id.assert_called_once_with(
        user_id=actor.id
    )

    # Aucune trace de succès
    incident_history_repository.create.assert_not_called()
    audit_repository.create.assert_not_called()


# ==========================================================
# 4. INCIDENT INEXISTANT
# ==========================================================


def test_resolve_incident_not_found() -> None:
    (
        service,
        incident,
        actor,
        incident_repository,
        user_repository,
        incident_history_repository,
        audit_repository,
    ) = build_resolve_context(
        incident_exists=False,
    )

    with pytest.raises(IncidentNotFoundError):
        service.resolve_incident(
            incident_id=9999999,
            resolution="Correction effectuée",
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
# 5. ACTEUR INEXISTANT
# ==========================================================


def test_resolve_incident_actor_not_found() -> None:
    (
        service,
        incident,
        actor,
        incident_repository,
        user_repository,
        incident_history_repository,
        audit_repository,
    ) = build_resolve_context(
        actor_exists=False,
    )

    old_status = incident.status

    with pytest.raises(UserNotFoundError):
        service.resolve_incident(
            incident_id=incident.id,
            resolution="Correction effectuée",
            actor_id=9999999,
        )

    incident_repository.get_by_id.assert_called_once_with(
        incident_id=incident.id
    )

    user_repository.get_by_id.assert_called_once_with(
        user_id=9999999
    )

    assert incident.status == old_status
    assert incident.resolution is None
    assert incident.resolved_at is None

    incident_history_repository.create.assert_not_called()
    audit_repository.create.assert_not_called()
