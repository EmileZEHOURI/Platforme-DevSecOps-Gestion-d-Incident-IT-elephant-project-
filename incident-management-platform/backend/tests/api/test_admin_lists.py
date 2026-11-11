
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.user import User
from app.models.enums import UserRole


# ============================================
# HELPERS
# ============================================

def login(client: TestClient, user: User) -> None:
    response = client.post(
        "/auth/login",
        json={
            "email": user.email,
            "password": "password",
        },
    )

    assert response.status_code == 200, response.text


def create_incident(client: TestClient, title: str) -> int:
    response = client.post(
        "/incidents",
        json={
            "title": title,
            "description": "Incident créé pour tester la consultation globale.",
            "category": "ANOMALY",
            "priority": "MEDIUM",
        },
    )

    assert response.status_code == 201, response.text

    return response.json()["id"]


# ============================================
# GET /incidents/all
# ============================================

def test_admin_can_get_all_incidents(
    test_user: User,
    other_user: User,
    admin_user: User,
) -> None:

    with (
        TestClient(app, client=("127.0.0.1", 50000)) as client_1,
        TestClient(app, client=("127.0.0.1", 50000)) as client_2,
        TestClient(app, client=("127.0.0.1", 50000)) as admin,
    ):
        login(client_1, test_user)
        login(client_2, other_user)
        login(admin, admin_user)

        incident_id_1 = create_incident(
            client_1,
            "Incident créé par utilisateur A",
        )

        incident_id_2 = create_incident(
            client_2,
            "Incident créé par utilisateur B",
        )

        response = admin.get("/incidents/all")

        assert response.status_code == 200, response.text

        body = response.json()

        assert isinstance(body, list)
        assert len(body) == 2

        returned_ids = {incident["id"] for incident in body}

        assert incident_id_1 in returned_ids
        assert incident_id_2 in returned_ids

        incidents_by_id = {
            incident["id"]: incident
            for incident in body
        }

        assert (
            incidents_by_id[incident_id_1]["created_by_id"]
            == test_user.id
        )

        assert (
            incidents_by_id[incident_id_2]["created_by_id"]
            == other_user.id
        )


def test_admin_get_all_incidents_returns_empty_list(
    admin_user: User,
) -> None:

    with TestClient(
        app,
        client=("127.0.0.1", 50000),
    ) as admin:

        login(admin, admin_user)

        response = admin.get("/incidents/all")

        assert response.status_code == 200
        assert response.json() == []


# ============================================
# GET /users/technicians
# ============================================

def test_admin_can_get_active_technicians(
    db_session: Session,
    test_user: User,
    technician_user: User,
    other_technician_user: User,
    admin_user: User,
) -> None:

    # On désactive volontairement le deuxième technicien.
    other_technician_user.is_active = False
    db_session.commit()

    with TestClient(
        app,
        client=("127.0.0.1", 50000),
    ) as admin:

        login(admin, admin_user)

        response = admin.get("/users/technicians")

        assert response.status_code == 200, response.text

        body = response.json()

        assert isinstance(body, list)

        returned_ids = {user["id"] for user in body}

        # Technicien actif : visible
        assert technician_user.id in returned_ids

        # Technicien inactif : invisible
        assert other_technician_user.id not in returned_ids

        # Autres rôles : invisibles
        assert test_user.id not in returned_ids
        assert admin_user.id not in returned_ids

        assert len(body) == 1

        assert all(
            user["role"] == UserRole.TECHNICIAN.value
            for user in body
        )

        # Le schéma public ne doit jamais exposer le hash.
        assert all(
            "password_hash" not in user
            for user in body
        )


def test_admin_get_active_technicians_returns_empty_list(
    db_session: Session,
    technician_user: User,
    other_technician_user: User,
    admin_user: User,
) -> None:

    technician_user.is_active = False
    other_technician_user.is_active = False

    db_session.commit()

    with TestClient(
        app,
        client=("127.0.0.1", 50000),
    ) as admin:

        login(admin, admin_user)

        response = admin.get("/users/technicians")

        assert response.status_code == 200
        assert response.json() == []


# ============================================
# ACCÈS INTERDIT AUX NON-ADMIN
# ============================================

@pytest.mark.parametrize(
    "endpoint",
    [
        "/incidents/all",
        "/users/technicians",
    ],
)
@pytest.mark.parametrize(
    "actor_role",
    [
        UserRole.USER,
        UserRole.TECHNICIAN,
    ],
)
def test_non_admin_cannot_access_admin_lists(
    endpoint: str,
    actor_role: UserRole,
    test_user: User,
    technician_user: User,
) -> None:

    actor = (
        test_user
        if actor_role == UserRole.USER
        else technician_user
    )

    with TestClient(
        app,
        client=("127.0.0.1", 50000),
    ) as client:

        login(client, actor)

        response = client.get(endpoint)

        assert response.status_code == 403


# ============================================
# ACCÈS NON AUTHENTIFIÉ
# ============================================

@pytest.mark.parametrize(
    "endpoint",
    [
        "/incidents/all",
        "/users/technicians",
    ],
)
def test_unauthenticated_user_cannot_access_admin_lists(
    endpoint: str,
) -> None:

    with TestClient(
        app,
        client=("127.0.0.1", 50000),
    ) as client:

        response = client.get(endpoint)

        assert response.status_code == 401
