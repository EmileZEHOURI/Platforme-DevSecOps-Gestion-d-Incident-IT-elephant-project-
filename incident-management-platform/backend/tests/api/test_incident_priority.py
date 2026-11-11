
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.main import app
from app.models.enums import (
    AuditEventType,
    AuditResult,
    IncidentHistoryAction,
    IncidentPriority,
    IncidentStatus,
)
from app.models.incident import Incident
from app.models.user import User


# ==========================================================
# HELPERS
# ==========================================================


def login(client: TestClient, user: User) -> None:
    response = client.post(
        "/auth/login",
        json={
            "email": user.email,
            "password": "password",
        },
    )

    assert response.status_code == 200, response.text


def create_incident(client: TestClient) -> int:
    response = client.post(
        "/incidents",
        json={
            "title": "Incident de test US-08",
            "description": "Incident créé pour vérifier le changement de priorité.",
            "category": "ANOMALY",
            "priority": "MEDIUM",
        },
    )

    assert response.status_code == 201, response.text
    return response.json()["id"]


def change_priority(
    client: TestClient,
    incident_id: int,
    priority: str,
):
    return client.patch(
        f"/incidents/{incident_id}/priority",
        json={"priority": priority},
    )


def get_incident_from_db(
    db_session: Session,
    incident_id: int,
) -> Incident:
    db_session.expire_all()

    incident = db_session.get(Incident, incident_id)
    assert incident is not None

    return incident


def get_priority_history(
    db_session: Session,
    incident_id: int,
) -> list[dict]:
    rows = db_session.execute(
        text(
            """
            SELECT
                action,
                actor_id,
                field_name,
                old_value,
                new_value
            FROM incident_history
            WHERE incident_id = :incident_id
              AND action = :action
            """
        ),
        {
            "incident_id": incident_id,
            "action": IncidentHistoryAction.PRIORITY_CHANGED.value,
        },
    ).mappings().all()

    return [dict(row) for row in rows]


