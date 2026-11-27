import time
from unittest.mock import Mock

import fakeredis
import jwt
import pytest
from fastapi.testclient import TestClient
from redis.exceptions import ConnectionError
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.main import app
from app.models import AuditLog, RevokedToken
from app.models.enums import AuditEventType, UserRole
from app.security import create_access_token
from app.security import token_revocation as rev
from app.security.token import decode_access_token_claims


@pytest.fixture(autouse=True)
def revocation_enabled(monkeypatch):
    client = fakeredis.FakeRedis()
    monkeypatch.setattr(settings, "jwt_revocation_enabled", True)
    monkeypatch.setattr(settings, "csrf_protection_enabled", True)
    monkeypatch.setattr(settings, "frontend_origin", "http://testserver")
    monkeypatch.setattr(rev, "get_redis_client", lambda: client)
    return client


@pytest.fixture
def client(test_user):
    with TestClient(
        app, client=("127.0.0.1", 50000), headers={"Origin": "http://testserver"}
    ) as client:
        yield client


def login(client):
    response = client.post(
        "/auth/login", json={"email": "test@example.com", "password": "password"}
    )
    assert response.status_code == 200
    return client.cookies.get("access_token")


def replay(client, token):
    client.cookies.clear()
    return client.get("/auth/me", headers={"Cookie": f"access_token={token}"})


def test_logout_replay_two_sessions_and_redis_loss(
    client, db_session, revocation_enabled
):
    first = login(client)
    second = login(client)
    assert first != second
    client.cookies.clear()
    client.cookies.set("access_token", first, domain="testserver.local", path="/")
    assert client.get("/auth/me").status_code == 200
    result = client.post("/auth/logout")
    assert result.status_code == 200
    assert "Max-Age=0" in result.headers["set-cookie"]
    assert client.cookies.get("access_token") is None
    for _ in range(3):
        assert replay(client, first).status_code == 401
    assert replay(client, second).status_code == 200
    # Simulate loss of exactly this cache entry, not unrelated Redis keys.
    claims = decode_access_token_claims(first)
    revocation_enabled.delete(rev.redis_key(claims.jti))
    assert replay(client, first).status_code == 401
    assert revocation_enabled.exists(rev.redis_key(claims.jti))
    assert db_session.scalar(select(func.count()).select_from(RevokedToken)) == 1
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(AuditLog)
            .where(AuditLog.event_type == AuditEventType.LOGOUT)
        )
        == 1
    )


@pytest.mark.parametrize("kind", ["invalid", "expired", "missing", "bad_signature"])
def test_invalid_tokens(client, kind):
    now = int(time.time())
    body = {
        "sub": "1",
        "type": "access",
        "iat": now - 60,
        "exp": now + 60,
        "jti": "a" * 32,
    }
    if kind == "expired":
        body["exp"] = now - 1
    if kind == "missing":
        body.pop("jti")
    token = (
        "invalid"
        if kind == "invalid"
        else jwt.encode(
            body,
            "z" * 40 if kind == "bad_signature" else settings.jwt_secret_key,
            algorithm="HS256",
        )
    )
    assert replay(client, token).status_code == 401


@pytest.mark.parametrize("path,method", [("/auth/me", "get"), ("/auth/logout", "post")])
def test_redis_read_failure_returns_503(client, monkeypatch, path, method):
    login(client)
    failed = Mock()
    failed.exists.side_effect = ConnectionError()
    monkeypatch.setattr(rev, "get_redis_client", lambda: failed)
    assert getattr(client, method)(path).status_code == 503


def test_failed_redis_write_is_not_success_but_sql_stays_revoked(
    client, monkeypatch, revocation_enabled, db_session
):
    token = login(client)
    monkeypatch.setattr(revocation_enabled, "set", Mock(side_effect=ConnectionError()))
    response = client.post("/auth/logout")
    assert response.status_code == 503
    assert "set-cookie" not in response.headers
    assert db_session.scalar(select(func.count()).select_from(RevokedToken)) == 1
    monkeypatch.undo()
    # Restore enabled configuration and a healthy empty cache after failure.
    monkeypatch.setattr(settings, "jwt_revocation_enabled", True)
    healthy = fakeredis.FakeRedis()
    monkeypatch.setattr(rev, "get_redis_client", lambda: healthy)
    assert replay(client, token).status_code == 401


def test_sql_commit_failure_rolls_back_audit_and_revocation(
    client, monkeypatch, db_session, revocation_enabled
):
    token = login(client)
    with monkeypatch.context() as scoped:
        scoped.setattr(db_session, "commit", Mock(side_effect=SQLAlchemyError()))
        assert client.post("/auth/logout").status_code == 503
    assert revocation_enabled.dbsize() == 0
    assert db_session.scalar(select(func.count()).select_from(RevokedToken)) == 0
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(AuditLog)
            .where(AuditLog.event_type == AuditEventType.LOGOUT)
        )
        == 0
    )
    assert replay(client, token).status_code == 200


@pytest.mark.parametrize("role", list(UserRole))
def test_roles_and_disabled_accounts(client, test_user, db_session, role):
    test_user.role = role
    db_session.commit()
    token = login(client)
    assert client.get("/auth/me").json()["role"] == role.value
    assert client.get("/users").status_code == (200 if role == UserRole.ADMIN else 403)
    test_user.is_active = False
    db_session.commit()
    assert replay(client, token).status_code == 401


def test_csrf_rejection_does_not_revoke(client, db_session):
    token = login(client)
    assert (
        client.post("/auth/logout", headers={"Origin": "http://evil.test"}).status_code
        == 403
    )
    assert db_session.scalar(select(func.count()).select_from(RevokedToken)) == 0
    assert replay(client, token).status_code == 200


def test_expired_durable_record_does_not_block_other_token(
    client, db_session, test_user
):
    rev.persist_revocation(db_session, "a" * 32, int(time.time()) - 1)
    db_session.commit()
    assert db_session.scalar(select(func.count()).select_from(RevokedToken)) == 0
    assert replay(client, create_access_token(test_user.id)).status_code == 200


def test_sql_read_failure_returns_503(client, monkeypatch, db_session):
    login(client)
    monkeypatch.setattr(db_session, "scalar", Mock(side_effect=SQLAlchemyError()))
    assert client.get("/auth/me").status_code == 503
