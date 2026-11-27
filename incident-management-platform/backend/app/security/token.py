import re
import secrets
from dataclasses import dataclass
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
    expires_at = now + timedelta(minutes=settings.access_token_expire_minutes)

    payload = {
        "sub": str(user_id),
        "jti": secrets.token_hex(16),
        "type": "access",
        "iat": now,
        "exp": expires_at,
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


@dataclass(frozen=True, slots=True)
class AccessTokenClaims:
    user_id: int
    jti: str | None
    expires_at: int


def decode_access_token_claims(token: str) -> AccessTokenClaims:
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

    jti = payload.get("jti")
    if jti is not None and (
        not isinstance(jti, str) or not re.fullmatch(r"[0-9a-f]{32}", jti)
    ):
        raise InvalidAccessTokenError
    if settings.jwt_revocation_required and jti is None:
        raise InvalidAccessTokenError
    if type(payload.get("exp")) is not int or type(payload.get("iat")) is not int:
        raise InvalidAccessTokenError
    return AccessTokenClaims(user_id=user_id, jti=jti, expires_at=payload["exp"])


def decode_access_token(token: str) -> int:
    """Compatibility helper; revocation is enforced by the API dependency."""
    return decode_access_token_claims(token).user_id