def count_priority_audits(
    db_session: Session,
    actor_id: int,
) -> int:
    return db_session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM audit_logs
            WHERE user_id = :actor_id
              AND event_type = :event_type
              AND result = :result
            """
        ),
        {
            "actor_id": actor_id,
            "event_type": AuditEventType.INCIDENT_PRIORITY_CHANGED.value,
            "result": AuditResult.SUCCESS.value,
        },
    ).scalar_one()


# ==========================================================
# 1. ADMIN MODIFIE LA PRIORITÉ : MEDIUM -> CRITICAL
# ==========================================================


def test_admin_changes_incident_priority(
    db_session: Session,
    test_user: User,
    admin_user: User,
) -> None:

    with (
        TestClient(app, client=("127.0.0.1", 50000)) as creator,
        TestClient(app, client=("127.0.0.1", 50000)) as admin,
    ):
        login(creator, test_user)
        login(admin, admin_user)

        incident_id = create_incident(creator)

        incident_before = get_incident_from_db(
            db_session,
            incident_id,
        )

        assert incident_before.priority == IncidentPriority.MEDIUM
        assert incident_before.status == IncidentStatus.OPEN

        audit_before = count_priority_audits(
            db_session,
            admin_user.id,
        )

        response = change_priority(
            admin,
            incident_id,
            "CRITICAL",
        )

        assert response.status_code == 200, response.text

        body = response.json()

        assert body["id"] == incident_id
        assert body["priority"] == "CRITICAL"
        assert body["status"] == "OPEN"
        assert body["created_by_id"] == test_user.id

        # Vérifier la modification en base
        incident_after = get_incident_from_db(
            db_session,
            incident_id,
        )

        assert incident_after.priority == IncidentPriority.CRITICAL
        assert incident_after.status == IncidentStatus.OPEN

        # Vérifier l'historique métier
        history = get_priority_history(
            db_session,
            incident_id,
        )

        assert len(history) == 1

        assert history[0]["action"] == "PRIORITY_CHANGED"
        assert history[0]["actor_id"] == admin_user.id
        assert history[0]["field_name"] == "priority"
        assert history[0]["old_value"] == "MEDIUM"
        assert history[0]["new_value"] == "CRITICAL"

        # Vérifier l'audit
        audit_after = count_priority_audits(
            db_session,
            admin_user.id,
        )

        assert audit_after == audit_before + 1


# ==========================================================
# 2. PRIORITÉ IDENTIQUE : AUCUN CHANGEMENT
# ==========================================================


def test_admin_sets_same_incident_priority(
    db_session: Session,
    test_user: User,
    admin_user: User,
) -> None:

    with (
        TestClient(app, client=("127.0.0.1", 50000)) as creator,
        TestClient(app, client=("127.0.0.1", 50000)) as admin,
    ):
        login(creator, test_user)
        login(admin, admin_user)

        incident_id = create_incident(creator)

        history_before = get_priority_history(
            db_session,
            incident_id,
        )

        audit_before = count_priority_audits(
            db_session,
            admin_user.id,
        )

        response = change_priority(
            admin,
            incident_id,
            "MEDIUM",
        )

        assert response.status_code == 200, response.text

        body = response.json()

        assert body["id"] == incident_id
        assert body["priority"] == "MEDIUM"
        assert body["status"] == "OPEN"

        incident = get_incident_from_db(
            db_session,
            incident_id,
        )

        assert incident.priority == IncidentPriority.MEDIUM

        history_after = get_priority_history(
            db_session,
            incident_id,
        )

        audit_after = count_priority_audits(
            db_session,
            admin_user.id,
        )

        assert len(history_before) == 0
        assert len(history_after) == 0
        assert audit_after == audit_before


# ==========================================================
# 3. USER ET TECHNICIAN NE PEUVENT PAS MODIFIER
# ==========================================================


@pytest.mark.parametrize(
    "actor_fixture",
    [
        "test_user",
        "technician_user",
    ],
    ids=[
        "user-forbidden",
        "technician-forbidden",
    ],
)
def test_non_admin_cannot_change_priority(
    request: pytest.FixtureRequest,
    actor_fixture: str,
    db_session: Session,
    test_user: User,
) -> None:

    actor: User = request.getfixturevalue(actor_fixture)

    with (
        TestClient(app, client=("127.0.0.1", 50000)) as creator,
        TestClient(app, client=("127.0.0.1", 50000)) as actor_client,
    ):
        login(creator, test_user)
        login(actor_client, actor)

        incident_id = create_incident(creator)

        response = change_priority(
            actor_client,
            incident_id,
            "HIGH",
        )

        assert response.status_code == 403

        incident = get_incident_from_db(
            db_session,
            incident_id,
        )

        assert incident.priority == IncidentPriority.MEDIUM

        history = get_priority_history(
            db_session,
            incident_id,
        )

        assert history == []

        assert count_priority_audits(
            db_session,
            actor.id,
        ) == 0


# ==========================================================
# 4. INCIDENT CLOSED : MODIFICATION INTERDITE
# ==========================================================


def test_admin_cannot_change_closed_incident_priority(
    db_session: Session,
    test_user: User,
    technician_user: User,
    admin_user: User,
) -> None:

    with (
        TestClient(app, client=("127.0.0.1", 50000)) as creator,
        TestClient(app, client=("127.0.0.1", 50000)) as admin,
    ):
        login(creator, test_user)
        login(admin, admin_user)

        incident_id = create_incident(creator)

        # Les US de résolution et fermeture ne sont pas encore
        # disponibles : on prépare l'état CLOSED directement en DB.
        incident = db_session.get(Incident, incident_id)

        assert incident is not None

        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)

        incident.assigned_to_id = technician_user.id
        incident.status = IncidentStatus.CLOSED
        incident.resolution = "Incident résolu et définitivement fermé."
        incident.resolved_at = now
        incident.closed_at = now

        db_session.flush()

        audit_before = count_priority_audits(
            db_session,
            admin_user.id,
        )

        response = change_priority(
            admin,
            incident_id,
            "CRITICAL",
        )

        assert response.status_code == 409

        incident_after = get_incident_from_db(
            db_session,
            incident_id,
        )

        assert incident_after.priority == IncidentPriority.MEDIUM
        assert incident_after.status == IncidentStatus.CLOSED

        history = get_priority_history(
            db_session,
            incident_id,
        )

        assert history == []

        assert count_priority_audits(
            db_session,
            admin_user.id,
        ) == audit_before


# ==========================================================
# 5. INCIDENT INEXISTANT
# ==========================================================


def test_change_priority_incident_not_found(
    admin_user: User,
) -> None:

    with TestClient(
        app,
        client=("127.0.0.1", 50000),
    ) as admin:

        login(admin, admin_user)

        response = change_priority(
            admin,
            incident_id=999999999,
            priority="HIGH",
        )

        assert response.status_code == 404


# ==========================================================
# 6. PRIORITÉ INVALIDE : 422
# ==========================================================


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"priority": "EXTREME"},
        {"priority": None},
        {"priority": 123},
        {"priority": "MEDIUM", "unexpected_field": True},
    ],
    ids=[
        "missing-priority",
        "unknown-priority",
        "null-priority",
        "numeric-priority",
        "extra-field",
    ],
)
def test_change_priority_invalid_payload(
    payload: dict,
    test_user: User,
    admin_user: User,
    db_session: Session,
) -> None:

    with (
        TestClient(app, client=("127.0.0.1", 50000)) as creator,
        TestClient(app, client=("127.0.0.1", 50000)) as admin,
    ):
        login(creator, test_user)
        login(admin, admin_user)

        incident_id = create_incident(creator)

        response = admin.patch(
            f"/incidents/{incident_id}/priority",
            json=payload,
        )

        assert response.status_code == 422

        # Aucune modification ne doit avoir lieu
        incident = get_incident_from_db(
            db_session,
            incident_id,
        )

        assert incident.priority == IncidentPriority.MEDIUM
        assert get_priority_history(db_session, incident_id) == []


# ==========================================================
# 7. UTILISATEUR NON AUTHENTIFIÉ : 401
# ==========================================================


def test_change_priority_requires_authentication() -> None:

    with TestClient(
        app,
        client=("127.0.0.1", 50000),
    ) as client:

        response = client.patch(
            "/incidents/999999999/priority",
            json={"priority": "HIGH"},
        )

        assert response.status_code == 401
