import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.user import User

def test_authentication_lifecycle(test_user: User) -> None:

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

        # /me
        response = client.get("/auth/me")
        assert response.status_code == 200

        assert response.json()["email"] == "test@example.com"

        # logout
        response = client.post(
            "/auth/logout",
        )

        assert response.status_code == 200

        # /me une deuxième fois
        response = client.get("/auth/me")
        assert response.status_code == 401


def test_login_rejects_incorrect_password(test_user: User) -> None:

    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        # login
        response = client.post(
            "/auth/login",
            json={
                "email": "test@example.com",
                "password": "incorrect-password",
            },
        )
        assert response.status_code == 401
        assert (
            response.json()["detail"]
            == "Adresse électronique ou mot de passe incorrect."
        )


def test_get_me_without_authentication() -> None:

    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        response = client.get("/auth/me")
        assert response.status_code == 401
