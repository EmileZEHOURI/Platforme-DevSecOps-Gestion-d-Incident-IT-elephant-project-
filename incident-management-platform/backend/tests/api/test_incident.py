from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.main import app
from app.models.incident import Incident
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


def test_double_user(test_user: User, other_user: User) -> None:
    payload_1 = {
        "title": "Incident utilisateur A - 1",
        "description": "Le bouton envoyé ne mène à aucun chemin",
        "category": "ANOMALY",
        "priority": "MEDIUM",
    }

    payload_2 = {
        "title": "Incident utilisateur A - 2",
        "description": "Le bouton envoyé ne mène à aucun chemin",
        "category": "ANOMALY",
        "priority": "MEDIUM",
    }

    payload_3 = {
        "title": "Incident utilisateur B - 1",
        "description": "Le bouton envoyé ne mène à aucun chemin",
        "category": "ANOMALY",
        "priority": "MEDIUM",
    }

    with (
        TestClient(app, client=("127.0.0.1", 50000)) as client_1,
        TestClient(app, client=("127.0.0.1", 50000)) as client_2,
    ):
        # login
        login_response_client_1 = client_1.post(
            "/auth/login",
            json={
                "email": test_user.email,
                "password": "password",
            },
        )
        assert login_response_client_1.status_code == 200

        login_response_client_2 = client_2.post(
            "/auth/login",
            json={
                "email": other_user.email,
                "password": "password",
            },
        )
        assert login_response_client_2.status_code == 200

        # enregistrement

        incident_response_1 = client_1.post("/incidents", json=payload_1)
        assert incident_response_1.status_code == 201
        incident_id_1 = incident_response_1.json()["id"]

        incident_response_2 = client_1.post("/incidents", json=payload_2)

        assert incident_response_2.status_code == 201
        incident_id_2 = incident_response_2.json()["id"]

        incident_response_3 = client_2.post("/incidents", json=payload_3)

        assert incident_response_3.status_code == 201
        incident_id_3 = incident_response_3.json()["id"]

        incident_list_response = client_1.get("/incidents")
        assert incident_list_response.status_code == 200

        body = incident_list_response.json()
        assert len(body) == 2

        returned_ids = [incident["id"] for incident in body]

        assert incident_id_1 in returned_ids
        assert incident_id_2 in returned_ids
        assert incident_id_3 not in returned_ids

        assert all(incident["created_by_id"] == test_user.id for incident in body)


def test_get_incident_detail_and_prevent_access_to_other_user_incident(
    test_user: User, other_user: User
) -> None:
    payload_1 = {
        "title": "Incident utilisateur A - 1",
        "description": "Le bouton envoyé ne mène à aucun chemin",
        "category": "ANOMALY",
        "priority": "MEDIUM",
    }

    payload_2 = {
        "title": "Incident utilisateur B - 1",
        "description": "Le bouton envoyé ne mène à aucun chemin",
        "category": "ANOMALY",
        "priority": "MEDIUM",
    }

    with (
        TestClient(app, client=("127.0.0.1", 50000)) as client_1,
        TestClient(app, client=("127.0.0.1", 50000)) as client_2,
    ):
        # login
        login_response_client_1 = client_1.post(
            "/auth/login",
            json={
                "email": test_user.email,
                "password": "password",
            },
        )
        assert login_response_client_1.status_code == 200

        login_response_client_2 = client_2.post(
            "/auth/login",
            json={
                "email": other_user.email,
                "password": "password",
            },
        )
        assert login_response_client_2.status_code == 200

        incident_response_1 = client_1.post("/incidents", json=payload_1)
        assert incident_response_1.status_code == 201
        incident_id_1 = incident_response_1.json()["id"]

        incident_response_2 = client_2.post("/incidents", json=payload_2)
        assert incident_response_2.status_code == 201
        incident_id_2 = incident_response_2.json()["id"]

        # 1. User A demande son propre incident → 200

        incident_details_1 = client_1.get(f"/incidents/{incident_id_1}")
        assert incident_details_1.status_code == 200
        body = incident_details_1.json()
        assert body["id"] == incident_id_1
        assert body["title"] == payload_1["title"]
        assert body["description"] == payload_1["description"]
        assert body["created_by_id"] == test_user.id

        # 2. User A demande un incident inexistant → 404

        incident_details_2 = client_1.get("/incidents/99999999")
        assert incident_details_2.status_code == 404

        # 3. User A demande l’incident de User B → 404

        incident_details_3 = client_2.get(f"/incidents/{incident_id_2}")
        assert incident_details_3.status_code == 200

        incident_details_4 = client_1.get(f"/incidents/{incident_id_2}")
        assert incident_details_4.status_code == 404


