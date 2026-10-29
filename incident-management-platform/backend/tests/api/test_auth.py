import pytest
from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.main import app
from app.models.user import User
from app.repositories import UserRepository
from app.security import hash_password


@pytest.fixture
def test_user():
    with SessionLocal() as db:
        repository = UserRepository(db)

        # Préparation avant le test
        existing_user = repository.get_by_email("test@example.com")

        if existing_user is not None:
            db.delete(existing_user)
            db.commit()

        user = repository.create(
            email="test@example.com",
            password_hash=hash_password("password"),
            full_name="Test User",
        )

        db.commit()
        db.refresh(user)

        yield user

        # Nettoyage après le test
        user_to_delete = repository.get_by_email("test@example.com")

        if user_to_delete is not None:
            db.delete(user_to_delete)
            db.commit()


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
        assert response.json()["detail"] == "Adresse électronique ou mot de passe incorrect."


def test_get_me_without_authentication() -> None:

    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        response = client.get("/auth/me")
        assert response.status_code == 401
