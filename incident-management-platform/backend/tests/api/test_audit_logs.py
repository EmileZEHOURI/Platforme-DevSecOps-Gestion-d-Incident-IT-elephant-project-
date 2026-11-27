import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.main import app


def test_admin_can_list_audit_logs(db_session, admin_user):
    previous_overrides = app.dependency_overrides.copy()

    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: admin_user

    try:
        with TestClient(
            app,
            client=("127.0.0.1", 50000),
        ) as client:
            response = client.get(
                "/audit-logs",
                params={"page": 1, "page_size": 20},
            )

        assert response.status_code == 200

        data = response.json()

        assert isinstance(data["items"], list)
        assert isinstance(data["total"], int)
        assert data["page"] == 1
        assert data["page_size"] == 20
        assert isinstance(data["total_pages"], int)
        assert isinstance(data["has_next"], bool)
        assert isinstance(data["has_previous"], bool)

    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)


def test_non_admin_cannot_list_audit_logs(db_session, test_user):
    previous_overrides = app.dependency_overrides.copy()

    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: test_user

    try:
        with TestClient(
            app,
            client=("127.0.0.1", 50000),
        ) as client:
            response = client.get("/audit-logs")

        assert response.status_code == 403

    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)


@pytest.mark.parametrize(
    "params",
    [
        {"page": 0},
        {"page": -1},
        {"page_size": 0},
        {"page_size": 101},
        {"page": "invalid"},
    ],
)
def test_audit_logs_invalid_pagination(
    db_session,
    admin_user,
    params,
):
    previous_overrides = app.dependency_overrides.copy()

    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: admin_user

    try:
        with TestClient(
            app,
            client=("127.0.0.1", 50000),
        ) as client:
            response = client.get(
                "/audit-logs",
                params=params,
            )

        assert response.status_code == 422

    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)

