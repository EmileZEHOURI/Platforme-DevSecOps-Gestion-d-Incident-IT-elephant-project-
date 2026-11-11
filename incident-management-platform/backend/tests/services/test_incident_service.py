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

# le repository incident est appelé avec data et created_by_id,


def create_incident_list() -> list[Incident]:
    return [
        Incident(
            id=number,
            title=f"Incident {number}",
            description="Incident de test",
            category=IncidentCategory.ANOMALY,
            priority=IncidentPriority.MEDIUM,
            status=IncidentStatus.OPEN,
            created_by_id=42,
            assigned_to_id=1,
        )
        for number in range(1, 4)
    ]


def test_success_create_with_data_and_created_by_id() -> None:
    incident_repository = MagicMock(spec=IncidentRepository)
    incident_history_repository = MagicMock(spec=IncidentHistoryRepository)
    audit_repository = MagicMock(spec=AuditRepository)
    user_repository = MagicMock(spec=UserRepository)

    # Simulation données envoyé par l'utilisateur
    incident_data = IncidentCreate(
        title="Erreur concernant bouton ENVOYE",
        description="Le bouton envoyé ne mène à aucun chemin",
        category=IncidentCategory.ANOMALY,
        priority=IncidentPriority.MEDIUM,
    )

    # simulation du retour du repository après cette création
    create_incident = Incident(
        id=42,
        title="Erreur concernant bouton ENVOYE",
        description="Le bouton envoyé ne mène à aucun chemin",
        category=IncidentCategory.ANOMALY,
        priority=IncidentPriority.MEDIUM,
        created_by_id=2,
        status=IncidentStatus.OPEN,
    )
    # service appel incident_repository.create(),
    # fais comme  repository avait créé l'incident en base
    # et retourne created_incident
    incident_repository.create.return_value = create_incident

    service = IncidentService(
        incident_repository,
        incident_history_repository,
        audit_repository,
        user_repository,
    )

    result = service.create_incident(
        data=incident_data,
        created_by_id=2,
    )

    incident_repository.create.assert_called_once_with(
        data=incident_data, created_by_id=2
    )

    incident_history_repository.create.assert_called_once_with(
        incident_id=42, actor_id=2, action=IncidentHistoryAction.INCIDENT_CREATED
    )

    assert result is create_incident
    audit_repository.create.assert_called_once_with(
        event_type=AuditEventType.INCIDENT_CREATED,
        result=AuditResult.SUCCESS,
        user_id=2,
        resource_type="incident",
        resource_id=42,
    )


def test_recuperation_list() -> None:
    incident_repository = MagicMock(spec=IncidentRepository)
    incident_history_repository = MagicMock(spec=IncidentHistoryRepository)
    audit_repository = MagicMock(spec=AuditRepository)
    user_repository = MagicMock(spec=UserRepository)

    expected_incidents = create_incident_list()

    incident_repository.list_by_creator.return_value = expected_incidents

    service = IncidentService(
        incident_repository,
        incident_history_repository,
        audit_repository,
        user_repository,
    )

    result = service.list_user_incidents(created_by_id=42)
    incident_repository.list_by_creator.assert_called_once_with(created_by_id=42)

    assert result is expected_incidents


def test_recuperation_empty_list() -> None:
    incident_repository = MagicMock(spec=IncidentRepository)
    incident_history_repository = MagicMock(spec=IncidentHistoryRepository)
    audit_repository = MagicMock(spec=AuditRepository)
    user_repository = MagicMock(spec=UserRepository)

    expected_incidents = []

    incident_repository.list_by_creator.return_value = expected_incidents

    service = IncidentService(
        incident_repository,
        incident_history_repository,
        audit_repository,
        user_repository,
    )

    result = service.list_user_incidents(created_by_id=42)
    incident_repository.list_by_creator.assert_called_once_with(created_by_id=42)
    assert result is expected_incidents


