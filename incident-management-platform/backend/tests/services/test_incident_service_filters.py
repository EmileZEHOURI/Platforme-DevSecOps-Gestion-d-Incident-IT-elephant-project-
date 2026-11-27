
from itertools import product
from types import SimpleNamespace
from unittest.mock import MagicMock, call

import pytest

from app.models.enums import (
    IncidentCategory,
    IncidentPriority,
    IncidentStatus,
    UserRole,
)
from app.repositories.audit_repository import AuditRepository
from app.repositories.incident_history_repository import (
    IncidentHistoryRepository,
)
from app.repositories.incident_repository import IncidentRepository
from app.repositories.user_repository import UserRepository
from app.services.incident_service import (
    IncidentService,
    NotEnoughAuthorization,
    UserNotFoundError,
)

# ==========================================================
# FIXTURES
# ==========================================================


@pytest.fixture
def incident_repository():
    return MagicMock(spec=IncidentRepository)


@pytest.fixture
def incident_history_repository():
    return MagicMock(spec=IncidentHistoryRepository)


@pytest.fixture
def audit_repository():
    return MagicMock(spec=AuditRepository)


@pytest.fixture
def user_repository():
    return MagicMock(spec=UserRepository)


@pytest.fixture
def incident_service(
    incident_repository,
    incident_history_repository,
    audit_repository,
    user_repository,
):
    return IncidentService(
        incident_repository,
        incident_history_repository,
        audit_repository,
        user_repository,
    )


@pytest.fixture
def technician():
    return SimpleNamespace(
        id=10,
        role=UserRole.TECHNICIAN,
    )


@pytest.fixture
def admin():
    return SimpleNamespace(
        id=20,
        role=UserRole.ADMIN,
    )


@pytest.fixture
def incidents():
    return [
        SimpleNamespace(
            id=1,
            assigned_to_id=10,
            status=IncidentStatus.OPEN,
            priority=IncidentPriority.HIGH,
            category=IncidentCategory.SECURITY,
        ),
        SimpleNamespace(
            id=2,
            assigned_to_id=10,
            status=IncidentStatus.OPEN,
            priority=IncidentPriority.HIGH,
            category=IncidentCategory.SECURITY,
        ),
    ]


# Les huit combinaisons possibles de filtres.
FILTER_COMBINATIONS = list(
    product(
        [None, IncidentStatus.OPEN],
        [None, IncidentPriority.HIGH],
        [None, IncidentCategory.SECURITY],
    )
)


# ==========================================================
# 1. UTILISATEURS AUTORISES
# Total : 2 tests
# ==========================================================


def test_technician_can_list_assigned_incidents(
    incident_service,
    incident_repository,
    user_repository,
    technician,
    incidents,
):
    user_repository.get_by_id.return_value = technician
    incident_repository.list_by_assignee.return_value = incidents

    result = incident_service.list_assigned_incidents(
        actor_id=technician.id,
    )

    assert result == incidents

    user_repository.get_by_id.assert_called_once_with(
        user_id=technician.id,
    )

    incident_repository.list_by_assignee.assert_called_once_with(
        assignee_id=technician.id,
        status=None,
        priority=None,
        category=None,
    )


def test_admin_can_list_all_incidents(
    incident_service,
    incident_repository,
    user_repository,
    admin,
    incidents,
):
    user_repository.get_by_id.return_value = admin
    incident_repository.list_all.return_value = incidents

    result = incident_service.list_all_incidents(
        actor_id=admin.id,
    )

    assert result == incidents

    user_repository.get_by_id.assert_called_once_with(
        user_id=admin.id,
    )

    incident_repository.list_all.assert_called_once_with(
        status=None,
        priority=None,
        category=None,
    )


# ==========================================================
# 2. UTILISATEURS NON AUTORISES
# Total : 4 tests
# ==========================================================


@pytest.mark.parametrize(
    "role",
    [
        UserRole.USER,
    ],
)



def test_non_technician_cannot_list_assigned_incidents(
    incident_service,
    incident_repository,
    user_repository,
    role,
):
    actor = SimpleNamespace(
        id=42,
        role=role,
    )

    user_repository.get_by_id.return_value = actor

    with pytest.raises(NotEnoughAuthorization):
        incident_service.list_assigned_incidents(
            actor_id=actor.id,
            status=IncidentStatus.OPEN,
            priority=IncidentPriority.HIGH,
            category=IncidentCategory.SECURITY,
        )

    user_repository.get_by_id.assert_called_once_with(
        user_id=actor.id,
    )

    assert incident_repository.mock_calls == []


@pytest.mark.parametrize(
    "role",
    [
        UserRole.USER,
        UserRole.TECHNICIAN,
    ],
)
def test_non_admin_cannot_list_all_incidents(
    incident_service,
    incident_repository,
    user_repository,
    role,
):
    actor = SimpleNamespace(
        id=42,
        role=role,
    )

    user_repository.get_by_id.return_value = actor

    with pytest.raises(NotEnoughAuthorization):
        incident_service.list_all_incidents(
            actor_id=actor.id,
            status=IncidentStatus.OPEN,
            priority=IncidentPriority.HIGH,
            category=IncidentCategory.SECURITY,
        )

    user_repository.get_by_id.assert_called_once_with(
        user_id=actor.id,
    )

    assert incident_repository.mock_calls == []


