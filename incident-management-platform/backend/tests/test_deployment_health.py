from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient
from redis.exceptions import ConnectionError as RedisConnectionError
from sqlalchemy.exc import OperationalError

from app.core.config import Settings
from app.core.database import get_db
from app.main import app


@pytest.mark.parametrize(
    "origin,expected",
    [
        ("https://frontend.example.com", 200),
        ("http://localhost:3000", 400),
        ("https://attacker.example.com", 400),
    ],
)
def test_production_cors_uses_exact_configured_origin(origin, expected):
    settings = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://unused",
        jwt_secret_key="a" * 64,
        environment="production",
        redis_url="redis://localhost:6379",
        frontend_origin="https://frontend.example.com",
    )
    application = FastAPI()
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    with TestClient(application) as client:
        response = client.options(
            "/auth/login",
            headers={"Origin": origin, "Access-Control-Request-Method": "POST"},
        )
    assert response.status_code == expected
    assert response.headers.get("access-control-allow-origin") == (
        origin if expected == 200 else None
    )


def test_database_health_hides_failure_details():
    db = Mock()
    db.execute.side_effect = OperationalError(
        "secret database address", {}, Exception("secret password")
    )
    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = lambda: db
    try:
        with TestClient(app) as client:
            response = client.get("/health/database")
        assert response.status_code == 503
        assert response.json() == {"detail": "Database unavailable."}
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


@pytest.mark.parametrize(
    "result", [True, False, RedisConnectionError("secret redis address")]
)
def test_redis_health(monkeypatch, result):
    client = Mock()
    if isinstance(result, Exception):
        client.ping.side_effect = result
    else:
        client.ping.return_value = result
    monkeypatch.setattr("app.main.get_redis_client", lambda: client)
    with TestClient(app) as test_client:
        response = test_client.get("/health/redis")
    assert response.status_code == (200 if result is True else 503)
    assert response.json() == (
        {"status": "ok", "redis": "connected"}
        if result is True
        else {"detail": "Redis unavailable."}
    )


def test_deployment_diagnostic_hides_invalid_configuration():
    import os
    import subprocess
    import sys
    from pathlib import Path

    env = os.environ.copy()
    env.update(
        ENVIRONMENT="production",
        DATABASE_URL="postgresql+psycopg://unused",
        JWT_SECRET_KEY="sentinel-secret",
        FRONTEND_ORIGIN="https://frontend.example.com",
        REDIS_URL="redis://localhost:6379",
    )
    result = subprocess.run(
        [sys.executable, "-m", "scripts.verify_deployment"],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 1
    assert '"configuration_error": "ValidationError"' in result.stdout
    assert "sentinel-secret" not in result.stdout + result.stderr
    assert result.stderr == ""
