
from datetime import UTC, datetime
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
def audit_service_setup():
    user_repository = MagicMock(spec=UserRepository)
    audit_repository = MagicMock(spec=AuditRepository)

    user_repository.get_by_id.return_value = SimpleNamespace(
        id=1,
        role=UserRole.ADMIN,
    )

    audit_repository.count_all.return_value = 2
    audit_repository.list_all.return_value = [
        SimpleNamespace(id=10),
        SimpleNamespace(id=11),
    ]

    service = AuditService(
        user_repository=user_repository,
        audit_repository=audit_repository,
    )

    return service, user_repository, audit_repository


def test_service_forwards_date_filters(
    audit_service_setup,
):
    service, user_repository, audit_repository = (
        audit_service_setup
    )

    date_from = datetime(
        2026, 11, 1, tzinfo=UTC
    )
    date_to = datetime(
        2026, 11, 25, tzinfo=UTC
    )

    result = service.paginate_audit_logs(
        actor_id=1,
        page=1,
        page_size=20,
        user_id=12,
        event_type=AuditEventType.LOGIN_FAILURE,
        result=AuditResult.FAILURE,
        date_from=date_from,
        date_to=date_to,
    )

    audit_repository.count_all.assert_called_once_with(
        user_id=12,
        event_type=AuditEventType.LOGIN_FAILURE,
        result=AuditResult.FAILURE,
        date_from=date_from,
        date_to=date_to,
    )

    audit_repository.list_all.assert_called_once_with(
        limit=20,
        offset=0,
        user_id=12,
        event_type=AuditEventType.LOGIN_FAILURE,
        result=AuditResult.FAILURE,
        date_from=date_from,
        date_to=date_to,
    )

    assert result["total"] == 2
    assert len(result["items"]) == 2


def test_service_rejects_inverted_date_range(
    audit_service_setup,
):
    service, user_repository, audit_repository = (
        audit_service_setup
    )

    with pytest.raises(
        audit_service_module.InvalidAuditDateRangeError
    ):
        service.paginate_audit_logs(
            actor_id=1,
            date_from=datetime(
                2026, 11, 25, tzinfo=UTC
            ),
            date_to=datetime(
                2026, 11, 1, tzinfo=UTC
            ),
        )

    audit_repository.count_all.assert_not_called()
    audit_repository.list_all.assert_not_called()


@pytest.mark.parametrize(
    "date_from,date_to",
    [
        (
            datetime(2026, 11, 1, tzinfo=UTC),
            None,
        ),
        (
            None,
            datetime(2026, 11, 25, tzinfo=UTC),
        ),
    ],
)
def test_service_accepts_single_date_bound(
    audit_service_setup,
    date_from,
    date_to,
):
    service, user_repository, audit_repository = (
        audit_service_setup
    )

    result = service.paginate_audit_logs(
        actor_id=1,
        date_from=date_from,
        date_to=date_to,
    )

    assert result["total"] == 2

    assert (
        audit_repository.count_all.call_args.kwargs[
            "date_from"
        ]
        == date_from
    )

    assert (
        audit_repository.list_all.call_args.kwargs[
            "date_to"
        ]
        == date_to
    )


def test_service_accepts_identical_date_bounds(
    audit_service_setup,
):
    service, user_repository, audit_repository = (
        audit_service_setup
    )

    date = datetime(
        2026, 11, 25, 12, tzinfo=UTC
    )

    service.paginate_audit_logs(
        actor_id=1,
        date_from=date,
        date_to=date,
    )

    audit_repository.count_all.assert_called_once()
    audit_repository.list_all.assert_called_once()
