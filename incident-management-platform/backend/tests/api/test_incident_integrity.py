import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from app.main import app
from app.models.audit_log import AuditLog
from app.models.enums import AuditEventType, IncidentHistoryAction
from app.models.history import IncidentHistory
from app.models.incident import Incident
from app.repositories.audit_repository import AuditRepository
from app.repositories.incident_history_repository import IncidentHistoryRepository

PAYLOAD = {
    "title": "Incident réseau",
    "description": "Le réseau est indisponible.",
    "category": "ANOMALY",
}


@pytest.fixture
def authenticated_client(test_user):
    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        assert (
            client.post(
                "/auth/login", json={"email": test_user.email, "password": "password"}
            ).status_code
            == 200
        )
        yield client


def test_creation_persists_history_and_audit(
    authenticated_client, db_session, test_user
):
    response = authenticated_client.post("/incidents", json=PAYLOAD)
    assert response.status_code == 201
    body = response.json()
    assert body["priority"] == "MEDIUM"
    assert body["status"] == "OPEN"
    assert body["assigned_to_id"] is None
    assert body["created_by_id"] == test_user.id
    assert body["created_at"]
    history = db_session.scalars(
        select(IncidentHistory).where(IncidentHistory.incident_id == body["id"])
    ).one()
    assert history.action == IncidentHistoryAction.INCIDENT_CREATED
    assert history.actor_id == test_user.id
    audit = db_session.scalars(
        select(AuditLog).where(AuditLog.event_type == AuditEventType.INCIDENT_CREATED)
    ).one()
    assert audit.user_id == test_user.id
    assert audit.resource_id == body["id"]
    assert audit.resource_type == "incident"
    assert audit.result == "SUCCESS"
    assert audit.details == {}
    second = authenticated_client.post("/incidents", json=PAYLOAD)
    assert second.status_code == 201
    assert second.json()["reference"] != body["reference"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("title", " " * 5),
        ("description", " " * 10),
        ("title", "x" * 151),
        ("description", "x" * 5001),
        ("category", "INVALID"),
        ("priority", "INVALID"),
        ("created_by_id", 999),
        ("status", "CLOSED"),
        ("assigned_to_id", 999),
    ],
)
def test_invalid_creation_returns_422(authenticated_client, db_session, field, value):
    assert (
        authenticated_client.post(
            "/incidents", json={**PAYLOAD, field: value}
        ).status_code
        == 422
    )
    assert db_session.scalar(select(func.count()).select_from(Incident)) == 0


def test_deactivated_account_cannot_create(authenticated_client, db_session, test_user):
    test_user.is_active = False
    db_session.commit()
    assert authenticated_client.post("/incidents", json=PAYLOAD).status_code == 401
    assert db_session.scalar(select(func.count()).select_from(Incident)) == 0


@pytest.mark.parametrize("repository", [IncidentHistoryRepository, AuditRepository])
def test_failed_write_rolls_back_everything(
    authenticated_client, db_session, monkeypatch, repository
):
    original = repository.create

    def fail_after_write(self, **kwargs):
        original(self, **kwargs)
        raise SQLAlchemyError("Internal diagnostic that must not be exposed")

    with monkeypatch.context() as patch:
        patch.setattr(repository, "create", fail_after_write)
        response = authenticated_client.post("/incidents", json=PAYLOAD)
    assert response.status_code == 500
    assert response.json() == {"detail": "Échec de la création de l'incident"}
    assert db_session.scalar(select(func.count()).select_from(Incident)) == 0
    assert db_session.scalar(select(func.count()).select_from(IncidentHistory)) == 0
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(AuditLog)
            .where(AuditLog.event_type == AuditEventType.INCIDENT_CREATED)
        )
        == 0
    )
    assert authenticated_client.post("/incidents", json=PAYLOAD).status_code == 201
