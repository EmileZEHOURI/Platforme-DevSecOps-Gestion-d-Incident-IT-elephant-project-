from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.config import settings
from app.security import (
    InvalidAccessTokenError,
    create_access_token,
    decode_access_token,
)


def test_create_and_decode_access_token() -> None:
    token = create_access_token(user_id=42)

    user_id = decode_access_token(token)

    assert user_id == 42


def test_decode_rejects_invalid_signature() -> None:
    token = jwt.encode(
        {
            "sub": "42",
            "type": "access",
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        "another-secret-key",
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(InvalidAccessTokenError):
        decode_access_token(token)


def test_decode_rejects_expired_token() -> None:
    token = jwt.encode(
        {
            "sub": "42",
            "type": "access",
            "iat": datetime.now(UTC) - timedelta(minutes=10),
            "exp": datetime.now(UTC) - timedelta(minutes=5),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(InvalidAccessTokenError):
        decode_access_token(token)


def test_decode_rejects_wrong_token_type() -> None:
    token = jwt.encode(
        {
            "sub": "42",
            "type": "refresh",
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(InvalidAccessTokenError):
        decode_access_token(token)


def test_decode_rejects_invalid_subject() -> None:
    token = jwt.encode(
        {
            "sub": "not-an-id",
            "type": "access",
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(InvalidAccessTokenError):
        decode_access_token(token)


def test_decode_rejects_missing_claim() -> None:
    token = jwt.encode(
        {
            "sub": "42",
            "type": "access",
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(InvalidAccessTokenError):
        decode_access_token(token)