def test_get_incident_details() -> None:
    incident_repository = MagicMock(spec=IncidentRepository)
    incident_history_repository = MagicMock(spec=IncidentHistoryRepository)
    audit_repository = MagicMock(spec=AuditRepository)
    user_repository = MagicMock(spec=UserRepository)

    expected_incident = Incident(
        id=1,
        title="Incident 1",
        description="Incident de test",
        category=IncidentCategory.ANOMALY,
        priority=IncidentPriority.MEDIUM,
        status=IncidentStatus.OPEN,
        created_by_id=42,
    )

    incident_repository.get_by_id_and_creator.return_value = expected_incident

    service = IncidentService(
        incident_repository,
        incident_history_repository,
        audit_repository,
        user_repository,
    )

    result = service.get_incident_detail(incident_id=1, created_by_id=42)
    assert result is expected_incident


def test_get_incident_details_error() -> None:
    incident_repository = MagicMock(spec=IncidentRepository)
    incident_history_repository = MagicMock(spec=IncidentHistoryRepository)
    audit_repository = MagicMock(spec=AuditRepository)
    user_repository = MagicMock(spec=UserRepository)

    expected_incident = None

    incident_repository.get_by_id_and_creator.return_value = expected_incident

    service = IncidentService(
        incident_repository,
        incident_history_repository,
        audit_repository,
        user_repository,
    )

    with pytest.raises(IncidentNotFoundError):
        service.get_incident_detail(incident_id=1, created_by_id=42)


def test_recuperation_list_assigned_incident() -> None:
    incident_repository = MagicMock(spec=IncidentRepository)
    incident_history_repository = MagicMock(spec=IncidentHistoryRepository)
    audit_repository = MagicMock(spec=AuditRepository)
    user_repository = MagicMock(spec=UserRepository)

    expected_incidents = create_incident_list()

    incident_repository.list_by_assignee.return_value = expected_incidents

    service = IncidentService(
        incident_repository,
        incident_history_repository,
        audit_repository,
        user_repository,
    )

    result = service.list_assigned_incidents(assigned_to_id=1)
    incident_repository.list_by_assignee.assert_called_once_with(assigned_to_id=1)

    assert result is expected_incidents


def test_list_assigned_incidents_returns_empty_list() -> None:
    incident_repository = MagicMock(spec=IncidentRepository)
    incident_history_repository = MagicMock(spec=IncidentHistoryRepository)
    audit_repository = MagicMock(spec=AuditRepository)
    user_repository = MagicMock(spec=UserRepository)

    expected_incidents = []

    incident_repository.list_by_assignee.return_value = expected_incidents

    service = IncidentService(
        incident_repository,
        incident_history_repository,
        audit_repository,
        user_repository,
    )

    result = service.list_assigned_incidents(assigned_to_id=2)
    incident_repository.list_by_assignee.assert_called_once_with(assigned_to_id=2)

    assert result is expected_incidents


def test_initial_assignation() -> None:
    incident_repository = MagicMock(spec=IncidentRepository)
    incident_history_repository = MagicMock(spec=IncidentHistoryRepository)
    audit_repository = MagicMock(spec=AuditRepository)
    user_repository = MagicMock(spec=UserRepository)

    user_technician = User(
        id=12,
        email="bblala@gmail.com",
        password_hash="password_hash",
        full_name="ZEHOURI",
        role=UserRole.TECHNICIAN,
        is_active=True,
    )

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
        assigned_to_id=None,
    )

    incident_repository.get_by_id.return_value = expected_incident

    service = IncidentService(
        incident_repository,
        incident_history_repository,
        audit_repository,
        user_repository,
    )

    assert expected_incident.assigned_to_id is None

    users = {
        user_admin.id: user_admin,
        user_technician.id: user_technician,
    }

    user_repository.get_by_id.side_effect = lambda user_id: users.get(user_id)

    result = service.assign_incident(
        incident_id=expected_incident.id,
        assigned_to_id=user_technician.id,
        actor_id=user_admin.id,
    )

    assert result is expected_incident
    assert result.assigned_to_id == user_technician.id
    assert result.status == IncidentStatus.OPEN

    incident_repository.get_by_id.assert_called_once_with(
        incident_id=expected_incident.id
    )

    incident_history_repository.create.assert_called_once_with(
        incident_id=expected_incident.id,
        actor_id=user_admin.id,
        action=IncidentHistoryAction.ASSIGNED,
        field_name="assigned_to_id",
        old_value=None,
        new_value=str(user_technician.id),
    )

    audit_repository.create.assert_called_once_with(
        event_type=AuditEventType.INCIDENT_ASSIGNED,
        result=AuditResult.SUCCESS,
        user_id=user_admin.id,
    )


