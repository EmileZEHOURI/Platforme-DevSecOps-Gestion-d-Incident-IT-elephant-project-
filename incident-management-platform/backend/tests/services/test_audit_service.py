from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.models.enums import AuditEventType, AuditResult
from app.models.user import UserRole
from app.repositories.audit_repository import AuditRepository
from app.repositories.user_repository import UserRepository
from app.services import audit_service as audit_service_module
from app.services.audit_service import AuditService


@pytest.fixture
def repositories():
    user_repository = MagicMock(spec=UserRepository)
    audit_repository = MagicMock(spec=AuditRepository)

    return user_repository, audit_repository


@pytest.fixture
def service(repositories):
    user_repository, audit_repository = repositories

    return AuditService(
        user_repository=user_repository,
        audit_repository=audit_repository,
    )


def test_admin_can_paginate_audit_logs(service, repositories):
    user_repository, audit_repository = repositories

    user_repository.get_by_id.return_value = SimpleNamespace(
        id=1,
        role=UserRole.ADMIN,
    )

    audit_repository.count_all.return_value = 47

    logs = [SimpleNamespace(id=i) for i in range(41, 48)]
    audit_repository.list_all.return_value = logs

    result = service.paginate_audit_logs(
        actor_id=1,
        page=3,
        page_size=20,
    )

    assert result["items"] == logs
    assert result["total"] == 47
    assert result["page"] == 3
    assert result["page_size"] == 20
    assert result["total_pages"] == 3
    assert result["has_next"] is False
    assert result["has_previous"] is True

    user_repository.get_by_id.assert_called_once_with(user_id=1)

    audit_repository.count_all.assert_called_once_with(
        user_id=None,
        event_type=None,
        result=None,
        date_from=None,
        date_to=None,
    )

    audit_repository.list_all.assert_called_once_with(
        limit=20,
        offset=40,
        user_id=None,
        event_type=None,
        result=None,
        date_from=None,
        date_to=None,
    )


def test_audit_service_forwards_filters(service, repositories):
    user_repository, audit_repository = repositories

    user_repository.get_by_id.return_value = SimpleNamespace(
        id=1,
        role=UserRole.ADMIN,
    )

    audit_repository.count_all.return_value = 5
    audit_repository.list_all.return_value = []

    service.paginate_audit_logs(
        actor_id=1,
        user_id=12,
        event_type=AuditEventType.LOGIN_FAILURE,
        result=AuditResult.FAILURE,
    )

    audit_repository.count_all.assert_called_once_with(
        user_id=12,
        event_type=AuditEventType.LOGIN_FAILURE,
        result=AuditResult.FAILURE,
        date_from=None,
        date_to=None,
    )

    audit_repository.list_all.assert_called_once_with(
        limit=20,
        offset=0,
        user_id=12,
        event_type=AuditEventType.LOGIN_FAILURE,
        result=AuditResult.FAILURE,
        date_from=None,
        date_to=None,
    )


def test_missing_actor_cannot_read_audit_logs(service, repositories):
    user_repository, audit_repository = repositories

    user_repository.get_by_id.return_value = None

    with pytest.raises(audit_service_module.UserNotFoundError):
        service.paginate_audit_logs(actor_id=999)

    audit_repository.count_all.assert_not_called()
    audit_repository.list_all.assert_not_called()


@pytest.mark.parametrize(
    "role",
    [UserRole.USER, UserRole.TECHNICIAN],
)
def test_non_admin_cannot_read_audit_logs(
    service,
    repositories,
    role,
):
    user_repository, audit_repository = repositories

    user_repository.get_by_id.return_value = SimpleNamespace(
        id=2,
        role=role,
    )

    with pytest.raises(audit_service_module.NotEnoughAuthorization):
        service.paginate_audit_logs(actor_id=2)

    audit_repository.count_all.assert_not_called()
    audit_repository.list_all.assert_not_called()


@pytest.mark.parametrize(
    "page,page_size",
    [
        (0, 20),
        (-1, 20),
        (1, 0),
        (1, 101),
    ],
)
def test_invalid_pagination_raises_error(
    service,
    repositories,
    page,
    page_size,
):
    user_repository, audit_repository = repositories

    user_repository.get_by_id.return_value = SimpleNamespace(
        id=1,
        role=UserRole.ADMIN,
    )

    with pytest.raises(audit_service_module.PaginationError):
        service.paginate_audit_logs(
            actor_id=1,
            page=page,
            page_size=page_size,
        )

    audit_repository.count_all.assert_not_called()
    audit_repository.list_all.assert_not_called()


def test_empty_audit_logs(service, repositories):
    user_repository, audit_repository = repositories

    user_repository.get_by_id.return_value = SimpleNamespace(
        id=1,
        role=UserRole.ADMIN,
    )

    audit_repository.count_all.return_value = 0
    audit_repository.list_all.return_value = []

    result = service.paginate_audit_logs(
        actor_id=1,
        page=1,
        page_size=20,
    )

    assert result["items"] == []
    assert result["total"] == 0
    assert result["total_pages"] == 0
    assert result["has_next"] is False
    assert result["has_previous"] is False


def test_page_beyond_available_results(service, repositories):
    user_repository, audit_repository = repositories

    user_repository.get_by_id.return_value = SimpleNamespace(
        id=1,
        role=UserRole.ADMIN,
    )

    audit_repository.count_all.return_value = 47
    audit_repository.list_all.return_value = []

    result = service.paginate_audit_logs(
        actor_id=1,
        page=10,
        page_size=20,
    )

    assert result["items"] == []
    assert result["total"] == 47
    assert result["total_pages"] == 3
    assert result["has_next"] is False
    assert result["has_previous"] is True

    audit_repository.list_all.assert_called_once_with(
        limit=20,
        offset=180,
        user_id=None,
        event_type=None,
        result=None,
        date_from=None,
        date_to=None,
    )
