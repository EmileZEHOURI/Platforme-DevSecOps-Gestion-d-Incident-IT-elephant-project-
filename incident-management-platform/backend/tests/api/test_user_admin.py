
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.main import app
from app.models.user import UserRole
from app.repositories.audit_repository import AuditRepository
from app.repositories.incident_repository import IncidentRepository
from app.repositories.user_repository import UserRepository


@pytest.fixture
def client_as(db_session):
    """
    Crée un client API authentifié avec l'utilisateur choisi.
    Réutilise la session PostgreSQL de test.
    """
    previous_db = app.dependency_overrides.get(get_db)
    previous_user = app.dependency_overrides.get(get_current_user)

    def make_client(user):
        app.dependency_overrides[get_db] = lambda: db_session
        app.dependency_overrides[get_current_user] = lambda: user

        return TestClient(
            app,
            client=("127.0.0.1", 50000),
        )

    yield make_client

    if previous_db is None:
        app.dependency_overrides.pop(get_db, None)
    else:
        app.dependency_overrides[get_db] = previous_db

    if previous_user is None:
        app.dependency_overrides.pop(get_current_user, None)
    else:
        app.dependency_overrides[get_current_user] = previous_user


# ============================================================
# GET /users
# ============================================================


def test_admin_can_list_all_users(
    client_as,
    admin_user,
    test_user,
    technician_user,
):
    client = client_as(admin_user)

    response = client.get("/users")

    assert response.status_code == 200

    users = response.json()
    ids = {user["id"] for user in users}

    assert isinstance(users, list)
    assert admin_user.id in ids
    assert test_user.id in ids
    assert technician_user.id in ids

    for user in users:
        assert "password_hash" not in user


def test_admin_can_filter_users_by_role(
    client_as,
    admin_user,
    technician_user,
):
    client = client_as(admin_user)

    response = client.get(
        "/users",
        params={"role": UserRole.TECHNICIAN.value},
    )

    assert response.status_code == 200

    users = response.json()

    assert technician_user.id in {
        user["id"] for user in users
    }

    assert all(
        user["role"] == UserRole.TECHNICIAN.value
        for user in users
    )


def test_admin_can_filter_inactive_users(
    client_as,
    db_session,
    admin_user,
    test_user,
    other_user,
):
    test_user.is_active = True
    other_user.is_active = False
    db_session.flush()

    client = client_as(admin_user)

    response = client.get(
        "/users",
        params={"is_active": "false"},
    )

    assert response.status_code == 200

    users = response.json()
    ids = {user["id"] for user in users}

    assert other_user.id in ids
    assert test_user.id not in ids
    assert all(user["is_active"] is False for user in users)


def test_admin_can_filter_active_users(
    client_as,
    db_session,
    admin_user,
    test_user,
    other_user,
):
    test_user.is_active = True
    other_user.is_active = False
    db_session.flush()

    client = client_as(admin_user)

    response = client.get(
        "/users",
        params={"is_active": "true"},
    )

    assert response.status_code == 200

    users = response.json()
    ids = {user["id"] for user in users}

    assert test_user.id in ids
    assert other_user.id not in ids
    assert all(user["is_active"] is True for user in users)


def test_admin_can_combine_role_and_active_filters(
    client_as,
    db_session,
    admin_user,
    technician_user,
    other_technician_user,
):
    technician_user.is_active = True
    other_technician_user.is_active = False
    db_session.flush()

    client = client_as(admin_user)

    response = client.get(
        "/users",
        params={
            "role": UserRole.TECHNICIAN.value,
            "is_active": "false",
        },
    )

    assert response.status_code == 200

    users = response.json()
    ids = {user["id"] for user in users}

    assert other_technician_user.id in ids
    assert technician_user.id not in ids

    assert all(
        user["role"] == UserRole.TECHNICIAN.value
        and user["is_active"] is False
        for user in users
    )


def test_non_admin_cannot_list_users(
    client_as,
    test_user,
):
    client = client_as(test_user)

    response = client.get("/users")

    assert response.status_code == 403


