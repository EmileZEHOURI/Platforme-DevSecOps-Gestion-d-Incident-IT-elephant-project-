from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.main import app
from app.models.enums import (
    IncidentCategory,
    IncidentPriority,
    IncidentStatus,
)
from app.models.incident import Incident
from app.models.user import User


def test_incident_comment_creation_lifecycle(test_user: User) -> None:
    incident_payload = {
        "title": "Incident utilisateur A - 1",
        "description": "Le bouton envoyé ne mène à aucun chemin",
        "category": "ANOMALY",
        "priority": "MEDIUM",
    }

    comment_payload = {
        "content": "Le problème est toujours présent.",
    }

    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        login_response = client.post(
            "/auth/login",
            json={
                "email": test_user.email,
                "password": "password",
            },
        )

        assert login_response.status_code == 200

        incident_response = client.post(
            "/incidents",
            json=incident_payload,
        )

        assert incident_response.status_code == 201

        incident_id = incident_response.json()["id"]

        comment_response = client.post(
            f"/incidents/{incident_id}/comments",
            json=comment_payload,
        )

        assert comment_response.status_code == 201

        body = comment_response.json()

        assert body["id"] is not None
        assert body["incident_id"] == incident_id
        assert body["author_id"] == test_user.id
        assert body["content"] == comment_payload["content"]
        assert body["created_at"] is not None


def test_comment_other_user_incident_returns_404(
    test_user: User,
    other_user: User,
) -> None:
    incident_payload = {
        "title": "Incident utilisateur B",
        "description": "Incident appartenant à l'utilisateur B",
        "category": "ANOMALY",
        "priority": "MEDIUM",
    }

    comment_payload = {
        "content": "Je tente de commenter cet incident.",
    }

    with (
        TestClient(app, client=("127.0.0.1", 50000)) as client_1,
        TestClient(app, client=("127.0.0.1", 50000)) as client_2,
    ):
        # Connexion utilisateur A
        login_response_1 = client_1.post(
            "/auth/login",
            json={
                "email": test_user.email,
                "password": "password",
            },
        )
        assert login_response_1.status_code == 200

        # Connexion utilisateur B
        login_response_2 = client_2.post(
            "/auth/login",
            json={
                "email": other_user.email,
                "password": "password",
            },
        )
        assert login_response_2.status_code == 200

        # B crée son incident
        incident_response = client_2.post(
            "/incidents",
            json=incident_payload,
        )
        assert incident_response.status_code == 201

        incident_id = incident_response.json()["id"]

        # A tente de commenter l'incident de B
        comment_response = client_1.post(
            f"/incidents/{incident_id}/comments",
            json=comment_payload,
        )

        assert comment_response.status_code == 404
        assert (
            comment_response.json()["detail"] == "incident inexistant ou inaccessible"
        )


def test_comment_closed_incident_returns_409(
    test_user: User,
    db_session: Session,
) -> None:

    closed_incident = Incident(
        title="Incident fermé",
        description="Cet incident est déjà résolu et fermé.",
        category=IncidentCategory.ANOMALY,
        priority=IncidentPriority.MEDIUM,
        status=IncidentStatus.OPEN,
        created_by_id=test_user.id,
        assigned_to_id=test_user.id,
        resolution=None,
        resolved_at=None,
        closed_at=None,
    )

    db_session.add(closed_incident)
    db_session.flush()

    closed_incident.status = IncidentStatus.CLOSED
    closed_incident.resolution = "Le problème a été résolu."
    closed_incident.resolved_at = (
        closed_incident.created_at + timedelta(seconds=1)
    )
    closed_incident.closed_at = (
        closed_incident.created_at + timedelta(seconds=2)
    )

    db_session.flush()

    incident_id = closed_incident.id

    comment_payload = {
        "content": "Je tente de commenter un incident fermé.",
    }

    with TestClient(
        app,
        client=("127.0.0.1", 50000),
    ) as client:

        login_response = client.post(
            "/auth/login",
            json={
                "email": test_user.email,
                "password": "password",
            },
        )

        assert login_response.status_code == 200

        comment_response = client.post(
            f"/incidents/{incident_id}/comments",
            json=comment_payload,
        )

        assert comment_response.status_code == 409, comment_response.text
        assert (
            comment_response.json()["detail"]
            == "Impossible d’ajouter un commentaire à un incident fermé"
        )