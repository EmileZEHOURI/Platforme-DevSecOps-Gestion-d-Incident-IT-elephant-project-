from unittest.mock import MagicMock, patch

import pytest

from app.models.enums import AuditEventType, AuditResult, UserRole
from app.models.user import User
from app.repositories.audit_repository import AuditRepository
from app.repositories.user_repository import UserRepository
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


# connexion réussie → LOGIN_SUCCESS


def test_success_authenticate_returns_user_and_token() -> None:
    user_repository = MagicMock(spec=UserRepository)
    audit_repository = MagicMock(spec=AuditRepository)

    user = create_user()
    ip_address = "192.0.2.1"
    user_agent = "pytest-client"

    service = AuthService(
        user_repository,
        audit_repository,
    )

    user_repository.get_by_email.return_value = user

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
            ip_address=ip_address,
            user_agent=user_agent,
        )

    assert result.user is user

    assert result.access_token == "generated-access-token"

    user_repository.get_by_email.assert_called_once_with("emile@example.com")

    verify_password_mock.assert_called_once_with(
        "correct-password",
        "stored-password-hash",
    )

    audit_repository.create.assert_called_once_with(
        user_id=user.id,
        event_type=AuditEventType.LOGIN_SUCCESS,
        result=AuditResult.SUCCESS,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    create_token_mock.assert_called_once_with(1)


# utilisateur inexistant → LOGIN_FAILURE


def test_authenticate_rejects_unknown_user() -> None:
    user_repository = MagicMock(spec=UserRepository)
    audit_repository = MagicMock(spec=AuditRepository)

    ip_address = None
    user_agent = None

    service = AuthService(
        user_repository,
        audit_repository,
    )

    user_repository.get_by_email.return_value = None

    with pytest.raises(AuthenticationError):
        service.authenticate(
            email="unknown@example.com",
            password="password",
        )

    user_repository.get_by_email.assert_called_once_with("unknown@example.com")

    audit_repository.create.assert_called_once_with(
        event_type=AuditEventType.LOGIN_FAILURE,
        result=AuditResult.FAILURE,
        ip_address=ip_address,
        user_agent=user_agent,
        details={
            "reason": "invalid_credentials",
        },
    )


# mauvais mot de passe → LOGIN_FAILURE


def test_authenticate_rejects_incorrect_password() -> None:
    user_repository = MagicMock(spec=UserRepository)
    audit_repository = MagicMock(spec=AuditRepository)

    user = create_user()
    ip_address = "192.0.2.1"
    user_agent = "pytest-client"

    user_repository.get_by_email.return_value = user

    service = AuthService(
        user_repository,
        audit_repository,
    )

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
            ip_address=ip_address,
            user_agent=user_agent,
        )

    create_token_mock.assert_not_called()

    audit_repository.create.assert_called_once_with(
        user_id=user.id,
        event_type=AuditEventType.LOGIN_FAILURE,
        result=AuditResult.FAILURE,
        ip_address=ip_address,
        user_agent=user_agent,
        details={
            "reason": "invalid_credentials",
        },
    )


# compte inactif → LOGIN_FAILURE


def test_authenticate_rejects_inactive_user() -> None:
    user_repository = MagicMock(spec=UserRepository)
    audit_repository = MagicMock(spec=AuditRepository)

    user = create_user(is_active=False)
    ip_address = None
    user_agent = None

    user_repository.get_by_email.return_value = user

    service = AuthService(
        user_repository,
        audit_repository,
    )

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

    audit_repository.create.assert_called_once_with(
        user_id=user.id,
        event_type=AuditEventType.LOGIN_FAILURE,
        result=AuditResult.FAILURE,
        ip_address=ip_address,
        user_agent=user_agent,
        details={
            "reason": "inactive_account",
        },
    )
