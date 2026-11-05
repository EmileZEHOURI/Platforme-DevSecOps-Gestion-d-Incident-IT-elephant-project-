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


def test_get_incident_detail_and_prevent_access_to_other_user_incident(test_user: User, other_user: User) -> None:
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

        #1. User A demande son propre incident → 200

        incident_details_1 = client_1.get(f"/incidents/{incident_id_1}")
        assert incident_details_1.status_code == 200
        body = incident_details_1.json()
        assert body["id"] == incident_id_1
        assert body["title"] == payload_1["title"]
        assert body["description"] == payload_1["description"]
        assert body["created_by_id"] == test_user.id

        #2. User A demande un incident inexistant → 404

        incident_details_2 = client_1.get("/incidents/99999999")
        assert incident_details_2.status_code == 404

        #3. User A demande l’incident de User B → 404

        incident_details_3 = client_2.get(f"/incidents/{incident_id_2}")
        assert incident_details_3.status_code == 200

        incident_details_4 = client_1.get(f"/incidents/{incident_id_2}")
        assert incident_details_4.status_code == 404

        


