import time

import fakeredis
import pytest

from fastapi.testclient import TestClient
from redis.exceptions import RedisError

from app.core.config import settings
from app.main import app
from app.security import login_rate_limit


@pytest.fixture
def api_client(rate_limit_enabled):
    with TestClient(
        app,
        client=("127.0.0.1", 50000),
    ) as client:
        yield client

@pytest.fixture
def rate_limit_enabled(monkeypatch, db_session):
    """Active le limiteur avec un Redis simulé."""

    redis_client = fakeredis.FakeRedis()

    monkeypatch.setattr(
        settings,
        "environment",
        "test",
    )

    monkeypatch.setattr(
        settings,
        "login_rate_limit_enabled",
        True,
    )

    monkeypatch.setattr(
        settings,
        "csrf_protection_enabled",
        False,
    )

    monkeypatch.setattr(
        login_rate_limit,
        "get_redis_client",
        lambda: redis_client,
    )

    return redis_client


def attempt_login(client, email):
    return client.post(
        "/auth/login",
        json={
            "email": email,
            "password": "incorrect-password",
        },
    )



def test_account_rate_limit_returns_429(
    api_client,
):
    """Le compte est limité après 10 tentatives."""

    for _ in range(10):
        response = attempt_login(
            api_client,
            "unknown@example.com",
        )
        assert response.status_code == 401

    response = attempt_login(
        api_client,
        "unknown@example.com",
    )

    assert response.status_code == 429

    assert int(response.headers["Retry-After"]) > 0

    assert "Trop de tentatives" in (response.json()["detail"])


def test_ip_rate_limit_returns_429(
    api_client,
):
    """Une IP est limitée après 20 tentatives."""

    for index in range(20):
        response = attempt_login(
            api_client,
            f"unknown{index}@example.com",
        )

        assert response.status_code == 401

    response = attempt_login(
        api_client,
        "another@example.com",
    )

    assert response.status_code == 429
    assert int(response.headers["Retry-After"]) > 0


def test_redis_failure_returns_503(
    api_client,
    monkeypatch,
):
    """L'API refuse la connexion si Redis échoue."""

    def unavailable_redis():
        raise RedisError("Redis unavailable")

    monkeypatch.setattr(
        login_rate_limit,
        "get_redis_client",
        unavailable_redis,
    )

    response = attempt_login(
        api_client,
        "unknown@example.com",
    )

    assert response.status_code == 503
    assert response.json()["detail"] == ("Service temporairement indisponible.")


def test_login_allowed_after_window_expiration(
    api_client,
    monkeypatch,
):
    """Une nouvelle tentative est possible après expiration."""

    monkeypatch.setattr(
        login_rate_limit,
        "ACCOUNT_LIMIT",
        2,
    )

    monkeypatch.setattr(
        login_rate_limit,
        "ACCOUNT_WINDOW",
        1,
    )

    for _ in range(2):
        response = attempt_login(
            api_client,
            "unknown@example.com",
        )
        assert response.status_code == 401

    blocked = attempt_login(
        api_client,
        "unknown@example.com",
    )

    assert blocked.status_code == 429

    # Fenêtre volontairement réduite à une seconde.
    time.sleep(1.2)

    allowed = attempt_login(
        api_client,
        "unknown@example.com",
    )

    # Le rate limiter autorise la nouvelle tentative.
    # Le mot de passe reste incorrect.
    assert allowed.status_code == 401


def test_login_endpoint_calls_rate_limiter(
    api_client,
    monkeypatch,
):
    from app.api.routes import auth as auth_routes

    calls = []

    def fake_rate_limit(
        *,
        ip_address: str,
        email: str,
    ) -> int:
        calls.append((ip_address, email))
        return 60

    monkeypatch.setattr(
        auth_routes,
        "check_login_rate_limit",
        fake_rate_limit,
    )

    response = attempt_login(
        api_client,
        "unknown@example.com",
    )

    assert calls == [
        ("127.0.0.1", "unknown@example.com")
    ]

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "60"
