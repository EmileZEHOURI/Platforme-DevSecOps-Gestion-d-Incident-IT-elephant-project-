
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.models.enums import (
    IncidentCategory,
    IncidentPriority,
    IncidentStatus,
    UserRole,
)
from app.services.incident_service import (
    IncidentService,
    NotEnoughAuthorization,
    PaginationError,
    UserNotFoundError,
)

# ============================================================
# HELPERS
# ============================================================


def build_service(
    *,
    role: UserRole = UserRole.ADMIN,
    user_exists: bool = True,
):
    incident_repository = Mock()
    user_repository = Mock()

    if user_exists:
        user_repository.get_by_id.return_value = SimpleNamespace(
            id=7,
            role=role,
        )
    else:
        user_repository.get_by_id.return_value = None

    service = IncidentService(
        incident_repository,
        Mock(),  # IncidentHistoryRepository
        Mock(),  # AuditRepository
        user_repository,
    )

    return service, incident_repository, user_repository


def call_pagination(service, scope: str, **kwargs):
    if scope == "assigned":
        return service.paginate_assigned_incidents(**kwargs)

    if scope == "all":
        return service.paginate_all_incidents(**kwargs)

    raise ValueError(f"Scope inconnu : {scope}")


VALID_SCOPES = [
    pytest.param(
        "assigned",
        UserRole.TECHNICIAN,
        id="technician-assigned",
    ),
    pytest.param(
        "assigned",
        UserRole.ADMIN,
        id="admin-assigned",
    ),
    pytest.param(
        "all",
        UserRole.ADMIN,
        id="admin-all",
    ),
]


# ============================================================
# 1. PAGINATION NOMINALE
# ============================================================


@pytest.mark.parametrize("scope, role", VALID_SCOPES)
def test_pagination_returns_expected_metadata(scope, role):
    service, repository, users = build_service(role=role)

    incidents = [
        SimpleNamespace(id=index)
        for index in range(1, 9)
    ]

    filters = {
        "status": IncidentStatus.OPEN,
        "priority": IncidentPriority.HIGH,
        "category": IncidentCategory.SECURITY,
    }

    if scope == "assigned":
        repository.count_by_assignee.return_value = 23
        repository.list_by_assignee.return_value = incidents
    else:
        repository.count_all.return_value = 23
        repository.list_all.return_value = incidents

    result = call_pagination(
        service,
        scope,
        actor_id=7,
        page=2,
        page_size=8,
        **filters,
    )

    assert result == {
        "items": incidents,
        "total": 23,
        "page": 2,
        "page_size": 8,
        "total_pages": 3,
        "has_next": True,
        "has_previous": True,
    }

    users.get_by_id.assert_called_once_with(user_id=7)

    if scope == "assigned":
        repository.count_by_assignee.assert_called_once_with(
            assignee_id=7,
            **filters,
        )

        repository.list_by_assignee.assert_called_once_with(
            assignee_id=7,
            limit=8,
            offset=8,
            **filters,
        )

        repository.count_all.assert_not_called()
        repository.list_all.assert_not_called()

    else:
        repository.count_all.assert_called_once_with(**filters)

        repository.list_all.assert_called_once_with(
            limit=8,
            offset=8,
            **filters,
        )

        repository.count_by_assignee.assert_not_called()
        repository.list_by_assignee.assert_not_called()


# ============================================================
# 2. PREMIERE PAGE PAR DEFAUT
# ============================================================


@pytest.mark.parametrize("scope, role", VALID_SCOPES)
def test_default_page_and_size(scope, role):
    service, repository, _ = build_service(role=role)

    if scope == "assigned":
        repository.count_by_assignee.return_value = 1
        repository.list_by_assignee.return_value = [
            SimpleNamespace(id=10)
        ]
    else:
        repository.count_all.return_value = 1
        repository.list_all.return_value = [
            SimpleNamespace(id=10)
        ]

    result = call_pagination(
        service,
        scope,
        actor_id=7,
    )

    assert result["page"] == 1
    assert result["page_size"] == 20
    assert result["total"] == 1
    assert result["total_pages"] == 1
    assert result["has_next"] is False
    assert result["has_previous"] is False

    if scope == "assigned":
        kwargs = repository.list_by_assignee.call_args.kwargs
        assert kwargs["limit"] == 20
        assert kwargs["offset"] == 0
    else:
        kwargs = repository.list_all.call_args.kwargs
        assert kwargs["limit"] == 20
        assert kwargs["offset"] == 0


# ============================================================
# 3. AUCUN INCIDENT
# ============================================================


@pytest.mark.parametrize("scope, role", VALID_SCOPES)
def test_no_incidents(scope, role):
    service, repository, _ = build_service(role=role)

    if scope == "assigned":
        repository.count_by_assignee.return_value = 0
        repository.list_by_assignee.return_value = []
    else:
        repository.count_all.return_value = 0
        repository.list_all.return_value = []

    result = call_pagination(
        service,
        scope,
        actor_id=7,
        page=1,
        page_size=10,
    )

    assert result["items"] == []
    assert result["total"] == 0
    assert result["total_pages"] == 0
    assert result["has_next"] is False
    assert result["has_previous"] is False


