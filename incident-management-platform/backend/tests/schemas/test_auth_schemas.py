from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.models.enums import UserRole
from app.schemas import LoginRequest, UserResponse


def test_login_request_normalizes_email() -> None:
    login = LoginRequest(
        email="  Emile@Example.com  ",
        password="secret",
    )

    assert str(login.email) == "emile@example.com"
    assert login.password == "secret"


def test_login_request_rejects_invalid_email() -> None:
    with pytest.raises(ValidationError):
        LoginRequest(
            email="invalid-email",
            password="secret",
        )


def test_login_request_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        LoginRequest.model_validate(
            {
                "email": "emile@example.com",
                "password": "secret",
                "role": "ADMIN",
            }
        )


def test_user_response_does_not_expose_password_hash() -> None:
    response = UserResponse(
        id=1,
        email="emile@example.com",
        full_name="Emile Zehouri",
        role=UserRole.USER,
        is_active=True,
        created_at=datetime.now(UTC),
    )

    data = response.model_dump()

    assert data["role"] == UserRole.USER
    assert "password" not in data
    assert "password_hash" not in data
