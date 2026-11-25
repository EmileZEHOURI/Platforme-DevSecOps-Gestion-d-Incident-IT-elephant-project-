
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.main import app
from app.models.audit_log import AuditLog
from app.models.enums import AuditEventType, AuditResult


@pytest.fixture
def admin_client(db_session, admin_user):
    previous_overrides = app.dependency_overrides.copy()

    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = (
        lambda: admin_user
    )

    try:
        with TestClient(
            app,
            client=("127.0.0.1", 50000),
        ) as client:
            yield client

    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)


@pytest.fixture
def audit_logs_with_dates(db_session, test_user):
    dates = [
        datetime(2045, 3, 10, 10, tzinfo=timezone.utc),
        datetime(2045, 3, 11, 10, tzinfo=timezone.utc),
        datetime(2045, 3, 12, 10, tzinfo=timezone.utc),
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


def test_api_filters_audit_logs_by_date_range(
    admin_client,
    test_user,
    audit_logs_with_dates,
):
    response = admin_client.get(
        "/audit-logs",
        params={
            "user_id": test_user.id,
            "event_type": AuditEventType.LOGIN_FAILURE.value,
            "result": AuditResult.FAILURE.value,
            "date_from": "2045-03-11T10:00:00Z",
            "date_to": "2045-03-12T10:00:00Z",
            "page": 1,
            "page_size": 20,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 2
    assert data["total_pages"] == 1

    ids = [log["id"] for log in data["items"]]

    assert ids == [
        audit_logs_with_dates[2].id,
        audit_logs_with_dates[1].id,
    ]


def test_api_accepts_date_from_only(
    admin_client,
    test_user,
    audit_logs_with_dates,
):
    response = admin_client.get(
        "/audit-logs",
        params={
            "user_id": test_user.id,
            "event_type": AuditEventType.LOGIN_FAILURE.value,
            "date_from": "2045-03-12T10:00:00Z",
        },
    )

    assert response.status_code == 200

    ids = {
        log["id"] for log in response.json()["items"]
    }

    assert audit_logs_with_dates[2].id in ids
    assert audit_logs_with_dates[0].id not in ids
    assert audit_logs_with_dates[1].id not in ids


def test_api_accepts_date_to_only(
    admin_client,
    test_user,
    audit_logs_with_dates,
):
    response = admin_client.get(
        "/audit-logs",
        params={
            "user_id": test_user.id,
            "event_type": AuditEventType.LOGIN_FAILURE.value,
            "date_to": "2045-03-11T10:00:00Z",
        },
    )

    assert response.status_code == 200

    ids = {
        log["id"] for log in response.json()["items"]
    }

    assert audit_logs_with_dates[0].id in ids
    assert audit_logs_with_dates[1].id in ids
    assert audit_logs_with_dates[2].id not in ids


def test_api_rejects_inverted_date_range(
    admin_client,
):
    response = admin_client.get(
        "/audit-logs",
        params={
            "date_from": "2026-11-25T00:00:00Z",
            "date_to": "2026-11-01T00:00:00Z",
        },
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "params",
    [
        {
            "date_from": "invalid-date",
        },
        {
            "date_to": "invalid-date",
        },
    ],
)
def test_api_rejects_invalid_date_format(
    admin_client,
    params,
):
    response = admin_client.get(
        "/audit-logs",
        params=params,
    )

    assert response.status_code == 422