# ==========================================================
# 3. UTILISATEURS INEXISTANTS
# Total : 2 tests
# ==========================================================


def test_missing_user_cannot_list_assigned_incidents(
    incident_service,
    incident_repository,
    user_repository,
):
    user_repository.get_by_id.return_value = None

    with pytest.raises(UserNotFoundError):
        incident_service.list_assigned_incidents(
            actor_id=999,
        )

    user_repository.get_by_id.assert_called_once_with(
        user_id=999,
    )

    assert incident_repository.mock_calls == []


def test_missing_user_cannot_list_all_incidents(
    incident_service,
    incident_repository,
    user_repository,
):
    user_repository.get_by_id.return_value = None

    with pytest.raises(UserNotFoundError):
        incident_service.list_all_incidents(
            actor_id=999,
        )

    user_repository.get_by_id.assert_called_once_with(
        user_id=999,
    )

    assert incident_repository.mock_calls == []


# ==========================================================
# 4. COMBINAISONS DE FILTRES - TECHNICIEN
# Total : 8 tests
# ==========================================================


@pytest.mark.parametrize(
    "status, priority, category",
    FILTER_COMBINATIONS,
    ids=[
        "no-filters",
        "category-only",
        "priority-only",
        "priority-and-category",
        "status-only",
        "status-and-category",
        "status-and-priority",
        "all-filters",
    ],
)
def test_assigned_incidents_with_filter_combinations(
    incident_service,
    incident_repository,
    user_repository,
    technician,
    incidents,
    status,
    priority,
    category,
):
    user_repository.get_by_id.return_value = technician
    incident_repository.list_by_assignee.return_value = incidents

    result = incident_service.list_assigned_incidents(
        actor_id=technician.id,
        status=status,
        priority=priority,
        category=category,
    )

    assert result == incidents

    user_repository.get_by_id.assert_called_once_with(
        user_id=technician.id,
    )

    incident_repository.list_by_assignee.assert_called_once_with(
        assignee_id=technician.id,
        status=status,
        priority=priority,
        category=category,
    )

    incident_repository.list_all.assert_not_called()


# ==========================================================
# 5. COMBINAISONS DE FILTRES - ADMINISTRATEUR
# Total : 8 tests
# ==========================================================


@pytest.mark.parametrize(
    "status, priority, category",
    FILTER_COMBINATIONS,
    ids=[
        "no-filters",
        "category-only",
        "priority-only",
        "priority-and-category",
        "status-only",
        "status-and-category",
        "status-and-priority",
        "all-filters",
    ],
)
def test_all_incidents_with_filter_combinations(
    incident_service,
    incident_repository,
    user_repository,
    admin,
    incidents,
    status,
    priority,
    category,
):
    user_repository.get_by_id.return_value = admin
    incident_repository.list_all.return_value = incidents

    result = incident_service.list_all_incidents(
        actor_id=admin.id,
        status=status,
        priority=priority,
        category=category,
    )

    assert result == incidents

    user_repository.get_by_id.assert_called_once_with(
        user_id=admin.id,
    )

    incident_repository.list_all.assert_called_once_with(
        status=status,
        priority=priority,
        category=category,
    )

    incident_repository.list_by_assignee.assert_not_called()


# ==========================================================
# 6. AUCUN INCIDENT CORRESPONDANT
# Total : 2 tests
# ==========================================================


def test_assigned_incidents_returns_empty_list(
    incident_service,
    incident_repository,
    user_repository,
    technician,
):
    user_repository.get_by_id.return_value = technician
    incident_repository.list_by_assignee.return_value = []

    result = incident_service.list_assigned_incidents(
        actor_id=technician.id,
        status=IncidentStatus.CLOSED,
        priority=IncidentPriority.CRITICAL,
        category=IncidentCategory.SECURITY,
    )

    assert result == []

    incident_repository.list_by_assignee.assert_called_once_with(
        assignee_id=technician.id,
        status=IncidentStatus.CLOSED,
        priority=IncidentPriority.CRITICAL,
        category=IncidentCategory.SECURITY,
    )


def test_all_incidents_returns_empty_list(
    incident_service,
    incident_repository,
    user_repository,
    admin,
):
    user_repository.get_by_id.return_value = admin
    incident_repository.list_all.return_value = []

    result = incident_service.list_all_incidents(
        actor_id=admin.id,
        status=IncidentStatus.CLOSED,
        priority=IncidentPriority.CRITICAL,
        category=IncidentCategory.SECURITY,
    )

    assert result == []

    incident_repository.list_all.assert_called_once_with(
        status=IncidentStatus.CLOSED,
        priority=IncidentPriority.CRITICAL,
        category=IncidentCategory.SECURITY,
    )