def test_reassignation() -> None:
    incident_repository = MagicMock(spec=IncidentRepository)
    incident_history_repository = MagicMock(spec=IncidentHistoryRepository)
    audit_repository = MagicMock(spec=AuditRepository)
    user_repository = MagicMock(spec=UserRepository)

    user_technician_1 = User(
        id=1,
        email="bblala@gmail.com",
        password_hash="password_hash",
        full_name="ZEHOURI",
        role=UserRole.TECHNICIAN,
        is_active=True,
    )

    user_technician_2 = User(
        id=2,
        email="bblala@gmail.com",
        password_hash="password_hash",
        full_name="ZEHOURI",
        role=UserRole.TECHNICIAN,
        is_active=True,
    )

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
        assigned_to_id=1,
    )

    incident_repository.get_by_id.return_value = expected_incident

    service = IncidentService(
        incident_repository,
        incident_history_repository,
        audit_repository,
        user_repository,
    )

    users = {
        user_admin.id: user_admin,
        user_technician_1.id: user_technician_1,
        user_technician_2.id: user_technician_2,
    }

    user_repository.get_by_id.side_effect = lambda user_id: users.get(user_id)

    result = service.assign_incident(
        incident_id=expected_incident.id,
        assigned_to_id=user_technician_2.id,
        actor_id=user_admin.id,
    )

    assert result is expected_incident
    assert result.assigned_to_id == user_technician_2.id
    assert result.status == IncidentStatus.OPEN

    incident_repository.get_by_id.assert_called_once_with(
        incident_id=expected_incident.id
    )

    incident_history_repository.create.assert_called_once_with(
        incident_id=expected_incident.id,
        actor_id=user_admin.id,
        action=IncidentHistoryAction.REASSIGNED,
        field_name="assigned_to_id",
        old_value=str(user_technician_1.id),
        new_value=str(user_technician_2.id),
    )

    audit_repository.create.assert_called_once_with(
        event_type=AuditEventType.INCIDENT_REASSIGNED,
        result=AuditResult.SUCCESS,
        user_id=user_admin.id,
    )


def test_assign_incident_to_a_technician_already_responsible() -> None:
    incident_repository = MagicMock(spec=IncidentRepository)
    incident_history_repository = MagicMock(spec=IncidentHistoryRepository)
    audit_repository = MagicMock(spec=AuditRepository)
    user_repository = MagicMock(spec=UserRepository)

    user_technician = User(
        id=1,
        email="bblala@gmail.com",
        password_hash="password_hash",
        full_name="ZEHOURI",
        role=UserRole.TECHNICIAN,
        is_active=True,
    )

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
        assigned_to_id=1,
    )

    incident_repository.get_by_id.return_value = expected_incident

    service = IncidentService(
        incident_repository,
        incident_history_repository,
        audit_repository,
        user_repository,
    )

    users = {
        user_admin.id: user_admin,
        user_technician.id: user_technician,
    }

    user_repository.get_by_id.side_effect = lambda user_id: users.get(user_id)

    result = service.assign_incident(
        incident_id=expected_incident.id,
        assigned_to_id=user_technician.id,
        actor_id=user_admin.id,
    )

    assert result is expected_incident
    assert result.assigned_to_id == user_technician.id
    assert result.status == IncidentStatus.OPEN

    incident_repository.get_by_id.assert_called_once_with(
        incident_id=expected_incident.id
    )

    incident_history_repository.create.assert_not_called()

    audit_repository.create.assert_not_called()


