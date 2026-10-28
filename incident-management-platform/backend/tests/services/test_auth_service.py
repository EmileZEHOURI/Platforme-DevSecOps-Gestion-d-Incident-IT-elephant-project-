from unittest.mock import MagicMock, patch

import pytest

from app.models.enums import UserRole
from app.models.user import User
from app.repositories import UserRepository
from app.services import (
    AuthenticationError,
    AuthService,
)


def create_user(
    *,
    is_active: bool = True,
) -> User:
    """Crée un utilisateur utilisable dans les tests."""

    return User(
        id=1,
        email="emile@example.com",
        password_hash="stored-password-hash",
        full_name="Emile Zehouri",
        role=UserRole.USER,
        is_active=is_active,
    )


def test_authenticate_returns_user_and_token() -> None:
    repository = MagicMock(spec=UserRepository)
    user = create_user()

    repository.get_by_email.return_value = user

    service = AuthService(repository)

    with (
        patch(
            "app.services.auth_service.verify_password",
            return_value=True,
        ) as verify_password_mock,
        patch(
            "app.services.auth_service.create_access_token",
            return_value="generated-access-token",
        ) as create_token_mock,
    ):
        result = service.authenticate(
            email="emile@example.com",
            password="correct-password",
        )

    assert result.user is user
    assert result.access_token == "generated-access-token"

    repository.get_by_email.assert_called_once_with(
        "emile@example.com"
    )

    verify_password_mock.assert_called_once_with(
        "correct-password",
        "stored-password-hash",
    )

    create_token_mock.assert_called_once_with(1)


def test_authenticate_rejects_unknown_user() -> None:
    repository = MagicMock(spec=UserRepository)
    repository.get_by_email.return_value = None

    service = AuthService(repository)

    with pytest.raises(AuthenticationError):
        service.authenticate(
            email="unknown@example.com",
            password="password",
        )


def test_authenticate_rejects_incorrect_password() -> None:
    repository = MagicMock(spec=UserRepository)
    repository.get_by_email.return_value = create_user()

    service = AuthService(repository)

    with (
        patch(
            "app.services.auth_service.verify_password",
            return_value=False,
        ),
        patch(
            "app.services.auth_service.create_access_token",
        ) as create_token_mock,
        pytest.raises(AuthenticationError),
    ):
        service.authenticate(
            email="emile@example.com",
            password="wrong-password",
        )

    create_token_mock.assert_not_called()


def test_authenticate_rejects_inactive_user() -> None:
    repository = MagicMock(spec=UserRepository)
    repository.get_by_email.return_value = create_user(
        is_active=False
    )

    service = AuthService(repository)

    with (
        patch(
            "app.services.auth_service.verify_password",
            return_value=True,
        ),
        patch(
            "app.services.auth_service.create_access_token",
        ) as create_token_mock,
        pytest.raises(AuthenticationError),
    ):
        service.authenticate(
            email="emile@example.com",
            password="correct-password",
        )

    create_token_mock.assert_not_called()