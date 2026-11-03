from fastapi.testclient import TestClient

from app.main import app
from app.models.user import User


def test_incident_creation_lifecycle(test_user: User) -> None:

    payload = {
        "title": "Erreur concernant bouton ENVOYE",
        "description": "Le bouton envoyé ne mène à aucun chemin",
        "category": "ANOMALY",
        "priority": "MEDIUM",
    }

    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        # login
        login_response = client.post(
            "/auth/login",
            json={
                "email": "test@example.com",
                "password": "password",
            },
        )

        assert login_response.status_code == 200
        # enregistrement

        incident_response = client.post(
            "/incidents",
            json=payload,
        )
        assert incident_response.status_code == 201

        body = incident_response.json()

        assert body["title"] == payload["title"]
        assert body["description"] == payload["description"]
        assert body["category"] == "ANOMALY"
        assert body["priority"] == "MEDIUM"
        assert body["status"] == "OPEN"
        assert body["id"] is not None
        assert body["reference"].startswith("INC-")
        assert body["created_by_id"] == test_user.id
        assert body["assigned_to_id"] is None
        assert body["resolution"] is None


def test_incident_creation_user_authentification_error() -> None:

    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        payload = {
            "title": "Erreur concernant bouton ENVOYE",
            "description": "Le bouton envoyé ne mène à aucun chemin",
            "category": "ANOMALY",
            "priority": "MEDIUM",
        }

        incident_response = client.post(
            "/incidents",
            json=payload,
        )

        assert incident_response.status_code == 401


def test_incident_creation_invalid_payload(test_user: User) -> None:
    payload = {
        "title": "E",
        "description": "Le bouton envoyé ne mène à aucun chemin",
        "category": "ANOMALY",
        "priority": "MEDIUM",
    }

    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        # login
        login_response = client.post(
            "/auth/login",
            json={
                "email": "test@example.com",
                "password": "password",
            },
        )

        assert login_response.status_code == 200
        # enregistrement

        incident_response = client.post(
            "/incidents",
            json=payload,
        )
        assert incident_response.status_code == 422
