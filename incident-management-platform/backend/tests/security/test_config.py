
import secrets

import pytest
from pydantic import ValidationError

from app.core.config import Settings

VALID_ORIGIN = "https://incidents.example.com"



def make_settings(**overrides):
    """Construit une configuration de test sans charger .env."""

    values = {
        "database_url": (
            "postgresql://test:test@localhost/config_test"
        ),
        "jwt_secret_key": secrets.token_hex(32),
        "environment": "production",
        "frontend_origin": VALID_ORIGIN,
        "redis_url": "redis://localhost:6379/0",
    }

    values.update(overrides)

    return Settings(
        _env_file=None,
        **values,
    )



def test_valid_production_configuration():
    settings = make_settings()

    assert settings.environment == "production"
    assert settings.frontend_origin == VALID_ORIGIN
    assert settings.jwt_algorithm == "HS256"
    assert settings.access_token_expire_minutes == 30


@pytest.mark.parametrize(
    "environment",
    ["prod", "staging", "PRODUCTION", ""],
)
def test_invalid_environment_is_rejected(environment):
    with pytest.raises(ValidationError):
        make_settings(environment=environment)


def test_short_jwt_secret_is_rejected_in_production():
    with pytest.raises(
        ValidationError,
        match="JWT_SECRET_KEY",
    ):
        make_settings(jwt_secret_key="a" * 31)


@pytest.mark.parametrize(
    "origin",
    [
        None,
        "",
        "http://incidents.example.com",
        "https://incidents.example.com/",
        "https://incidents.example.com/login",
        "https://incidents.example.com?x=1",
        "https://user:pass@incidents.example.com",
        "https://incidents.example.com:invalid",
    ],
)
def test_invalid_production_origin_is_rejected(origin):
    with pytest.raises(
        ValidationError,
        match="FRONTEND_ORIGIN",
    ):
        make_settings(frontend_origin=origin)


def test_invalid_jwt_algorithm_is_rejected():
    with pytest.raises(ValidationError):
        make_settings(jwt_algorithm="none")


@pytest.mark.parametrize(
    "minutes",
    [0, -1],
)
def test_invalid_token_lifetime_is_rejected(minutes):
    with pytest.raises(ValidationError):
        make_settings(access_token_expire_minutes=minutes)


def test_development_allows_local_configuration():
    settings = make_settings(
        environment="development",
        frontend_origin=None,
        jwt_secret_key="local-dev-secret",
    )

    assert settings.environment == "development"


def test_e2e_can_enable_csrf_with_http_origin():
    settings = make_settings(
        environment="test",
        frontend_origin="http://127.0.0.1:3017",
        csrf_protection_enabled=True,
        jwt_secret_key="local-test-secret",
    )

    assert settings.environment == "test"
    assert settings.csrf_protection_enabled is True
    assert settings.frontend_origin == (
        "http://127.0.0.1:3017"
    )

def test_production_requires_redis_url():
    with pytest.raises(
        ValidationError,
        match="REDIS_URL",
    ):
        make_settings(redis_url=None)


def test_test_environment_allows_no_redis_when_disabled():
    settings = make_settings(
        environment="test",
        redis_url=None,
        login_rate_limit_enabled=False,
    )

    assert settings.redis_url is None
    assert settings.login_rate_limit_enabled is False