
from datetime import UTC, datetime

import pytest

from app.models.audit_log import AuditLog
from app.models.enums import AuditEventType, AuditResult
from app.repositories.audit_repository import AuditRepository


@pytest.fixture
def dated_audit_logs(db_session, test_user):
    dates = [
        datetime(2045, 2, 10, 10, tzinfo=UTC),
        datetime(2045, 2, 11, 10, tzinfo=UTC),
        datetime(2045, 2, 12, 10, tzinfo=UTC),
        datetime(2045, 2, 13, 10, tzinfo=UTC),
    ]

    logs = [
        AuditLog(
            user_id=test_user.id,
            event_type=AuditEventType.LOGIN_FAILURE.value,
            result=AuditResult.FAILURE,
            created_at=date,
        )
        for date in dates
    ]

    db_session.add_all(logs)
    db_session.flush()

    return logs


def test_filter_audit_logs_between_two_dates(
    db_session,
    test_user,
    dated_audit_logs,
):
    repository = AuditRepository(db_session)

    results = repository.list_all(
        user_id=test_user.id,
        event_type=AuditEventType.LOGIN_FAILURE,
        result=AuditResult.FAILURE,
        date_from=datetime(
            2045, 2, 11, 10, tzinfo=UTC
        ),
        date_to=datetime(
            2045, 2, 12, 10, tzinfo=UTC
        ),
    )

    ids = [log.id for log in results]

    assert ids == [
        dated_audit_logs[2].id,
        dated_audit_logs[1].id,
    ]


def test_filter_audit_logs_with_date_from_only(
    db_session,
    test_user,
    dated_audit_logs,
):
    repository = AuditRepository(db_session)

    results = repository.list_all(
        user_id=test_user.id,
        event_type=AuditEventType.LOGIN_FAILURE,
        date_from=datetime(
            2045, 2, 12, 10, tzinfo=UTC
        ),
    )

    ids = {log.id for log in results}

    assert dated_audit_logs[0].id not in ids
    assert dated_audit_logs[1].id not in ids
    assert dated_audit_logs[2].id in ids
    assert dated_audit_logs[3].id in ids


def test_filter_audit_logs_with_date_to_only(
    db_session,
    test_user,
    dated_audit_logs,
):
    repository = AuditRepository(db_session)

    results = repository.list_all(
        user_id=test_user.id,
        event_type=AuditEventType.LOGIN_FAILURE,
        date_to=datetime(
            2045, 2, 11, 10, tzinfo=UTC
        ),
    )

    ids = {log.id for log in results}

    assert dated_audit_logs[0].id in ids
    assert dated_audit_logs[1].id in ids
    assert dated_audit_logs[2].id not in ids
    assert dated_audit_logs[3].id not in ids


def test_count_all_respects_date_filters(
    db_session,
    test_user,
    dated_audit_logs,
):
    repository = AuditRepository(db_session)

    filters = {
        "user_id": test_user.id,
        "event_type": AuditEventType.LOGIN_FAILURE,
        "result": AuditResult.FAILURE,
        "date_from": datetime(
            2045, 2, 11, 10, tzinfo=UTC
        ),
        "date_to": datetime(
            2045, 2, 12, 10, tzinfo=UTC
        ),
    }

    total = repository.count_all(**filters)
    results = repository.list_all(**filters)

    assert total == 2
    assert len(results) == 2
    assert {log.id for log in results} == {
        dated_audit_logs[1].id,
        dated_audit_logs[2].id,
    }


def test_pagination_respects_date_filters(
    db_session,
    test_user,
    dated_audit_logs,
):
    repository = AuditRepository(db_session)

    filters = {
        "user_id": test_user.id,
        "event_type": AuditEventType.LOGIN_FAILURE,
        "date_from": datetime(
            2045, 2, 11, 10, tzinfo=UTC
        ),
        "date_to": datetime(
            2045, 2, 13, 10, tzinfo=UTC
        ),
    }

    first_page = repository.list_all(
        **filters,
        limit=2,
        offset=0,
    )

    second_page = repository.list_all(
        **filters,
        limit=2,
        offset=2,
    )

    assert [log.id for log in first_page] == [
        dated_audit_logs[3].id,
        dated_audit_logs[2].id,
    ]

    assert [log.id for log in second_page] == [
        dated_audit_logs[1].id,
    ]
