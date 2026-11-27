
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.models.enums import IncidentStatus, UserRole
from app.repositories.audit_repository import AuditRepository
from app.repositories.incident_history_repository import (
    IncidentHistoryRepository,
)
from app.repositories.incident_repository import IncidentRepository
from app.repositories.user_repository import UserRepository
from app.services.incident_service import (
    IncidentNotFoundError,
    IncidentService,
    NotEnoughAuthorization,
    UserNotFoundError,
)

# ==========================================================
# FIXTURE : CONSTRUCTION DU SERVICE AVEC DES MOCKS
# ==========================================================


@pytest.fixture
def context():
    incident_repository = MagicMock(spec=IncidentRepository)
    incident_history_repository = MagicMock(
        spec=IncidentHistoryRepository
    )
    audit_repository = MagicMock(spec=AuditRepository)
    user_repository = MagicMock(spec=UserRepository)

    actor = SimpleNamespace(
        id=10,
        role=UserRole.USER,
    )

    incident = SimpleNamespace(
        id=42,
        created_by_id=10,
        assigned_to_id=20,
        status=IncidentStatus.OPEN,
    )

    # Evénements simulés : le service doit les retourner
    # tels que fournis par le repository.
    history_events = [
        SimpleNamespace(
            id=101,
            incident_id=42,
            actor_id=10,
            action="INCIDENT_CREATED",
        ),
        SimpleNamespace(
            id=102,
            incident_id=42,
            actor_id=20,
            action="ASSIGNED",
        ),
    ]

    user_repository.get_by_id.return_value = actor
    incident_repository.get_by_id.return_value = incident

    incident_history_repository.list_by_incident.return_value = (
        history_events
    )

    service = IncidentService(
        incident_repository,
        incident_history_repository,
        audit_repository,
        user_repository,
    )

    return SimpleNamespace(
        service=service,
        actor=actor,
        incident=incident,
        history_events=history_events,
        incident_repository=incident_repository,
        user_repository=user_repository,
        history_repository=incident_history_repository,
        audit_repository=audit_repository,
    )


# ==========================================================
# HELPER : VERIFIER L'ABSENCE D'ACCES A L'HISTORIQUE
# ==========================================================


def assert_history_not_accessed(context) -> None:
    context.history_repository.list_by_incident.assert_not_called()

    context.history_repository.create.assert_not_called()
    context.audit_repository.create.assert_not_called()


# ==========================================================
# 1. UTILISATEURS AUTORISES
# ==========================================================


@pytest.mark.parametrize(
    "actor_role, created_by_id, assigned_to_id",
    [
        pytest.param(
            UserRole.USER,
            10,
            20,
            id="user-creator",
        ),
        pytest.param(
            UserRole.TECHNICIAN,
            10,
            30,
            id="technician-creator",
        ),
        pytest.param(
            UserRole.TECHNICIAN,
            99,
            10,
            id="technician-assigned",
        ),
        pytest.param(
            UserRole.ADMIN,
            99,
            20,
            id="admin-not-creator",
        ),
    ],
)
def test_authorized_actor_can_list_incident_history(
    context,
    actor_role: UserRole,
    created_by_id: int,
    assigned_to_id: int,
) -> None:

    context.actor.role = actor_role
    context.incident.created_by_id = created_by_id
    context.incident.assigned_to_id = assigned_to_id

    result = context.service.list_incident_history(
        incident_id=42,
        actor_id=10,
    )

    # Le service retourne la liste fournie par le repository.
    assert result is context.history_events
    assert len(result) == 2

    context.incident_repository.get_by_id.assert_called_once_with(
        incident_id=42,
    )

    context.user_repository.get_by_id.assert_called_once_with(
        user_id=10,
    )

    context.history_repository.list_by_incident.assert_called_once_with(
        incident_id=42,
    )

    # Une simple consultation ne crée aucun événement.
    context.history_repository.create.assert_not_called()
    context.audit_repository.create.assert_not_called()


# ==========================================================
# 2. UTILISATEURS NON AUTORISES
# ==========================================================


