from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

from app.core.config import settings


class InvalidAccessTokenError(Exception):
    """Jeton d'accès absent, invalide ou expiré."""


def create_access_token(user_id: int) -> str:
    """Crée un jeton d'accès JWT pour un utilisateur."""

    now = datetime.now(UTC)
    expires_at = now + timedelta(
        minutes=settings.access_token_expire_minutes
    )

    payload = {
        "sub": str(user_id),
        "type": "access",
        "iat": now,
        "exp": expires_at,
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> int:
    """Vérifie un jeton et retourne l'identifiant utilisateur."""

    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={
                "require": [
                    "sub",
                    "type",
                    "iat",
                    "exp",
                ]
            },
        )
    except (ExpiredSignatureError, InvalidTokenError) as error:
        raise InvalidAccessTokenError from error

    if payload.get("type") != "access":
        raise InvalidAccessTokenError

    subject = payload.get("sub")

    if not isinstance(subject, str) or not subject.isdigit():
        raise InvalidAccessTokenError

    user_id = int(subject)

    if user_id <= 0:
        raise InvalidAccessTokenError

    return user_id