# ============================================================
# 4. PAGE HORS LIMITES
# ============================================================


@pytest.mark.parametrize("scope, role", VALID_SCOPES)
def test_out_of_range_page_returns_empty_items(scope, role):
    service, repository, _ = build_service(role=role)

    if scope == "assigned":
        repository.count_by_assignee.return_value = 23
        repository.list_by_assignee.return_value = []
    else:
        repository.count_all.return_value = 23
        repository.list_all.return_value = []

    result = call_pagination(
        service,
        scope,
        actor_id=7,
        page=10,
        page_size=8,
    )

    assert result["items"] == []
    assert result["total"] == 23
    assert result["page"] == 10
    assert result["total_pages"] == 3
    assert result["has_next"] is False
    assert result["has_previous"] is True

    if scope == "assigned":
        kwargs = repository.list_by_assignee.call_args.kwargs
    else:
        kwargs = repository.list_all.call_args.kwargs

    assert kwargs["limit"] == 8
    assert kwargs["offset"] == 72


# ============================================================
# 5. VALIDATION DES PARAMETRES
# ============================================================


@pytest.mark.parametrize("scope, role", VALID_SCOPES)
@pytest.mark.parametrize(
    "page, page_size",
    [
        pytest.param(0, 20, id="page-zero"),
        pytest.param(-1, 20, id="negative-page"),
        pytest.param(1, 0, id="size-zero"),
        pytest.param(1, -5, id="negative-size"),
        pytest.param(1, 101, id="size-above-100"),
    ],
)
def test_invalid_pagination_raises_error(
    scope,
    role,
    page,
    page_size,
):
    service, repository, _ = build_service(role=role)

    with pytest.raises(PaginationError):
        call_pagination(
            service,
            scope,
            actor_id=7,
            page=page,
            page_size=page_size,
        )

    repository.count_by_assignee.assert_not_called()
    repository.list_by_assignee.assert_not_called()
    repository.count_all.assert_not_called()
    repository.list_all.assert_not_called()


# ============================================================
# 6. UTILISATEUR INEXISTANT
# ============================================================


@pytest.mark.parametrize("scope, role", VALID_SCOPES)
def test_unknown_user_is_rejected(scope, role):
    service, repository, users = build_service(
        role=role,
        user_exists=False,
    )

    with pytest.raises(UserNotFoundError):
        call_pagination(
            service,
            scope,
            actor_id=999,
        )

    users.get_by_id.assert_called_once_with(user_id=999)

    repository.count_by_assignee.assert_not_called()
    repository.list_by_assignee.assert_not_called()
    repository.count_all.assert_not_called()
    repository.list_all.assert_not_called()


# ============================================================
# 7. AUTORISATIONS
# ============================================================


@pytest.mark.parametrize(
    "scope, role",
    [
        pytest.param(
            "assigned",
            UserRole.USER,
            id="user-cannot-access-assigned",
        ),
        pytest.param(
            "all",
            UserRole.USER,
            id="user-cannot-access-all",
        ),
        pytest.param(
            "all",
            UserRole.TECHNICIAN,
            id="technician-cannot-access-all",
        ),
    ],
)
def test_unauthorized_role_is_rejected(scope, role):
    service, repository, _ = build_service(role=role)

    with pytest.raises(NotEnoughAuthorization):
        call_pagination(
            service,
            scope,
            actor_id=7,
        )

    repository.count_by_assignee.assert_not_called()
    repository.list_by_assignee.assert_not_called()
    repository.count_all.assert_not_called()
    repository.list_all.assert_not_called()


# ============================================================
# 8. DERNIERE PAGE PARTIELLE
# ============================================================


@pytest.mark.parametrize("scope, role", VALID_SCOPES)
def test_last_page_metadata(scope, role):
    service, repository, _ = build_service(role=role)

    incidents = [
        SimpleNamespace(id=21),
        SimpleNamespace(id=22),
        SimpleNamespace(id=23),
    ]

    if scope == "assigned":
        repository.count_by_assignee.return_value = 23
        repository.list_by_assignee.return_value = incidents
    else:
        repository.count_all.return_value = 23
        repository.list_all.return_value = incidents

    result = call_pagination(
        service,
        scope,
        actor_id=7,
        page=3,
        page_size=10,
    )

    assert result["items"] == incidents
    assert result["total"] == 23
    assert result["total_pages"] == 3
    assert result["has_next"] is False
    assert result["has_previous"] is True

    if scope == "assigned":
        kwargs = repository.list_by_assignee.call_args.kwargs
    else:
        kwargs = repository.list_all.call_args.kwargs

    assert kwargs["limit"] == 10
    assert kwargs["offset"] == 20
