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
from app.services.incident_service import (
    IncidentNotFoundError,
    IncidentService,
    IncidentStatusClosedError,
    IncidentStatusResolvedError,
    IncidentWithoutAssignmentError,
    InvalidStatusTransitionError,
    NotEnoughAuthorization,
    UserNotFoundError,
)


def test_technician_can_start_assigned_incident() -> None:
    incident_repository = MagicMock(spec=IncidentRepository)
    incident_history_repository = MagicMock(spec=IncidentHistoryRepository)
    audit_repository = MagicMock(spec=AuditRepository)
    user_repository = MagicMock(spec=UserRepository)

    user_technician = User(
        id=12,
        email="technician@gmail.com",
        password_hash="password_hash",
        full_name="SYLLA",
        role=UserRole.TECHNICIAN,
        is_active=True,
    )

    expected_incident = Incident(
        id=42,
        title="Incident à traiter",
        description="Un incident nécessitant une intervention.",
        category=IncidentCategory.ANOMALY,
        priority=IncidentPriority.MEDIUM,
        status=IncidentStatus.OPEN,
        created_by_id=10,
        assigned_to_id=12,
    )

    incident_repository.get_by_id.return_value = expected_incident

    service = IncidentService(
        incident_repository,
        incident_history_repository,
        audit_repository,
        user_repository,
    )

    assert expected_incident.status is IncidentStatus.OPEN

    user_repository.get_by_id.return_value = user_technician

    old_status = expected_incident.status

    result = service.change_status(
        incident_id=expected_incident.id,
        new_status=IncidentStatus.IN_PROGRESS,
        actor_id=user_technician.id,
    )

    user_repository.get_by_id.assert_called_once_with(user_id=user_technician.id)

    assert result is expected_incident
    assert result.status == IncidentStatus.IN_PROGRESS

    incident_repository.get_by_id.assert_called_once_with(
        incident_id=expected_incident.id
    )

    incident_history_repository.create.assert_called_once_with(
        incident_id=expected_incident.id,
        actor_id=user_technician.id,
        action=IncidentHistoryAction.STATUS_CHANGED,
        field_name="status",
        old_value=old_status.value,
        new_value=IncidentStatus.IN_PROGRESS.value,
    )

    audit_repository.create.assert_called_once_with(
        event_type=AuditEventType.INCIDENT_STATUS_CHANGED,
        result=AuditResult.SUCCESS,
        user_id=user_technician.id,
    )


def test_admin_can_start_self_assigned_incident() -> None:
    incident_repository = MagicMock(spec=IncidentRepository)
    incident_history_repository = MagicMock(spec=IncidentHistoryRepository)
    audit_repository = MagicMock(spec=AuditRepository)
    user_repository = MagicMock(spec=UserRepository)

    user_admin = User(
        id=12,
        email="admin@gmail.com",
        password_hash="password_hash",
        full_name="SYLLA",
        role=UserRole.ADMIN,
        is_active=True,
    )

    expected_incident = Incident(
        id=42,
        title="Incident à traiter",
        description="Un incident nécessitant une intervention.",
        category=IncidentCategory.ANOMALY,
        priority=IncidentPriority.MEDIUM,
        status=IncidentStatus.OPEN,
        created_by_id=10,
        assigned_to_id=12,
    )

    incident_repository.get_by_id.return_value = expected_incident

    service = IncidentService(
        incident_repository,
        incident_history_repository,
        audit_repository,
        user_repository,
    )

    assert expected_incident.status is IncidentStatus.OPEN

    user_repository.get_by_id.return_value = user_admin

    old_status = expected_incident.status

    result = service.change_status(
        incident_id=expected_incident.id,
        new_status=IncidentStatus.IN_PROGRESS,
        actor_id=user_admin.id,
    )

    user_repository.get_by_id.assert_called_once_with(user_id=user_admin.id)

    assert result is expected_incident
    assert result.status == IncidentStatus.IN_PROGRESS

    incident_repository.get_by_id.assert_called_once_with(
        incident_id=expected_incident.id
    )

    incident_history_repository.create.assert_called_once_with(
        incident_id=expected_incident.id,
        actor_id=user_admin.id,
        action=IncidentHistoryAction.STATUS_CHANGED,
        field_name="status",
        old_value=old_status.value,
        new_value=IncidentStatus.IN_PROGRESS.value,
    )

    audit_repository.create.assert_called_once_with(
        event_type=AuditEventType.INCIDENT_STATUS_CHANGED,
        result=AuditResult.SUCCESS,
        user_id=user_admin.id,
    )