# ==========================================================
# 7. SECURITE ET ISOLATION DES REQUETES
# Total : 2 tests
# ==========================================================


def test_technician_never_calls_global_incident_list(
    incident_service,
    incident_repository,
    user_repository,
    technician,
):
    user_repository.get_by_id.return_value = technician

    assigned_incidents = [
        SimpleNamespace(
            id=1,
            assigned_to_id=technician.id,
        )
    ]

    all_incidents = [
        SimpleNamespace(
            id=1,
            assigned_to_id=technician.id,
        ),
        SimpleNamespace(
            id=2,
            assigned_to_id=999,
        ),
        SimpleNamespace(
            id=3,
            assigned_to_id=None,
        ),
    ]

    incident_repository.list_by_assignee.return_value = (
        assigned_incidents
    )

    incident_repository.list_all.return_value = all_incidents

    result = incident_service.list_assigned_incidents(
        actor_id=technician.id,
        status=IncidentStatus.OPEN,
    )

    assert result == assigned_incidents

    incident_repository.list_by_assignee.assert_called_once_with(
        assignee_id=technician.id,
        status=IncidentStatus.OPEN,
        priority=None,
        category=None,
    )

    incident_repository.list_all.assert_not_called()

    assert all(
        incident.assigned_to_id == technician.id
        for incident in result
    )


def test_admin_global_list_is_not_restricted_to_assignment(
    incident_service,
    incident_repository,
    user_repository,
    admin,
):
    user_repository.get_by_id.return_value = admin

    all_incidents = [
        SimpleNamespace(
            id=1,
            assigned_to_id=10,
        ),
        SimpleNamespace(
            id=2,
            assigned_to_id=11,
        ),
        SimpleNamespace(
            id=3,
            assigned_to_id=None,
        ),
    ]

    incident_repository.list_all.return_value = all_incidents

    result = incident_service.list_all_incidents(
        actor_id=admin.id,
        status=IncidentStatus.OPEN,
    )

    assert result == all_incidents
    assert len(result) == 3

    incident_repository.list_all.assert_called_once_with(
        status=IncidentStatus.OPEN,
        priority=None,
        category=None,
    )

    incident_repository.list_by_assignee.assert_not_called()

    assert any(
        incident.assigned_to_id is None
        for incident in result
    )


# ==========================================================
# 8. CONSULTATION SANS ECRITURE
# Total : 2 tests
# ==========================================================


def test_assigned_incidents_does_not_write_history_or_audit(
    incident_service,
    incident_repository,
    incident_history_repository,
    audit_repository,
    user_repository,
    technician,
    incidents,
):
    user_repository.get_by_id.return_value = technician
    incident_repository.list_by_assignee.return_value = incidents

    result = incident_service.list_assigned_incidents(
        actor_id=technician.id,
        status=IncidentStatus.OPEN,
        priority=IncidentPriority.HIGH,
        category=IncidentCategory.SECURITY,
    )

    assert result == incidents

    assert incident_repository.mock_calls == [
        call.list_by_assignee(
            assignee_id=technician.id,
            status=IncidentStatus.OPEN,
            priority=IncidentPriority.HIGH,
            category=IncidentCategory.SECURITY,
        )
    ]

    assert user_repository.mock_calls == [
        call.get_by_id(user_id=technician.id)
    ]

    assert incident_history_repository.mock_calls == []
    assert audit_repository.mock_calls == []


def test_all_incidents_does_not_write_history_or_audit(
    incident_service,
    incident_repository,
    incident_history_repository,
    audit_repository,
    user_repository,
    admin,
    incidents,
):
    user_repository.get_by_id.return_value = admin
    incident_repository.list_all.return_value = incidents

    result = incident_service.list_all_incidents(
        actor_id=admin.id,
        status=IncidentStatus.OPEN,
        priority=IncidentPriority.HIGH,
        category=IncidentCategory.SECURITY,
    )

    assert result == incidents

    assert incident_repository.mock_calls == [
        call.list_all(
            status=IncidentStatus.OPEN,
            priority=IncidentPriority.HIGH,
            category=IncidentCategory.SECURITY,
        )
    ]

    assert user_repository.mock_calls == [
        call.get_by_id(user_id=admin.id)
    ]

    assert incident_history_repository.mock_calls == []
    assert audit_repository.mock_calls == []


def test_admin_can_list_assigned_incidents(
    incident_service,
    incident_repository,
    user_repository,
    admin,
    incidents,
):
    user_repository.get_by_id.return_value = admin
    incident_repository.list_by_assignee.return_value = incidents

    result = incident_service.list_assigned_incidents(
        actor_id=admin.id,
        status=IncidentStatus.OPEN,
    )

    assert result == incidents

    incident_repository.list_by_assignee.assert_called_once_with(
        assignee_id=admin.id,
        status=IncidentStatus.OPEN,
        priority=None,
        category=None,
    )

    incident_repository.list_all.assert_not_called()