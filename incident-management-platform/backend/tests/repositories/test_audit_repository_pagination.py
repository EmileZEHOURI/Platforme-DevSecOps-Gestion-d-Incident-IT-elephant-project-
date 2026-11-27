
from datetime import UTC, datetime

from app.models.audit_log import AuditLog
from app.models.enums import AuditEventType, AuditResult
from app.repositories.audit_repository import AuditRepository


def test_count_all_applies_filters(
    db_session,
    test_user,
    admin_user,
):
    repository = AuditRepository(db_session)

    filters = {
        "user_id": test_user.id,
        "event_type": AuditEventType.LOGIN_FAILURE,
        "result": AuditResult.FAILURE,
    }

    initial_total = repository.count_all(**filters)

    logs = [
        AuditLog(
            user_id=test_user.id,
            event_type=AuditEventType.LOGIN_FAILURE.value,
            result=AuditResult.FAILURE,
        ),
        AuditLog(
            user_id=test_user.id,
            event_type=AuditEventType.LOGIN_FAILURE.value,
            result=AuditResult.FAILURE,
        ),
        AuditLog(
            user_id=admin_user.id,
            event_type=AuditEventType.LOGIN_FAILURE.value,
            result=AuditResult.FAILURE,
        ),
        AuditLog(
            user_id=test_user.id,
            event_type=AuditEventType.LOGIN_SUCCESS.value,
            result=AuditResult.SUCCESS,
        ),
    ]

    db_session.add_all(logs)
    db_session.flush()

    assert repository.count_all(**filters) == initial_total + 2

    results = repository.list_all(**filters)
    result_ids = {log.id for log in results}

    assert logs[0].id in result_ids
    assert logs[1].id in result_ids
    assert logs[2].id not in result_ids
    assert logs[3].id not in result_ids


def test_list_all_applies_ordering_and_pagination(
    db_session,
    admin_user,
):
    repository = AuditRepository(db_session)

    timestamps = [
        datetime(2030, 1, 1, tzinfo=UTC),
        datetime(2030, 1, 2, tzinfo=UTC),
        datetime(2030, 1, 2, tzinfo=UTC),
        datetime(2030, 1, 3, tzinfo=UTC),
    ]

    logs = [
        AuditLog(
            user_id=admin_user.id,
            event_type=AuditEventType.LOGIN_SUCCESS.value,
            result=AuditResult.SUCCESS,
            created_at=timestamp,
        )
        for timestamp in timestamps
    ]

    db_session.add_all(logs)
    db_session.flush()

    filters = {
        "user_id": admin_user.id,
        "event_type": AuditEventType.LOGIN_SUCCESS,
    }

    all_logs = repository.list_all(**filters)

    assert [log.id for log in all_logs] == [
        log.id
        for log in sorted(
            all_logs,
            key=lambda log: (log.created_at, log.id),
            reverse=True,
        )
    ]

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
        log.id for log in all_logs[:2]
    ]

    assert [log.id for log in second_page] == [
        log.id for log in all_logs[2:4]
    ]


def test_count_and_list_return_empty_results(
    db_session,
):
    repository = AuditRepository(db_session)

    filters = {
        "user_id": -999999,
        "event_type": AuditEventType.LOGIN_FAILURE,
    }

    assert repository.count_all(**filters) == 0
    assert repository.list_all(**filters) == []