def test_technician_not_responsible() -> None:
    incident_repository = MagicMock(spec=IncidentRepository)
    incident_history_repository = MagicMock(spec=IncidentHistoryRepository)
    audit_repository = MagicMock(spec=AuditRepository)
    user_repository = MagicMock(spec=UserRepository)

    user_technician = User(
        id=12,
        email="technician@gmail.com",
        password_hash="password_hash",
        full_name="SYLLA",
        role=UserRole.TECHNICIAN,
        is_active=True,
    )

    expected_incident = Incident(
        id=42,
        title="Incident à traiter",
        description="Un incident nécessitant une intervention.",
        category=IncidentCategory.ANOMALY,
        priority=IncidentPriority.MEDIUM,
        status=IncidentStatus.OPEN,
        created_by_id=10,
        assigned_to_id=9999,
    )

    incident_repository.get_by_id.return_value = expected_incident

    service = IncidentService(
        incident_repository,
        incident_history_repository,
        audit_repository,
        user_repository,
    )

    assert expected_incident.status is IncidentStatus.OPEN

    user_repository.get_by_id.return_value = user_technician

    with pytest.raises(NotEnoughAuthorization):
        service.change_status(
            incident_id=expected_incident.id,
            new_status=IncidentStatus.IN_PROGRESS,
            actor_id=user_technician.id,
        )

    incident_history_repository.create.assert_not_called()
    audit_repository.create.assert_not_called()