@pytest.mark.parametrize(
    "actor_role, created_by_id, assigned_to_id",
    [
        pytest.param(
            UserRole.USER,
            99,
            None,
            id="user-not-creator",
        ),
        pytest.param(
            UserRole.USER,
            99,
            10,
            id="user-assigned-but-not-creator",
        ),
        pytest.param(
            UserRole.TECHNICIAN,
            99,
            None,
            id="technician-not-assigned",
        ),
        pytest.param(
            UserRole.TECHNICIAN,
            99,
            30,
            id="technician-assigned-to-another-incident",
        ),
    ],
)
def test_unauthorized_actor_cannot_list_incident_history(
    context,
    actor_role: UserRole,
    created_by_id: int,
    assigned_to_id: int | None,
) -> None:

    context.actor.role = actor_role
    context.incident.created_by_id = created_by_id
    context.incident.assigned_to_id = assigned_to_id

    with pytest.raises(NotEnoughAuthorization):
        context.service.list_incident_history(
            incident_id=42,
            actor_id=10,
        )

    assert_history_not_accessed(context)


# ==========================================================
# 3. ACTEUR INEXISTANT
# ==========================================================


def test_list_history_actor_not_found(context) -> None:

    context.user_repository.get_by_id.return_value = None

    with pytest.raises(UserNotFoundError):
        context.service.list_incident_history(
            incident_id=42,
            actor_id=999,
        )

    context.user_repository.get_by_id.assert_called_once_with(
        user_id=999,
    )

    assert_history_not_accessed(context)


# ==========================================================
# 4. INCIDENT INEXISTANT
# ==========================================================


def test_list_history_incident_not_found(context) -> None:

    context.incident_repository.get_by_id.return_value = None

    with pytest.raises(IncidentNotFoundError):
        context.service.list_incident_history(
            incident_id=999,
            actor_id=10,
        )

    context.incident_repository.get_by_id.assert_called_once_with(
        incident_id=999,
    )

    assert_history_not_accessed(context)


# ==========================================================
# 5. ACTEUR ET INCIDENT INEXISTANTS
# ==========================================================


def test_list_history_actor_and_incident_not_found(context) -> None:

    context.user_repository.get_by_id.return_value = None
    context.incident_repository.get_by_id.return_value = None

    # Le service vérifie d'abord l'existence de l'acteur.
    with pytest.raises(UserNotFoundError):
        context.service.list_incident_history(
            incident_id=999,
            actor_id=999,
        )

    assert_history_not_accessed(context)


# ==========================================================
# 6. HISTORIQUE VIDE
# ==========================================================


def test_list_history_returns_empty_list(context) -> None:

    context.history_repository.list_by_incident.return_value = []

    result = context.service.list_incident_history(
        incident_id=42,
        actor_id=10,
    )

    assert result == []
    assert isinstance(result, list)

    context.history_repository.list_by_incident.assert_called_once_with(
        incident_id=42,
    )

    context.history_repository.create.assert_not_called()
    context.audit_repository.create.assert_not_called()


# ==========================================================
# 7. CONSULTATION POSSIBLE QUEL QUE SOIT LE STATUT
# ==========================================================


@pytest.mark.parametrize(
    "incident_status",
    [
        pytest.param(IncidentStatus.OPEN, id="open"),
        pytest.param(IncidentStatus.IN_PROGRESS, id="in-progress"),
        pytest.param(IncidentStatus.RESOLVED, id="resolved"),
        pytest.param(IncidentStatus.CLOSED, id="closed"),
    ],
)
def test_creator_can_list_history_for_any_incident_status(
    context,
    incident_status: IncidentStatus,
) -> None:

    context.incident.status = incident_status

    result = context.service.list_incident_history(
        incident_id=42,
        actor_id=10,
    )

    assert result is context.history_events

    context.history_repository.list_by_incident.assert_called_once_with(
        incident_id=42,
    )


# ==========================================================
# 8. CONSULTATION SANS MODIFICATION DES DONNEES
# ==========================================================


def test_list_history_does_not_modify_incident(context) -> None:

    old_status = context.incident.status
    old_creator = context.incident.created_by_id
    old_assignee = context.incident.assigned_to_id

    original_events = list(context.history_events)

    result = context.service.list_incident_history(
        incident_id=42,
        actor_id=10,
    )

    assert result is context.history_events
    assert result == original_events

    assert context.incident.status == old_status
    assert context.incident.created_by_id == old_creator
    assert context.incident.assigned_to_id == old_assignee

    context.history_repository.create.assert_not_called()
    context.audit_repository.create.assert_not_called()
