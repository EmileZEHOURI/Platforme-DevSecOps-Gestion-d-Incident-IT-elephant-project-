
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.main import app
from app.models.user import User
from app.models.incident import Incident
from app.models.history import IncidentHistory
from app.models.audit_log import AuditLog
from app.models.enums import (
    IncidentPriority,
    IncidentStatus,
    IncidentHistoryAction,
    AuditEventType,
    AuditResult,
)


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
            "title": "Incident de test US-09",
            "description": (
                "Incident créé pour tester le démarrage "
                "du traitement par un responsable."
            ),
            "category": "ANOMALY",
            "priority": "MEDIUM",
        },
    )

    assert response.status_code == 201, response.text
    return response.json()["id"]


def change_status(
    client: TestClient,
    incident_id: int,
    new_status: str,
):
    return client.patch(
        f"/incidents/{incident_id}/status",
        json={"status": new_status},
    )


def prepare_incident(
    db_session: Session,
    incident_id: int,
    *,
    assigned_to_id: int | None,
    incident_status: IncidentStatus = IncidentStatus.OPEN,
) -> None:
    incident = db_session.get(Incident, incident_id)

    assert incident is not None

    incident.assigned_to_id = assigned_to_id
    incident.status = incident_status

    if incident_status in (
        IncidentStatus.RESOLVED,
        IncidentStatus.CLOSED,
    ):
        now = datetime.now(timezone.utc)

        incident.resolution = "Problème corrigé."
        incident.resolved_at = now

        if incident_status == IncidentStatus.CLOSED:
            incident.closed_at = now

    db_session.flush()


def get_incident_from_db(
    db_session: Session,
    incident_id: int,
) -> Incident:
    db_session.expire_all()

    incident = db_session.get(Incident, incident_id)

    assert incident is not None
    return incident


def get_status_history(
    db_session: Session,
    incident_id: int,
) -> list[IncidentHistory]:
    statement = (
        select(IncidentHistory)
        .where(
            IncidentHistory.incident_id == incident_id,
            IncidentHistory.action == IncidentHistoryAction.STATUS_CHANGED,
        )
        .order_by(IncidentHistory.id)
    )

    return list(db_session.scalars(statement).all())


def get_status_audits(
    db_session: Session,
    actor_id: int,
) -> list[AuditLog]:
    statement = select(AuditLog).where(
        AuditLog.user_id == actor_id,
        AuditLog.event_type == AuditEventType.INCIDENT_STATUS_CHANGED,
        AuditLog.result == AuditResult.SUCCESS,
    )

    return list(db_session.scalars(statement).all())


# ==========================================================
# 1. TECHNICIAN OU ADMIN RESPONSABLE : SUCCÈS
# ==========================================================