def build_change_status_context(
    *,
    actor_role: UserRole = UserRole.TECHNICIAN,
    incident_status: IncidentStatus = IncidentStatus.OPEN,
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
        email="actor@example.com",
        password_hash="password_hash",
        full_name="Test Actor",
        role=actor_role,
        is_active=True,
    )

    incident = Incident(
        id=42,
        title="Incident à traiter",
        description="Un incident nécessitant une intervention.",
        category=IncidentCategory.ANOMALY,
        priority=IncidentPriority.MEDIUM,
        status=incident_status,
        created_by_id=10,
        assigned_to_id=assigned_to_id,
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


def test_change_status_to_same_value() -> None:
    (
        service,
        incident,
        actor,
        incident_repository,
        user_repository,
        incident_history_repository,
        audit_repository,
    ) = build_change_status_context(
        incident_status=IncidentStatus.IN_PROGRESS,
    )

    result = service.change_status(
        incident_id=incident.id,
        new_status=IncidentStatus.IN_PROGRESS,
        actor_id=actor.id,
    )

    assert result is incident
    assert result.status == IncidentStatus.IN_PROGRESS
    assert result.assigned_to_id == actor.id

    incident_repository.get_by_id.assert_called_once_with(
        incident_id=incident.id
    )

    user_repository.get_by_id.assert_called_once_with(
        user_id=actor.id
    )

    incident_history_repository.create.assert_not_called()
    audit_repository.create.assert_not_called()


@pytest.mark.parametrize(
    "actor_role, assigned_to_id, current_status, new_status, expected_error",
    [
        pytest.param(
            UserRole.USER,
            12,
            IncidentStatus.OPEN,
            IncidentStatus.IN_PROGRESS,
            NotEnoughAuthorization,
            id="user-forbidden",
        ),
        pytest.param(
            UserRole.ADMIN,
            99,
            IncidentStatus.OPEN,
            IncidentStatus.IN_PROGRESS,
            NotEnoughAuthorization,
            id="admin-not-assigned",
        ),
        pytest.param(
            UserRole.TECHNICIAN,
            None,
            IncidentStatus.OPEN,
            IncidentStatus.IN_PROGRESS,
            IncidentWithoutAssignmentError,
            id="incident-without-assignment",
        ),
        pytest.param(
            UserRole.TECHNICIAN,
            12,
            IncidentStatus.CLOSED,
            IncidentStatus.IN_PROGRESS,
            IncidentStatusClosedError,
            id="incident-closed",
        ),
        pytest.param(
            UserRole.TECHNICIAN,
            12,
            IncidentStatus.RESOLVED,
            IncidentStatus.IN_PROGRESS,
            IncidentStatusResolvedError,
            id="incident-resolved",
        ),
        pytest.param(
            UserRole.TECHNICIAN,
            12,
            IncidentStatus.OPEN,
            IncidentStatus.RESOLVED,
            InvalidStatusTransitionError,
            id="open-to-resolved",
        ),
        pytest.param(
            UserRole.TECHNICIAN,
            12,
            IncidentStatus.OPEN,
            IncidentStatus.CLOSED,
            InvalidStatusTransitionError,
            id="open-to-closed",
        ),
        pytest.param(
            UserRole.TECHNICIAN,
            12,
            IncidentStatus.IN_PROGRESS,
            IncidentStatus.OPEN,
            InvalidStatusTransitionError,
            id="in-progress-to-open",
        ),
        pytest.param(
            UserRole.TECHNICIAN,
            12,
            IncidentStatus.IN_PROGRESS,
            IncidentStatus.RESOLVED,
            InvalidStatusTransitionError,
            id="in-progress-to-resolved",
        ),
        pytest.param(
            UserRole.TECHNICIAN,
            12,
            IncidentStatus.OPEN,
            IncidentStatus.OPEN,
            InvalidStatusTransitionError,
            id="open-to-open",
        ),
    ],
)
def test_change_status_rejected(
    actor_role: UserRole,
    assigned_to_id: int | None,
    current_status: IncidentStatus,
    new_status: IncidentStatus,
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
    ) = build_change_status_context(
        actor_role=actor_role,
        incident_status=current_status,
        assigned_to_id=assigned_to_id,
    )

    old_status = incident.status
    old_assignee = incident.assigned_to_id

    print(f"{expected_error=}, {type(expected_error)=}")

    with pytest.raises(expected_error):
        service.change_status(
            incident_id=incident.id,
            new_status=new_status,
            actor_id=actor.id,
        )

    # L'incident ne doit pas être modifié
    assert incident.status == old_status
    assert incident.assigned_to_id == old_assignee

    incident_repository.get_by_id.assert_called_once_with(
        incident_id=incident.id
    )

    user_repository.get_by_id.assert_called_once_with(
        user_id=actor.id
    )

    # Aucun historique ni audit de succès
    incident_history_repository.create.assert_not_called()
    audit_repository.create.assert_not_called()

    


def test_change_status_incident_not_found() -> None:
    (
        service,
        incident,
        actor,
        incident_repository,
        user_repository,
        incident_history_repository,
        audit_repository,
    ) = build_change_status_context(
        incident_exists=False,
    )

    with pytest.raises(IncidentNotFoundError):
        service.change_status(
            incident_id=9999999,
            new_status=IncidentStatus.IN_PROGRESS,
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


def test_change_status_actor_not_found() -> None:
    (
        service,
        incident,
        actor,
        incident_repository,
        user_repository,
        incident_history_repository,
        audit_repository,
    ) = build_change_status_context(
        actor_exists=False,
    )

    old_status = incident.status

    with pytest.raises(UserNotFoundError):
        service.change_status(
            incident_id=incident.id,
            new_status=IncidentStatus.IN_PROGRESS,
            actor_id=9999999,
        )

    user_repository.get_by_id.assert_called_once_with(
        user_id=9999999
    )

    incident_repository.get_by_id.assert_called_once_with(
        incident_id=incident.id
    )

    assert incident.status == old_status

    incident_history_repository.create.assert_not_called()
    audit_repository.create.assert_not_called()
