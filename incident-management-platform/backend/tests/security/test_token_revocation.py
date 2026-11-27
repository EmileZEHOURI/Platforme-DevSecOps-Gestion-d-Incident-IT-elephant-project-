import os
import time
from secrets import token_hex
from unittest.mock import Mock

import fakeredis
import jwt
import pytest
from pydantic import ValidationError
from redis import Redis
from redis.exceptions import ConnectionError

from app.core.config import Settings, settings
from app.security import (
    InvalidAccessTokenError,
    create_access_token,
    decode_access_token,
)
from app.security import token_revocation as rev
from app.security.token import decode_access_token_claims


@pytest.fixture
def fake(monkeypatch):
    client = fakeredis.FakeRedis()
    monkeypatch.setattr(rev, "get_redis_client", lambda: client)
    return client


def signed(**overrides):
    payload = {
        "sub": "42",
        "type": "access",
        "iat": int(time.time()),
        "exp": int(time.time()) + 60,
        "jti": token_hex(16),
    }
    payload.update(overrides)
    return jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")


def test_jti_unique_and_independent():
    claims = [decode_access_token_claims(create_access_token(42)) for _ in range(20)]
    assert len({c.jti for c in claims}) == 20
    assert all(c.user_id == 42 and len(c.jti) == 32 for c in claims)


@pytest.mark.parametrize("jti", ["", "42", "x" * 32, 1, [], {}, False])
def test_invalid_jti_rejected(jti):
    with pytest.raises(InvalidAccessTokenError):
        decode_access_token(signed(jti=jti))


def test_legacy_rejected_when_required(monkeypatch):
    monkeypatch.setattr(settings, "jwt_revocation_enabled", True)
    with pytest.raises(InvalidAccessTokenError):
        decode_access_token(signed(jti=None))


def test_production_cannot_disable_revocation():
    config = Settings(
        _env_file=None,
        database_url="postgresql://localhost/test",
        jwt_secret_key=token_hex(32),
        environment="production",
        frontend_origin="https://example.com",
        redis_url="redis://localhost:6380",
        jwt_revocation_enabled=False,
    )
    assert config.jwt_revocation_required


def test_enabled_requires_redis():
    with pytest.raises(ValidationError, match="REDIS_URL"):
        Settings(
            _env_file=None,
            database_url="postgresql://localhost/test",
            jwt_secret_key=token_hex(32),
            environment="test",
            redis_url=None,
            jwt_revocation_enabled=True,
        )


def test_cache_ttl_idempotence_and_independence(fake):
    first, second = token_hex(16), token_hex(16)
    exp = int(time.time()) + 60
    rev.cache_revocation(first, exp)
    assert rev.is_revoked(Mock(), first)
    assert 58 <= fake.ttl(rev.redis_key(first)) <= 60
    rev.cache_revocation(first, exp)
    assert fake.ttl(rev.redis_key(first)) <= 60
    assert not fake.exists(rev.redis_key(second))
    assert fake.get(rev.redis_key(first)) == b"1"
    assert first not in rev.redis_key(first)


def test_expired_not_written(fake):
    rev.cache_revocation(token_hex(16), int(time.time()) - 1)
    assert fake.dbsize() == 0


@pytest.mark.parametrize("operation", ["read", "write"])
def test_redis_failure_closed(monkeypatch, operation):
    client = Mock()
    client.exists.side_effect = ConnectionError()
    client.set.side_effect = ConnectionError()
    monkeypatch.setattr(rev, "get_redis_client", lambda: client)
    with pytest.raises(rev.RevocationUnavailableError):
        if operation == "read":
            rev.is_revoked(Mock(), token_hex(16))
        else:
            rev.cache_revocation(token_hex(16), int(time.time()) + 60)


def test_real_redis_ttl_opt_in(monkeypatch):
    url = os.environ.get("TEST_REVOCATION_REDIS_URL")
    if not url:
        pytest.skip("TEST_REVOCATION_REDIS_URL required for opt-in real Redis test")
    client = Redis.from_url(url, socket_timeout=1, socket_connect_timeout=1)
    client.ping()
    monkeypatch.setattr(rev, "get_redis_client", lambda: client)
    jti = token_hex(16)
    key = rev.redis_key(jti)
    try:
        rev.cache_revocation(jti, int(time.time()) + 2)
        assert rev.is_revoked(Mock(), jti)
        assert 0 < client.ttl(key) <= 2
        time.sleep(2.1)
        assert not client.exists(key)
    finally:
        client.delete(key)
        client.close()


def test_redis_refused_write_is_failure(monkeypatch):
    client = Mock()
    client.set.return_value = False
    monkeypatch.setattr(rev, "get_redis_client", lambda: client)
    with pytest.raises(rev.RevocationUnavailableError):
        rev.cache_revocation(token_hex(16), int(time.time()) + 60)


@pytest.mark.parametrize("claim", ["exp", "iat"])
def test_non_integer_dates_rejected(claim):
    with pytest.raises(InvalidAccessTokenError):
        decode_access_token(signed(**{claim: str(int(time.time()) + 30)}))