def test_admin_cannot_assign_incident_to_another_admin() -> None:

    incident_repository = MagicMock(spec=IncidentRepository)
    incident_history_repository = MagicMock(spec=IncidentHistoryRepository)
    audit_repository = MagicMock(spec=AuditRepository)
    user_repository = MagicMock(spec=UserRepository)

    user_admin_1 = User(
        id=13,
        email="admin_1@gmail.com",
        password_hash="password_hash",
        full_name="SYLLA",
        role=UserRole.ADMIN,
        is_active=True,
    )

    user_admin_2 = User(
        id=14,
        email="admin_2@gmail.com",
        password_hash="password_hash",
        full_name="MAWA",
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
        assigned_to_id=None,
    )

    incident_repository.get_by_id.return_value = expected_incident

    assert expected_incident.assigned_to_id is None

    service = IncidentService(
        incident_repository,
        incident_history_repository,
        audit_repository,
        user_repository,
    )

    users = {
        user_admin_1.id: user_admin_1,
        user_admin_2.id: user_admin_2,
    }

    user_repository.get_by_id.side_effect = lambda user_id: users.get(user_id)

    with pytest.raises(InvalidAssignmentTargetError):
        service.assign_incident(
            incident_id=expected_incident.id,
            assigned_to_id=user_admin_2.id,
            actor_id=user_admin_1.id,
        )

    assert expected_incident.assigned_to_id is None
    incident_history_repository.create.assert_not_called()
    audit_repository.create.assert_not_called()


@pytest.mark.parametrize(
    "actor_role, target_active, target_role, incident_status, expected_error",
    [
        pytest.param(
            UserRole.USER,
            True,
            UserRole.TECHNICIAN,
            IncidentStatus.OPEN,
            NotEnoughAuthorization,
            id="actor-not-admin",
        ),
        pytest.param(
            UserRole.ADMIN,
            False,
            UserRole.TECHNICIAN,
            IncidentStatus.OPEN,
            UserInactiveError,
            id="target-inactive",
        ),
        pytest.param(
            UserRole.ADMIN,
            True,
            UserRole.USER,
            IncidentStatus.OPEN,
            InvalidAssignmentTargetError,
            id="target-role-user",
        ),
        pytest.param(
            UserRole.ADMIN,
            True,
            UserRole.TECHNICIAN,
            IncidentStatus.CLOSED,
            IncidentStatusClosedError,
            id="incident-closed",
        ),
    ],
)
def test_assignment_rejected(
    actor_role,
    target_active,
    target_role,
    incident_status,
    expected_error,
) -> None:

    incident_repository = MagicMock(spec=IncidentRepository)
    incident_history_repository = MagicMock(spec=IncidentHistoryRepository)
    audit_repository = MagicMock(spec=AuditRepository)
    user_repository = MagicMock(spec=UserRepository)

    user_1 = User(
        id=13,
        email="user_1@gmail.com",
        password_hash="password_hash",
        full_name="SYLLA",
        role=target_role,
        is_active=target_active,
    )

    user_2 = User(
        id=14,
        email="user_2@gmail.com",
        password_hash="password_hash",
        full_name="MAWA",
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
        assigned_to_id=None,
    )

    incident_repository.get_by_id.return_value = expected_incident

    assert expected_incident.assigned_to_id is None

    service = IncidentService(
        incident_repository,
        incident_history_repository,
        audit_repository,
        user_repository,
    )

    users = {
        user_1.id: user_1,
        user_2.id: user_2,
    }

    user_repository.get_by_id.side_effect = lambda user_id: users.get(user_id)

    with pytest.raises(expected_error):
        service.assign_incident(
            incident_id=expected_incident.id,
            assigned_to_id=user_1.id,
            actor_id=user_2.id,
        )

    assert expected_incident.assigned_to_id is None
    incident_history_repository.create.assert_not_called()
    audit_repository.create.assert_not_called()


def test_admin_assign_an_incident_to_himself() -> None:
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
        assigned_to_id=None,
    )

    incident_repository.get_by_id.return_value = expected_incident

    service = IncidentService(
        incident_repository,
        incident_history_repository,
        audit_repository,
        user_repository,
    )

    assert expected_incident.assigned_to_id is None

    users = {
        user_admin.id: user_admin,
    }

    user_repository.get_by_id.side_effect = lambda user_id: users.get(user_id)

    result = service.assign_incident(
        incident_id=expected_incident.id,
        assigned_to_id=user_admin.id,
        actor_id=user_admin.id,
    )

    assert result is expected_incident
    assert result.assigned_to_id == user_admin.id
    assert result.status == IncidentStatus.OPEN

    incident_repository.get_by_id.assert_called_once_with(
        incident_id=expected_incident.id
    )

    incident_history_repository.create.assert_called_once_with(
        incident_id=expected_incident.id,
        actor_id=user_admin.id,
        action=IncidentHistoryAction.ASSIGNED,
        field_name="assigned_to_id",
        old_value=None,
        new_value=str(user_admin.id),
    )

    audit_repository.create.assert_called_once_with(
        event_type=AuditEventType.INCIDENT_ASSIGNED,
        result=AuditResult.SUCCESS,
        user_id=user_admin.id,
    )