def test_get_assigned_incident_lifecyle(
    test_user: User, technician_user: User, other_technician_user: User
) -> None:
    incident_payload_1 = {
        "title": "Incident utilisateur A - 1, Assignée à Tehcnician A ",
        "description": "Le bouton envoyé ne mène à aucun chemin",
        "category": "ANOMALY",
        "priority": "MEDIUM",
    }

    incident_payload_2 = {
        "title": "Incident utilisateur A - 2 , Assignée à Tehcnician A",
        "description": "Le bouton envoyé ne mène à aucun chemin",
        "category": "ANOMALY",
        "priority": "MEDIUM",
    }

    incident_payload_3 = {
        "title": "Incident utilisateur A - 1, , Assignée à Tehcnician B",
        "description": "Le bouton envoyé ne mène à aucun chemin",
        "category": "ANOMALY",
        "priority": "MEDIUM",
    }

    with (
        TestClient(app, client=("127.0.0.1", 50000)) as client,
        TestClient(app, client=("127.0.0.1", 50000)) as technician_1,
        TestClient(app, client=("127.0.0.1", 50000)) as technician_2,
    ):
        # Connexion utilisateur A
        login_response_1 = client.post(
            "/auth/login",
            json={
                "email": test_user.email,
                "password": "password",
            },
        )
        assert login_response_1.status_code == 200

        # Connexion technicien A

        login_response_2 = technician_1.post(
            "/auth/login",
            json={
                "email": technician_user.email,
                "password": "password",
            },
        )
        assert login_response_2.status_code == 200

        # Connexion technicien B

        login_response_3 = technician_2.post(
            "/auth/login",
            json={
                "email": other_technician_user.email,
                "password": "password",
            },
        )
        assert login_response_3.status_code == 200

        # client crée ses incident
        incident_response_1 = client.post(
            "/incidents",
            json=incident_payload_1,
        )
        assert incident_response_1.status_code == 201
        incident_id_1 = incident_response_1.json()["id"]

        incident_response_2 = client.post(
            "/incidents",
            json=incident_payload_2,
        )
        assert incident_response_2.status_code == 201
        incident_id_2 = incident_response_2.json()["id"]

        incident_response_3 = client.post(
            "/incidents",
            json=incident_payload_3,
        )
        assert incident_response_3.status_code == 201
        incident_id_3 = incident_response_3.json()["id"]

        incident_technician_1_list = technician_1.get(
            "/incidents/assigned",
        )

        with SessionLocal() as db:
            incident_1 = db.get(Incident, incident_id_1)
            incident_2 = db.get(Incident, incident_id_2)
            incident_3 = db.get(Incident, incident_id_3)

            assert incident_1 is not None
            assert incident_2 is not None
            assert incident_3 is not None

            incident_1.assigned_to_id = technician_user.id
            incident_2.assigned_to_id = technician_user.id
            incident_3.assigned_to_id = other_technician_user.id

            db.commit()

        assert incident_technician_1_list.status_code == 200

        body_list = incident_technician_1_list.json()

        returned_ids = [incident["id"] for incident in body_list]

        assert incident_id_1 in returned_ids
        assert incident_id_2 in returned_ids
        assert incident_id_3 not in returned_ids

        assert all(
            incident["assigned_to_id"] == technician_user.id for incident in body_list
        )
        assert len(body_list) == 2


def test_user_get_incident_assigned_forbidden(
    test_user: User, technician_user: User
) -> None:
    incident_payload_1 = {
        "title": "Incident utilisateur A - 1, Assignée à Tehcnician A ",
        "description": "Le bouton envoyé ne mène à aucun chemin",
        "category": "ANOMALY",
        "priority": "MEDIUM",
    }

    with (
        TestClient(app, client=("127.0.0.1", 50000)) as client,
    ):
        # Connexion utilisateur A
        login_response_1 = client.post(
            "/auth/login",
            json={
                "email": test_user.email,
                "password": "password",
            },
        )
        assert login_response_1.status_code == 200

        # client crée ses incident
        incident_response_1 = client.post(
            "/incidents",
            json=incident_payload_1,
        )
        assert incident_response_1.status_code == 201

        response = client.get(
            "/incidents/assigned",
        )

        assert response.status_code == 403


def test_technician_without_assigned_incident(technician_user: User) -> None:

    with (
        TestClient(app, client=("127.0.0.1", 50000)) as technician_1,
    ):
        # Connexion technicien A

        login_response_2 = technician_1.post(
            "/auth/login",
            json={
                "email": technician_user.email,
                "password": "password",
            },
        )
        assert login_response_2.status_code == 200

        incident_technician_1_list = technician_1.get(
            "/incidents/assigned",
        )
        assert incident_technician_1_list.status_code == 200

        body_list = incident_technician_1_list.json()

        assert len(body_list) == 0


