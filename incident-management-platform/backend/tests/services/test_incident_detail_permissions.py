
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.models.enums import UserRole
from app.repositories.incident_repository import (
    IncidentRepository,
)
from app.repositories.incident_history_repository import (
    IncidentHistoryRepository,
)
from app.repositories.audit_repository import (
    AuditRepository,
)
from app.repositories.user_repository import (
    UserRepository,
)
from app.services.incident_service import (
    IncidentService,
    IncidentNotFoundError,
)


def make_service(role, creator_id, assignee_id):
    incident_repository = MagicMock(
        spec=IncidentRepository
    )
    history_repository = MagicMock(
        spec=IncidentHistoryRepository
    )
    audit_repository = MagicMock(
        spec=AuditRepository
    )
    user_repository = MagicMock(
        spec=UserRepository
    )

    actor = SimpleNamespace(
        id=12,
        role=role,
        is_active=True,
    )

    incident = SimpleNamespace(
        id=42,
        created_by_id=creator_id,
        assigned_to_id=assignee_id,
    )

    user_repository.get_by_id.return_value = actor
    incident_repository.get_by_id.return_value = incident

    service = IncidentService(
        incident_repository,
        history_repository,
        audit_repository,
        user_repository,
    )

    return service, incident, incident_repository


@pytest.mark.parametrize(
    "role, creator_id, assignee_id, allowed",
    [
        (UserRole.USER, 12, None, True),
        (UserRole.USER, 99, None, False),
        (UserRole.TECHNICIAN, 12, None, True),
        (UserRole.TECHNICIAN, 99, 12, True),
        (UserRole.TECHNICIAN, 99, 88, False),
        (UserRole.ADMIN, 99, None, True),
    ],
)
def test_incident_detail_permissions(
    role,
    creator_id,
    assignee_id,
    allowed,
):
    service, incident, repository = make_service(
        role,
        creator_id,
        assignee_id,
    )

    if allowed:
        result = service.get_incident_detail(
            incident_id=42,
            actor_id=12,
        )
        assert result is incident
    else:
        with pytest.raises(IncidentNotFoundError):
            service.get_incident_detail(
                incident_id=42,
                actor_id=12,
            )

    repository.get_by_id.assert_called_once_with(
        incident_id=42
    )

    repository.get_by_id_and_creator.assert_not_called()


def test_unknown_incident_returns_not_found():
    service, _, repository = make_service(
        UserRole.ADMIN,
        creator_id=99,
        assignee_id=None,
    )

    repository.get_by_id.return_value = None

    with pytest.raises(IncidentNotFoundError):
        service.get_incident_detail(
            incident_id=999,
            actor_id=12,
        )
