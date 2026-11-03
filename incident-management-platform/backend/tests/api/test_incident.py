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

    body = response.json()

    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        # login
        response = client.post(
            "/auth/login",
            json={
                "email": "test@example.com",
                "password": "password",
            },
        )

        assert response.status_code == 200
        # enregistrement

        response = client.post(
            "/incidents",
            json=payload,
        )
        assert response.status_code == 201

        assert (
            body["title"] == payload["title"],
            body["description"] == payload["description"],
            body["category"] == "ANOMALY",
            body["priority"] == "MEDIUM",
            body["status"] == "OPEN",
            body["id"] is not None,
            body["reference"].startswith("INC-"),
            body["created_by_id"] == test_user.id,
            body["assigned_to_id"] is None,
            body["resolution"] is None,
        )
