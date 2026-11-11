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
from app.repositories.audit_repository import AuditRepository
from app.repositories.incident_history_repository import IncidentHistoryRepository
from app.repositories.incident_repository import IncidentRepository
from app.repositories.user_repository import UserRepository
from app.schemas.incident import IncidentCreate
from app.services.incident_service import (
    IncidentNotFoundError,
    IncidentService,
    IncidentStatusClosedError,
    InvalidAssignmentTargetError,
    NotEnoughAuthorization,
    UserInactiveError,
    UserNotFoundError,
)


def test_admin_can_change_incident_priority() -> None:
    incident_repository = MagicMock(spec=IncidentRepository)
    incident_history_repository = MagicMock(spec=IncidentHistoryRepository)
    audit_repository = MagicMock(spec=AuditRepository)
    user_repository = MagicMock(spec=UserRepository)

    user_admin = User(
        id=13,
        email="admin@gmail.com",
        password_hash="password_hash",
        full_name="SYLLA",
        role=UserRole.ADMIN,
        is_active=True,
    )

    expected_incident = Incident(
        id=42,
        title="Erreur concernant bouton ENVOYE",
        description="Le bouton envoyé ne mène à aucun chemin",
        category=IncidentCategory.ANOMALY,
        priority=IncidentPriority.MEDIUM,
        status=IncidentStatus.OPEN,
        created_by_id=42,
    )

    incident_repository.get_by_id.return_value = expected_incident

    service = IncidentService(
        incident_repository,
        incident_history_repository,
        audit_repository,
        user_repository,
    )

    assert expected_incident.priority is IncidentPriority.MEDIUM

    user_repository.get_by_id.return_value = user_admin

    old_priority = expected_incident.priority

    result = service.change_priority(
        incident_id=expected_incident.id,
        new_priority=IncidentPriority.CRITICAL,
        actor_id=user_admin.id,
    )

    user_repository.get_by_id.assert_called_once_with(user_id=user_admin.id)

    assert result is expected_incident
    assert result.status == IncidentStatus.OPEN
    assert result.priority == IncidentPriority.CRITICAL

    incident_repository.get_by_id.assert_called_once_with(
        incident_id=expected_incident.id
    )

    incident_history_repository.create.assert_called_once_with(
        incident_id=expected_incident.id,
        actor_id=user_admin.id,
        action=IncidentHistoryAction.PRIORITY_CHANGED,
        field_name="priority",
        old_value=old_priority.value,
        new_value=IncidentPriority.CRITICAL.value,
    )

    audit_repository.create.assert_called_once_with(
        event_type=AuditEventType.INCIDENT_PRIORITY_CHANGED,
        result=AuditResult.SUCCESS,
        user_id=user_admin.id,
    )


def test_change_incident_priority_to_the_same_value() -> None:
    incident_repository = MagicMock(spec=IncidentRepository)
    incident_history_repository = MagicMock(spec=IncidentHistoryRepository)
    audit_repository = MagicMock(spec=AuditRepository)
    user_repository = MagicMock(spec=UserRepository)

    user_admin = User(
        id=13,
        email="admin@gmail.com",
        password_hash="password_hash",
        full_name="SYLLA",
        role=UserRole.ADMIN,
        is_active=True,
    )

    expected_incident = Incident(
        id=42,
        title="Erreur concernant bouton ENVOYE",
        description="Le bouton envoyé ne mène à aucun chemin",
        category=IncidentCategory.ANOMALY,
        priority=IncidentPriority.MEDIUM,
        status=IncidentStatus.OPEN,
        created_by_id=42,
    )

    incident_repository.get_by_id.return_value = expected_incident

    user_repository.get_by_id.return_value = user_admin

    service = IncidentService(
        incident_repository,
        incident_history_repository,
        audit_repository,
        user_repository,
    )

    assert expected_incident.priority is IncidentPriority.MEDIUM

    result = service.change_priority(
        incident_id=expected_incident.id,
        new_priority=IncidentPriority.MEDIUM,
        actor_id=user_admin.id,
    )

    user_repository.get_by_id.assert_called_once_with(user_id=user_admin.id)

    assert result is expected_incident
    assert result.priority == IncidentPriority.MEDIUM

    incident_history_repository.create.assert_not_called()
    audit_repository.create.assert_not_called()


