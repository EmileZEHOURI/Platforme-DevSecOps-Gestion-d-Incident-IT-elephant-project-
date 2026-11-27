import hashlib
import hmac
import time
from datetime import UTC, datetime

from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.revoked_token import RevokedToken
from app.security.redis_client import get_redis_client


class RevocationUnavailableError(Exception):
    """Fail closed when a revocation store cannot be checked or written."""


def token_digest(jti: str) -> str:
    return hmac.new(
        settings.jwt_secret_key.encode(),
        f"jwt-revocation:{jti}".encode(),
        hashlib.sha256,
    ).hexdigest()


def redis_key(jti: str) -> str:
    return f"auth:revoked:{token_digest(jti)}"


def cache_revocation(jti: str, expires_at: int) -> None:
    if expires_at <= time.time():
        return
    try:
        # Absolute expiration avoids extending TTL on repeated revocations.
        if not get_redis_client().set(redis_key(jti), "1", exat=expires_at):
            raise RevocationUnavailableError
    except (RedisError, OSError, RuntimeError) as exc:
        raise RevocationUnavailableError from exc


def persist_revocation(db: Session, jti: str, expires_at: int) -> None:
    """Participates in the caller's transaction alongside the logout audit."""
    if expires_at <= time.time():
        return
    db.execute(
        insert(RevokedToken)
        .values(
            digest=token_digest(jti), expires_at=datetime.fromtimestamp(expires_at, UTC)
        )
        .on_conflict_do_nothing(index_elements=[RevokedToken.digest])
    )


def is_revoked(db: Session, jti: str) -> bool:
    try:
        if get_redis_client().exists(redis_key(jti)):
            return True
        # Never cache a negative result: SQL is the durable source of truth.
        expiry = db.scalar(
            select(RevokedToken.expires_at).where(
                RevokedToken.digest == token_digest(jti),
                RevokedToken.expires_at > datetime.now(UTC),
            )
        )
        if expiry is None:
            return False
        cache_revocation(jti, int(expiry.timestamp()))
        return True
    except (RedisError, OSError, RuntimeError, SQLAlchemyError) as exc:
        raise RevocationUnavailableError from exc