def test_missing_actor_cannot_list_users(client_as):
    missing_actor = SimpleNamespace(id=999999999)
    client = client_as(missing_actor)

    response = client.get("/users")

    assert response.status_code == 404


@pytest.mark.parametrize(
    "params",
    [
        {"is_active": "invalid"},
        {"role": "INVALID_ROLE"},
    ],
)
def test_list_users_rejects_invalid_filters(
    client_as,
    admin_user,
    params,
):
    client = client_as(admin_user)

    response = client.get("/users", params=params)

    assert response.status_code == 422


def test_list_users_database_error_returns_500(
    client_as,
    admin_user,
    monkeypatch,
):
    def failing_list_all(self, **kwargs):
        raise SQLAlchemyError("Database error")

    monkeypatch.setattr(
        UserRepository,
        "list_all",
        failing_list_all,
    )

    client = client_as(admin_user)

    response = client.get("/users")

    assert response.status_code == 500


# ============================================================
# PATCH /users/{user_id}/activation
# ============================================================


def test_admin_can_deactivate_user(
    client_as,
    db_session,
    admin_user,
    test_user,
):
    test_user.is_active = True
    db_session.flush()

    client = client_as(admin_user)

    response = client.patch(
        f"/users/{test_user.id}/activation",
        json={"is_active": False},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == test_user.id
    assert data["is_active"] is False
    assert "password_hash" not in data

    db_session.refresh(test_user)
    assert test_user.is_active is False


def test_admin_can_reactivate_user(
    client_as,
    db_session,
    admin_user,
    test_user,
):
    test_user.is_active = False
    db_session.flush()

    client = client_as(admin_user)

    response = client.patch(
        f"/users/{test_user.id}/activation",
        json={"is_active": True},
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is True

    db_session.refresh(test_user)
    assert test_user.is_active is True


def test_non_admin_cannot_deactivate_user(
    client_as,
    test_user,
    technician_user,
):
    client = client_as(test_user)

    response = client.patch(
        f"/users/{technician_user.id}/activation",
        json={"is_active": False},
    )

    assert response.status_code == 403


def test_admin_cannot_deactivate_another_admin(
    client_as,
    admin_user,
):
    client = client_as(admin_user)

    response = client.patch(
        f"/users/{admin_user.id}/activation",
        json={"is_active": False},
    )

    assert response.status_code == 409


def test_admin_cannot_deactivate_missing_user(
    client_as,
    admin_user,
):
    client = client_as(admin_user)

    response = client.patch(
        "/users/999999999/activation",
        json={"is_active": False},
    )

    assert response.status_code == 404


def test_missing_actor_cannot_change_user_activation(
    client_as,
    test_user,
):
    missing_actor = SimpleNamespace(id=999999999)
    client = client_as(missing_actor)

    response = client.patch(
        f"/users/{test_user.id}/activation",
        json={"is_active": False},
    )

    assert response.status_code == 404


def test_deactivation_is_idempotent(
    client_as,
    db_session,
    admin_user,
    test_user,
    monkeypatch,
):
    test_user.is_active = False
    db_session.flush()

    def unexpected_update(self, **kwargs):
        pytest.fail(
            "update_is_active ne doit pas être appelé"
        )

    def unexpected_audit(self, **kwargs):
        pytest.fail(
            "Aucun audit ne doit être créé sans changement"
        )

    monkeypatch.setattr(
        UserRepository,
        "update_is_active",
        unexpected_update,
    )

    monkeypatch.setattr(
        AuditRepository,
        "create",
        unexpected_audit,
    )

    client = client_as(admin_user)

    response = client.patch(
        f"/users/{test_user.id}/activation",
        json={"is_active": False},
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_technician_with_active_incidents_cannot_be_deactivated(
    client_as,
    db_session,
    admin_user,
    technician_user,
    monkeypatch,
):
    technician_user.is_active = True
    db_session.flush()

    checked_ids = []

    def fake_count(self, *, assignee_id):
        checked_ids.append(assignee_id)
        return 3

    monkeypatch.setattr(
        IncidentRepository,
        "count_active_by_assignee",
        fake_count,
    )

    client = client_as(admin_user)

    response = client.patch(
        f"/users/{technician_user.id}/activation",
        json={"is_active": False},
    )

    assert response.status_code == 409
    assert checked_ids == [technician_user.id]

    db_session.refresh(technician_user)
    assert technician_user.is_active is True


def test_technician_without_active_incidents_can_be_deactivated(
    client_as,
    db_session,
    admin_user,
    technician_user,
    monkeypatch,
):
    technician_user.is_active = True
    db_session.flush()

    def fake_count(self, *, assignee_id):
        assert assignee_id == technician_user.id
        return 0

    monkeypatch.setattr(
        IncidentRepository,
        "count_active_by_assignee",
        fake_count,
    )

    client = client_as(admin_user)

    response = client.patch(
        f"/users/{technician_user.id}/activation",
        json={"is_active": False},
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_reactivating_technician_does_not_check_incidents(
    client_as,
    db_session,
    admin_user,
    technician_user,
    monkeypatch,
):
    technician_user.is_active = False
    db_session.flush()

    def unexpected_count(self, *, assignee_id):
        pytest.fail(
            "Les incidents ne doivent pas bloquer la réactivation"
        )

    monkeypatch.setattr(
        IncidentRepository,
        "count_active_by_assignee",
        unexpected_count,
    )

    client = client_as(admin_user)

    response = client.patch(
        f"/users/{technician_user.id}/activation",
        json={"is_active": True},
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is True


def test_deactivating_regular_user_does_not_check_incidents(
    client_as,
    db_session,
    admin_user,
    test_user,
    monkeypatch,
):
    test_user.is_active = True
    db_session.flush()

    def unexpected_count(self, *, assignee_id):
        pytest.fail(
            "Le comptage des incidents ne concerne que les techniciens"
        )

    monkeypatch.setattr(
        IncidentRepository,
        "count_active_by_assignee",
        unexpected_count,
    )

    client = client_as(admin_user)

    response = client.patch(
        f"/users/{test_user.id}/activation",
        json={"is_active": False},
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"is_active": "invalid"},
        {"is_active": None},
    ],
)
def test_activation_rejects_invalid_payload(
    client_as,
    admin_user,
    test_user,
    payload,
):
    client = client_as(admin_user)

    response = client.patch(
        f"/users/{test_user.id}/activation",
        json=payload,
    )

    assert response.status_code == 422


def test_activation_creates_one_correct_audit(
    client_as,
    db_session,
    admin_user,
    test_user,
    monkeypatch,
):
    test_user.is_active = True
    db_session.flush()

    recorded_events = []
    original_create = AuditRepository.create

    def recording_create(self, **kwargs):
        recorded_events.append(kwargs)
        return original_create(self, **kwargs)

    monkeypatch.setattr(
        AuditRepository,
        "create",
        recording_create,
    )

    client = client_as(admin_user)

    response = client.patch(
        f"/users/{test_user.id}/activation",
        json={"is_active": False},
    )

    assert response.status_code == 200
    assert len(recorded_events) == 1

    event = recorded_events[0]

    assert event["event_type"].name == "USER_DEACTIVATED"
    assert event["user_id"] == admin_user.id
    assert event["resource_type"] == "user"
    assert event["resource_id"] == test_user.id


def test_activation_audit_error_returns_500(
    client_as,
    db_session,
    admin_user,
    test_user,
    monkeypatch,
):
    test_user.is_active = True
    db_session.flush()

    def failing_audit(self, **kwargs):
        raise SQLAlchemyError("Audit database error")

    monkeypatch.setattr(
        AuditRepository,
        "create",
        failing_audit,
    )

    client = client_as(admin_user)

    response = client.patch(
        f"/users/{test_user.id}/activation",
        json={"is_active": False},
    )

    assert response.status_code == 500


def test_admin_can_list_all_users(
    client_as,
    admin_user,
    test_user,
    technician_user,
):
    client = client_as(admin_user)

    response = client.get("/users")

    print("ADMIN ID :", admin_user.id)
    print("STATUS :", response.status_code)
    print("RESPONSE :", response.json())
