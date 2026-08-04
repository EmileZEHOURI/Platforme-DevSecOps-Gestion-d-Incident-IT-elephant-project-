from unittest.mock import MagicMock

from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories import UserRepository


def create_user() -> User:
    return User(
        email="emile@example.com",
        password_hash="hashed-password",
        full_name="Emile Zehouri",
    )


def test_get_by_id_returns_user() -> None:
    db = MagicMock(spec=Session)
    expected_user = create_user()
    db.get.return_value = expected_user

    repository = UserRepository(db)

    result = repository.get_by_id(1)

    assert result is expected_user
    db.get.assert_called_once_with(User, 1)


def test_get_by_id_returns_none_when_user_does_not_exist() -> None:
    db = MagicMock(spec=Session)
    db.get.return_value = None

    repository = UserRepository(db)

    result = repository.get_by_id(999)

    assert result is None
    db.get.assert_called_once_with(User, 999)


def test_get_by_email_returns_user() -> None:
    db = MagicMock(spec=Session)
    expected_user = create_user()
    db.scalar.return_value = expected_user

    repository = UserRepository(db)

    result = repository.get_by_email("  Emile@Example.com  ")

    assert result is expected_user
    db.scalar.assert_called_once()


def test_get_by_email_returns_none_when_user_does_not_exist() -> None:
    db = MagicMock(spec=Session)
    db.scalar.return_value = None

    repository = UserRepository(db)

    result = repository.get_by_email("unknown@example.com")

    assert result is None
    db.scalar.assert_called_once()