@pytest.mark.parametrize(
    "actor_role, incident_status, expected_error",
    [
        pytest.param(
            UserRole.USER,
            IncidentStatus.OPEN,
            NotEnoughAuthorization,
            id="user-forbidden",
        ),
        pytest.param(
            UserRole.TECHNICIAN,
            IncidentStatus.OPEN,
            NotEnoughAuthorization,
            id="technician-forbidden",
        ),
        pytest.param(
            UserRole.ADMIN,
            IncidentStatus.CLOSED,
            IncidentStatusClosedError,
            id="incident-closed",
        ),
    ],
)
def test_change_priority_rejected(actor_role, incident_status, expected_error) -> None:
    incident_repository = MagicMock(spec=IncidentRepository)
    incident_history_repository = MagicMock(spec=IncidentHistoryRepository)
    audit_repository = MagicMock(spec=AuditRepository)
    user_repository = MagicMock(spec=UserRepository)

    user_admin = User(
        id=13,
        email="user@gmail.com",
        password_hash="password_hash",
        full_name="SYLLA",
        role=actor_role,
        is_active=True,
    )

    expected_incident = Incident(
        id=42,
        title="Erreur concernant bouton ENVOYE",
        description="Le bouton envoyé ne mène à aucun chemin",
        category=IncidentCategory.ANOMALY,
        priority=IncidentPriority.MEDIUM,
        status=incident_status,
        created_by_id=42,
    )

    incident_repository.get_by_id.return_value = expected_incident

    old_priority = expected_incident.priority

    user_repository.get_by_id.return_value = user_admin

    service = IncidentService(
        incident_repository,
        incident_history_repository,
        audit_repository,
        user_repository,
    )

    assert expected_incident.priority is IncidentPriority.MEDIUM
    with pytest.raises(expected_error):
        service.change_priority(
            incident_id=expected_incident.id,
            new_priority=IncidentPriority.HIGH,
            actor_id=user_admin.id,
        )

    user_repository.get_by_id.assert_called_once_with(user_id=user_admin.id)

    assert expected_incident.priority == old_priority 
    incident_history_repository.create.assert_not_called()
    audit_repository.create.assert_not_called()



def test_change_priority_incident_not_found() -> None:
    incident_repository = MagicMock(spec=IncidentRepository)
    incident_history_repository = MagicMock(spec=IncidentHistoryRepository)
    audit_repository = MagicMock(spec=AuditRepository)
    user_repository = MagicMock(spec=UserRepository)

    user_admin = User(
        id=13,
        email="admin@gmail.com",
        password_hash="password_hash",
        full_name="SYLLA",
        role=UserRole.ADMIN,
        is_active=True,
    )

    # L'incident recherché n'existe pas
    incident_repository.get_by_id.return_value = None

    user_repository.get_by_id.return_value = user_admin

    service = IncidentService(
        incident_repository,
        incident_history_repository,
        audit_repository,
        user_repository,
    )

    with pytest.raises(IncidentNotFoundError):
        service.change_priority(
            incident_id=9999999,
            new_priority=IncidentPriority.HIGH,
            actor_id=user_admin.id,
        )

    incident_repository.get_by_id.assert_called_once_with(
        incident_id=9999999
    )

    user_repository.get_by_id.assert_called_once_with(
        user_id=user_admin.id
    )

    incident_history_repository.create.assert_not_called()
    audit_repository.create.assert_not_called()



def test_change_priority_actor_not_found() -> None:
    incident_repository = MagicMock(spec=IncidentRepository)
    incident_history_repository = MagicMock(spec=IncidentHistoryRepository)
    audit_repository = MagicMock(spec=AuditRepository)
    user_repository = MagicMock(spec=UserRepository)

    expected_incident = Incident(
        id=42,
        title="Erreur concernant bouton ENVOYE",
        description="Le bouton envoyé ne mène à aucun chemin",
        category=IncidentCategory.ANOMALY,
        priority=IncidentPriority.MEDIUM,
        status=IncidentStatus.OPEN,
        created_by_id=42,
    )

    incident_repository.get_by_id.return_value = expected_incident

    # L'administrateur recherché n'existe pas
    user_repository.get_by_id.return_value = None

    service = IncidentService(
        incident_repository,
        incident_history_repository,
        audit_repository,
        user_repository,
    )

    old_priority = expected_incident.priority

    with pytest.raises(UserNotFoundError):
        service.change_priority(
            incident_id=expected_incident.id,
            new_priority=IncidentPriority.CRITICAL,
            actor_id=9999999,
        )

    incident_repository.get_by_id.assert_called_once_with(
        incident_id=expected_incident.id
    )

    user_repository.get_by_id.assert_called_once_with(
        user_id=9999999
    )

    # Aucune modification de l'incident
    assert expected_incident.priority == old_priority

    # Aucun historique ni audit de succès
    incident_history_repository.create.assert_not_called()
    audit_repository.create.assert_not_called()