def test_assign_incident_to_inexistant_incident() -> None:
    incident_repository = MagicMock(spec=IncidentRepository)
    incident_history_repository = MagicMock(spec=IncidentHistoryRepository)
    audit_repository = MagicMock(spec=AuditRepository)
    user_repository = MagicMock(spec=UserRepository)

    user_technician = User(
        id=12,
        email="bblala@gmail.com",
        password_hash="password_hash",
        full_name="ZEHOURI",
        role=UserRole.TECHNICIAN,
        is_active=True,
    )

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
        assigned_to_id=None,
    )

    incident_repository.get_by_id.return_value = None

    service = IncidentService(
        incident_repository,
        incident_history_repository,
        audit_repository,
        user_repository,
    )

    assert expected_incident.assigned_to_id is None

    users = {
        user_admin.id: user_admin,
        user_technician.id: user_technician,
    }

    user_repository.get_by_id.side_effect = lambda user_id: users.get(user_id)

    with pytest.raises(IncidentNotFoundError):
        service.assign_incident(
            incident_id=9999999,
            assigned_to_id=user_technician.id,
            actor_id=user_admin.id,
        )

    incident_repository.get_by_id.assert_called_once_with(incident_id=9999999)

    incident_history_repository.create.assert_not_called()
    audit_repository.create.assert_not_called()


def test_assign_incident_to_nonexistent_user() -> None:
    incident_repository = MagicMock(spec=IncidentRepository)
    incident_history_repository = MagicMock(spec=IncidentHistoryRepository)
    audit_repository = MagicMock(spec=AuditRepository)
    user_repository = MagicMock(spec=UserRepository)

    user_technician = User(
        id=12,
        email="bblala@gmail.com",
        password_hash="password_hash",
        full_name="ZEHOURI",
        role=UserRole.TECHNICIAN,
        is_active=True,
    )

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
        assigned_to_id=None,
    )

    incident_repository.get_by_id.return_value = expected_incident

    service = IncidentService(
        incident_repository,
        incident_history_repository,
        audit_repository,
        user_repository,
    )

    assert expected_incident.assigned_to_id is None

    users = {
        user_admin.id: user_admin,
        user_technician.id: user_technician,
    }

    user_repository.get_by_id.side_effect = lambda user_id: users.get(user_id)

    with pytest.raises(UserNotFoundError):
        service.assign_incident(
            incident_id=expected_incident.id,
            assigned_to_id=9999999,
            actor_id=user_admin.id,
        )

    assert expected_incident.assigned_to_id is None
    incident_history_repository.create.assert_not_called()
    audit_repository.create.assert_not_called()


def test_assign_incident_to_nonexistent_admin() -> None:
    incident_repository = MagicMock(spec=IncidentRepository)
    incident_history_repository = MagicMock(spec=IncidentHistoryRepository)
    audit_repository = MagicMock(spec=AuditRepository)
    user_repository = MagicMock(spec=UserRepository)

    user_technician = User(
        id=12,
        email="bblala@gmail.com",
        password_hash="password_hash",
        full_name="ZEHOURI",
        role=UserRole.TECHNICIAN,
        is_active=True,
    )

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
        assigned_to_id=None,
    )

    incident_repository.get_by_id.return_value = expected_incident

    service = IncidentService(
        incident_repository,
        incident_history_repository,
        audit_repository,
        user_repository,
    )

    assert expected_incident.assigned_to_id is None

    users = {
        user_admin.id: user_admin,
        user_technician.id: user_technician,
    }

    user_repository.get_by_id.side_effect = lambda user_id: users.get(user_id)

    with pytest.raises(UserNotFoundError):
        service.assign_incident(
            incident_id=expected_incident.id,
            assigned_to_id=user_technician.id,
            actor_id=9999999,
        )

    user_repository.get_by_id.assert_any_call(user_id=9999999)

    assert expected_incident.assigned_to_id is None
    incident_history_repository.create.assert_not_called()
    audit_repository.create.assert_not_called()
