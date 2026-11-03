import pytest
from sqlalchemy import select

from app.models.incident import Incident
from app.models.history import IncidentHistory

from app.core.database import SessionLocal
from app.repositories import UserRepository
from app.security import hash_password


@pytest.fixture
def test_user():
    with SessionLocal() as db:
        repository = UserRepository(db)

        # Préparation avant le test
        existing_user = repository.get_by_email("test@example.com")

        if existing_user is not None:
            statement = select(Incident).where(
                Incident.created_by_id == existing_user.id
            )
            incidents = db.scalars(statement).all()

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
