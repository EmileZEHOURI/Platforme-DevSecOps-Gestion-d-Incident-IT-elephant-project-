
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

TRUSTED_ORIGIN = "https://incidents.example.test"


@pytest.fixture
def production_settings(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(
        settings,
        "frontend_origin",
        TRUSTED_ORIGIN,
    )


@pytest.mark.parametrize(
    "headers",
    [
        {"Origin": "https://evil.example"},
        {"Referer": "https://evil.example/page"},
        {},
    ],
)
def test_csrf_rejects_untrusted_requests(
    production_settings,
    headers,
):
    with TestClient(app) as client:
        response = client.post(
            "/auth/logout",
            headers=headers,
        )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Origine de la requête non autorisée."
    )


def test_csrf_accepts_trusted_origin(
    production_settings,
    db_session,
):
    with TestClient(app) as client:
        response = client.post(
            "/auth/logout",
            headers={"Origin": TRUSTED_ORIGIN},
        )

    assert response.status_code == 401


def test_csrf_accepts_trusted_referer(
    production_settings,
    db_session,
):
    with TestClient(app) as client:
        response = client.post(
            "/auth/logout",
            headers={
                "Referer": f"{TRUSTED_ORIGIN}/dashboard"
            },
        )

    assert response.status_code == 401