@pytest.mark.parametrize(
    "actor_fixture",
    [
        "technician_user",
        "admin_user",
    ],
    ids=[
        "technician-assigned",
        "admin-self-assigned",
    ],
)
def test_assigned_actor_can_start_incident(
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

        prepare_incident(
            db_session,
            incident_id,
            assigned_to_id=actor.id,
        )

        audits_before = len(
            get_status_audits(db_session, actor.id)
        )

        response = change_status(
            actor_client,
            incident_id,
            "IN_PROGRESS",
        )

        assert response.status_code == 200, response.text

        body = response.json()

        assert body["id"] == incident_id
        assert body["status"] == "IN_PROGRESS"
        assert body["priority"] == "MEDIUM"
        assert body["assigned_to_id"] == actor.id
        assert body["created_by_id"] == test_user.id

        # Vérifier la persistance en base
        incident = get_incident_from_db(
            db_session,
            incident_id,
        )

        assert incident.status == IncidentStatus.IN_PROGRESS
        assert incident.priority == IncidentPriority.MEDIUM
        assert incident.assigned_to_id == actor.id

        # Vérifier l'historique métier
        history = get_status_history(
            db_session,
            incident_id,
        )

        assert len(history) == 1
        assert history[0].actor_id == actor.id
        assert history[0].action == IncidentHistoryAction.STATUS_CHANGED
        assert history[0].field_name == "status"
        assert history[0].old_value == "OPEN"
        assert history[0].new_value == "IN_PROGRESS"

        # Vérifier l'audit
        audits_after = get_status_audits(
            db_session,
            actor.id,
        )

        assert len(audits_after) == audits_before + 1


# ==========================================================
# 2. IDEMPOTENCE : IN_PROGRESS -> IN_PROGRESS
# ==========================================================


def test_start_incident_is_idempotent(
    db_session: Session,
    test_user: User,
    technician_user: User,
) -> None:
    with (
        TestClient(app, client=("127.0.0.1", 50000)) as creator,
        TestClient(app, client=("127.0.0.1", 50000)) as technician,
    ):
        login(creator, test_user)
        login(technician, technician_user)

        incident_id = create_incident(creator)

        prepare_incident(
            db_session,
            incident_id,
            assigned_to_id=technician_user.id,
            incident_status=IncidentStatus.IN_PROGRESS,
        )

        history_before = len(
            get_status_history(db_session, incident_id)
        )

        audits_before = len(
            get_status_audits(db_session, technician_user.id)
        )

        response = change_status(
            technician,
            incident_id,
            "IN_PROGRESS",
        )

        assert response.status_code == 200, response.text
        assert response.json()["status"] == "IN_PROGRESS"

        incident = get_incident_from_db(
            db_session,
            incident_id,
        )

        assert incident.status == IncidentStatus.IN_PROGRESS
        assert incident.assigned_to_id == technician_user.id

        assert len(
            get_status_history(db_session, incident_id)
        ) == history_before

        assert len(
            get_status_audits(db_session, technician_user.id)
        ) == audits_before


# ==========================================================
# 3. UTILISATEURS NON AUTORISÉS : 403
# ==========================================================


@pytest.mark.parametrize(
    "actor_fixture, assignee_fixture",
    [
        pytest.param(
            "test_user",
            "test_user",
            id="user-even-if-assigned",
        ),
        pytest.param(
            "other_technician_user",
            "technician_user",
            id="technician-not-responsible",
        ),
        pytest.param(
            "admin_user",
            "technician_user",
            id="admin-not-responsible",
        ),
    ],
)
def test_unauthorized_actor_cannot_start_incident(
    request: pytest.FixtureRequest,
    actor_fixture: str,
    assignee_fixture: str,
    db_session: Session,
    test_user: User,
) -> None:
    actor: User = request.getfixturevalue(actor_fixture)
    assignee: User = request.getfixturevalue(assignee_fixture)

    with (
        TestClient(app, client=("127.0.0.1", 50000)) as creator,
        TestClient(app, client=("127.0.0.1", 50000)) as actor_client,
    ):
        login(creator, test_user)
        login(actor_client, actor)

        incident_id = create_incident(creator)

        prepare_incident(
            db_session,
            incident_id,
            assigned_to_id=assignee.id,
        )

        audits_before = len(
            get_status_audits(db_session, actor.id)
        )

        response = change_status(
            actor_client,
            incident_id,
            "IN_PROGRESS",
        )

        assert response.status_code == 403, response.text

        incident = get_incident_from_db(
            db_session,
            incident_id,
        )

        assert incident.status == IncidentStatus.OPEN
        assert incident.assigned_to_id == assignee.id

        assert get_status_history(db_session, incident_id) == []

        assert len(
            get_status_audits(db_session, actor.id)
        ) == audits_before


# ==========================================================
# 4. INCIDENT NON ASSIGNÉ : 409
# ==========================================================


def test_cannot_start_unassigned_incident(
    db_session: Session,
    test_user: User,
    technician_user: User,
) -> None:
    with (
        TestClient(app, client=("127.0.0.1", 50000)) as creator,
        TestClient(app, client=("127.0.0.1", 50000)) as technician,
    ):
        login(creator, test_user)
        login(technician, technician_user)

        incident_id = create_incident(creator)

        prepare_incident(
            db_session,
            incident_id,
            assigned_to_id=None,
        )

        response = change_status(
            technician,
            incident_id,
            "IN_PROGRESS",
        )

        assert response.status_code == 409, response.text

        incident = get_incident_from_db(
            db_session,
            incident_id,
        )

        assert incident.status == IncidentStatus.OPEN
        assert incident.assigned_to_id is None

        assert get_status_history(db_session, incident_id) == []
        assert get_status_audits(db_session, technician_user.id) == []


# ==========================================================
# 5. INCIDENT RESOLVED OU CLOSED : 409
# ==========================================================


@pytest.mark.parametrize(
    "incident_status",
    [
        IncidentStatus.RESOLVED,
        IncidentStatus.CLOSED,
    ],
    ids=[
        "resolved-incident",
        "closed-incident",
    ],
)
def test_cannot_start_finished_incident(
    incident_status: IncidentStatus,
    db_session: Session,
    test_user: User,
    technician_user: User,
) -> None:
    with (
        TestClient(app, client=("127.0.0.1", 50000)) as creator,
        TestClient(app, client=("127.0.0.1", 50000)) as technician,
    ):
        login(creator, test_user)
        login(technician, technician_user)

        incident_id = create_incident(creator)

        prepare_incident(
            db_session,
            incident_id,
            assigned_to_id=technician_user.id,
            incident_status=incident_status,
        )

        response = change_status(
            technician,
            incident_id,
            "IN_PROGRESS",
        )

        assert response.status_code == 409, response.text

        incident = get_incident_from_db(
            db_session,
            incident_id,
        )

        assert incident.status == incident_status
        assert incident.assigned_to_id == technician_user.id

        assert get_status_history(db_session, incident_id) == []
        assert get_status_audits(db_session, technician_user.id) == []


# ==========================================================
# 6. TRANSITIONS INTERDITES : 409
# ==========================================================


@pytest.mark.parametrize(
    "current_status, requested_status",
    [
        pytest.param(
            IncidentStatus.OPEN,
            "OPEN",
            id="open-to-open",
        ),
        pytest.param(
            IncidentStatus.OPEN,
            "RESOLVED",
            id="open-to-resolved",
        ),
        pytest.param(
            IncidentStatus.OPEN,
            "CLOSED",
            id="open-to-closed",
        ),
        pytest.param(
            IncidentStatus.IN_PROGRESS,
            "OPEN",
            id="in-progress-to-open",
        ),
        pytest.param(
            IncidentStatus.IN_PROGRESS,
            "RESOLVED",
            id="in-progress-to-resolved",
        ),
    ],
)
def test_invalid_status_transition(
    current_status: IncidentStatus,
    requested_status: str,
    db_session: Session,
    test_user: User,
    technician_user: User,
) -> None:
    with (
        TestClient(app, client=("127.0.0.1", 50000)) as creator,
        TestClient(app, client=("127.0.0.1", 50000)) as technician,
    ):
        login(creator, test_user)
        login(technician, technician_user)

        incident_id = create_incident(creator)

        prepare_incident(
            db_session,
            incident_id,
            assigned_to_id=technician_user.id,
            incident_status=current_status,
        )

        response = change_status(
            technician,
            incident_id,
            requested_status,
        )

        assert response.status_code == 409, response.text

        incident = get_incident_from_db(
            db_session,
            incident_id,
        )

        assert incident.status == current_status
        assert incident.assigned_to_id == technician_user.id

        assert get_status_history(db_session, incident_id) == []
        assert get_status_audits(db_session, technician_user.id) == []


# ==========================================================
# 7. INCIDENT INEXISTANT : 404
# ==========================================================


def test_start_incident_not_found(
    technician_user: User,
) -> None:
    with TestClient(
        app,
        client=("127.0.0.1", 50000),
    ) as technician:
        login(technician, technician_user)

        response = change_status(
            technician,
            incident_id=999999999,
            new_status="IN_PROGRESS",
        )

        assert response.status_code == 404, response.text


# ==========================================================
# 8. PAYLOAD INVALIDE : 422
# ==========================================================


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"status": "WAITING"},
        {"status": None},
        {"status": 123},
        {
            "status": "IN_PROGRESS",
            "unexpected_field": True,
        },
    ],
    ids=[
        "missing-status",
        "unknown-status",
        "null-status",
        "numeric-status",
        "extra-field",
    ],
)
def test_change_status_invalid_payload(
    payload: dict,
    db_session: Session,
    test_user: User,
    technician_user: User,
) -> None:
    with (
        TestClient(app, client=("127.0.0.1", 50000)) as creator,
        TestClient(app, client=("127.0.0.1", 50000)) as technician,
    ):
        login(creator, test_user)
        login(technician, technician_user)

        incident_id = create_incident(creator)

        prepare_incident(
            db_session,
            incident_id,
            assigned_to_id=technician_user.id,
        )

        response = technician.patch(
            f"/incidents/{incident_id}/status",
            json=payload,
        )

        assert response.status_code == 422, response.text

        incident = get_incident_from_db(
            db_session,
            incident_id,
        )

        assert incident.status == IncidentStatus.OPEN
        assert incident.assigned_to_id == technician_user.id

        assert get_status_history(db_session, incident_id) == []
        assert get_status_audits(db_session, technician_user.id) == []


# ==========================================================
# 9. UTILISATEUR NON AUTHENTIFIÉ : 401
# ==========================================================


def test_change_status_requires_authentication() -> None:
    with TestClient(
        app,
        client=("127.0.0.1", 50000),
    ) as client:
        response = client.patch(
            "/incidents/999999999/status",
            json={"status": "IN_PROGRESS"},
        )

        assert response.status_code == 401, response.text
