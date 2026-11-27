
import os
import time
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from redis import Redis

from app.core.config import settings
from app.main import app
from app.security import login_rate_limit

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_REAL_REDIS_TESTS") != "1",
    reason="Tests Redis réels non activés.",
)


@pytest.fixture
def real_redis(monkeypatch):
    # Base Redis 15 réservée à ces tests.
    client = Redis.from_url(
        "redis://127.0.0.1:6380/15",
        socket_connect_timeout=2,
        socket_timeout=2,
    )

    assert client.ping()

    keys_to_delete = set()

    def register(ip, email):
        keys_to_delete.add(
            login_rate_limit.make_key("ip", ip)
        )
        keys_to_delete.add(
            login_rate_limit.make_key(
                "account",
                email.strip().lower(),
            )
        )

    monkeypatch.setattr(
        login_rate_limit,
        "get_redis_client",
        lambda: client,
    )

    monkeypatch.setattr(settings, "environment", "test")
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

    try:
        yield register
    finally:
        if keys_to_delete:
            client.delete(*keys_to_delete)
        client.close()


def login(client, email):
    return client.post(
        "/auth/login",
        json={
            "email": email,
            "password": "incorrect-password",
        },
    )


def test_real_redis_limits_account_across_clients(
    real_redis,
    db_session,
    monkeypatch,
):
    monkeypatch.setattr(
        login_rate_limit,
        "ACCOUNT_LIMIT",
        2,
    )

    email = f"{uuid4().hex}@example.com"
    ip_a = "192.0.2.101"
    ip_b = "192.0.2.102"

    real_redis(ip_a, email)
    real_redis(ip_b, email)

    with (
        TestClient(
            app,
            client=(ip_a, 50000),
        ) as client_a,
        TestClient(
            app,
            client=(ip_b, 50001),
        ) as client_b,
    ):
        assert login(client_a, email).status_code == 401
        assert login(client_b, email).status_code == 401

        blocked = login(client_a, email)

    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) > 0


def test_real_redis_limits_ip(
    real_redis,
    db_session,
    monkeypatch,
):
    monkeypatch.setattr(
        login_rate_limit,
        "IP_LIMIT",
        2,
    )

    ip = "192.0.2.103"
    emails = [
        f"{uuid4().hex}@example.com"
        for _ in range(3)
    ]

    for email in emails:
        real_redis(ip, email)

    with TestClient(
        app,
        client=(ip, 50000),
    ) as client:
        assert login(client, emails[0]).status_code == 401
        assert login(client, emails[1]).status_code == 401

        blocked = login(client, emails[2])

    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) > 0


def test_real_redis_expiration(
    real_redis,
    db_session,
    monkeypatch,
):
    monkeypatch.setattr(
        login_rate_limit,
        "ACCOUNT_LIMIT",
        1,
    )

    monkeypatch.setattr(
        login_rate_limit,
        "ACCOUNT_WINDOW",
        1,
    )

    ip = "192.0.2.104"
    email = f"{uuid4().hex}@example.com"

    real_redis(ip, email)

    with TestClient(
        app,
        client=(ip, 50000),
    ) as client:
        first = login(client, email)
        assert first.status_code == 401

        blocked = login(client, email)
        assert blocked.status_code == 429

        time.sleep(1.2)

        allowed = login(client, email)

    assert allowed.status_code == 401
