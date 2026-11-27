from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.main import app
from app.models.audit_log import AuditLog
from app.models.enums import (
    AuditEventType,
    AuditResult,
    IncidentHistoryAction,
    IncidentPriority,
    IncidentStatus,
)
from app.models.history import IncidentHistory
from app.models.incident import Incident
from app.models.user import User

# ==========================================================
# HELPERS
# ==========================================================


def make_client() -> TestClient:
    # PostgreSQL attend une véritable IP dans audit_logs.ip_address.
    return TestClient(
        app,
        client=("127.0.0.1", 50000),
    )


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
            "title": "Incident de test US-11",
            "description": "Incident créé pour tester sa clôture.",
            "category": "ANOMALY",
            "priority": "MEDIUM",
        },
    )

    assert response.status_code == 201, response.text
    return response.json()["id"]


def close_incident(client: TestClient, incident_id: int):
    # Aucun body JSON requis.
    return client.patch(f"/incidents/{incident_id}/close")


def prepare_incident(
    db_session: Session,
    incident_id: int,
    *,
    assigned_to_id: int,
    incident_status: IncidentStatus = IncidentStatus.RESOLVED,
) -> None:
    incident = db_session.get(Incident, incident_id)
    assert incident is not None

    incident.assigned_to_id = assigned_to_id
    incident.status = incident_status

    incident.resolution = None
    incident.resolved_at = None
    incident.closed_at = None

    if incident_status in (
        IncidentStatus.RESOLVED,
        IncidentStatus.CLOSED,
    ):
        incident.resolution = "Redémarrage et vérification du service."
        incident.resolved_at = datetime.now(UTC)

    if incident_status == IncidentStatus.CLOSED:
        incident.closed_at = datetime.now(UTC)

    db_session.flush()


def get_incident_from_db(
    db_session: Session,
    incident_id: int,
) -> Incident:
    db_session.expire_all()

    incident = db_session.get(Incident, incident_id)
    assert incident is not None

    return incident


def get_close_history(
    db_session: Session,
    incident_id: int,
) -> list[IncidentHistory]:
    statement = (
        select(IncidentHistory)
        .where(
            IncidentHistory.incident_id == incident_id,
            IncidentHistory.action == IncidentHistoryAction.CLOSED,
        )
        .order_by(IncidentHistory.id)
    )

    return list(db_session.scalars(statement).all())


def get_close_audits(
    db_session: Session,
    actor_id: int,
) -> list[AuditLog]:
    statement = select(AuditLog).where(
        AuditLog.user_id == actor_id,
        AuditLog.event_type == AuditEventType.INCIDENT_CLOSED,
        AuditLog.result == AuditResult.SUCCESS,
    )

    return list(db_session.scalars(statement).all())


# ==========================================================
# 1. CLÔTURE AUTORISÉE : USER, ADMIN, TECHNICIAN CRÉATEUR
# ==========================================================


@pytest.mark.parametrize(
    "creator_fixture, actor_fixture, assignee_fixture",
    [
        pytest.param(
            "test_user",
            "test_user",
            "technician_user",
            id="user-creator",
        ),
        pytest.param(
            "test_user",
            "admin_user",
            "technician_user",
            id="admin-not-creator",
        ),
        pytest.param(
            "technician_user",
            "technician_user",
            "other_technician_user",
            id="technician-creator",
        ),
    ],
)
def test_authorized_actor_can_close_incident(
    request: pytest.FixtureRequest,
    creator_fixture: str,
    actor_fixture: str,
    assignee_fixture: str,
    db_session: Session,
) -> None:
    creator: User = request.getfixturevalue(creator_fixture)
    actor: User = request.getfixturevalue(actor_fixture)
    assignee: User = request.getfixturevalue(assignee_fixture)

    with (
        make_client() as creator_client,
        make_client() as actor_client,
    ):
        login(creator_client, creator)
        login(actor_client, actor)

        incident_id = create_incident(creator_client)

        prepare_incident(
            db_session,
            incident_id,
            assigned_to_id=assignee.id,
        )

        before_incident = get_incident_from_db(
            db_session,
            incident_id,
        )

        old_resolution = before_incident.resolution
        old_resolved_at = before_incident.resolved_at
        old_priority = before_incident.priority
        old_assignee = before_incident.assigned_to_id

        audits_before = len(get_close_audits(db_session, actor.id))

        before = datetime.now(UTC)

        response = close_incident(
            actor_client,
            incident_id,
        )

        after = datetime.now(UTC)

        assert response.status_code == 200, response.text

        body = response.json()

        assert body["id"] == incident_id
        assert body["status"] == "CLOSED"
        assert body["closed_at"] is not None
        assert body["resolution"] == old_resolution
        assert body["assigned_to_id"] == assignee.id
        assert body["priority"] == "MEDIUM"
        assert body["created_by_id"] == creator.id

        # Vérification des données enregistrées en PostgreSQL.
        incident = get_incident_from_db(
            db_session,
            incident_id,
        )

        assert incident.status == IncidentStatus.CLOSED
        assert incident.closed_at is not None

        # Les informations de résolution sont conservées.
        assert incident.resolution == old_resolution
        assert incident.resolved_at == old_resolved_at

        assert incident.priority == old_priority
        assert incident.priority == IncidentPriority.MEDIUM
        assert incident.assigned_to_id == old_assignee
        assert incident.created_by_id == creator.id

        # Date de clôture générée pendant la requête.
        closed_at = datetime.fromisoformat(body["closed_at"].replace("Z", "+00:00"))

        assert closed_at.tzinfo is not None
        assert before <= closed_at <= after

        # Historique métier : une seule clôture.
        history = get_close_history(
            db_session,
            incident_id,
        )

        assert len(history) == 1
        assert history[0].actor_id == actor.id
        assert history[0].action == IncidentHistoryAction.CLOSED
        assert history[0].field_name == "status"
        assert history[0].old_value == "RESOLVED"
        assert history[0].new_value == "CLOSED"

        # Audit applicatif.
        audits_after = get_close_audits(
            db_session,
            actor.id,
        )

        assert len(audits_after) == audits_before + 1


# ==========================================================
# 2. UTILISATEURS NON AUTORISÉS : 403
# ==========================================================


@pytest.mark.parametrize(
    "actor_fixture, assignee_fixture",
    [
        pytest.param(
            "other_user",
            "technician_user",
            id="user-not-creator",
        ),
        pytest.param(
            "technician_user",
            "technician_user",
            id="technician-assigned-not-creator",
        ),
        pytest.param(
            "other_technician_user",
            "technician_user",
            id="technician-not-assigned",
        ),
    ],
)
def test_unauthorized_actor_cannot_close_incident(
    request: pytest.FixtureRequest,
    actor_fixture: str,
    assignee_fixture: str,
    db_session: Session,
    test_user: User,
) -> None:
    actor: User = request.getfixturevalue(actor_fixture)
    assignee: User = request.getfixturevalue(assignee_fixture)

    with (
        make_client() as creator_client,
        make_client() as actor_client,
    ):
        login(creator_client, test_user)
        login(actor_client, actor)

        incident_id = create_incident(creator_client)

        prepare_incident(
            db_session,
            incident_id,
            assigned_to_id=assignee.id,
        )

        audits_before = len(get_close_audits(db_session, actor.id))

        response = close_incident(
            actor_client,
            incident_id,
        )

        assert response.status_code == 403, response.text

        incident = get_incident_from_db(
            db_session,
            incident_id,
        )

        assert incident.status == IncidentStatus.RESOLVED
        assert incident.closed_at is None
        assert incident.resolution == ("Redémarrage et vérification du service.")
        assert incident.assigned_to_id == assignee.id

        assert (
            get_close_history(
                db_session,
                incident_id,
            )
            == []
        )

        assert len(get_close_audits(db_session, actor.id)) == audits_before


# ==========================================================
# 3. TRANSITIONS INTERDITES : 409
# ==========================================================


@pytest.mark.parametrize(
    "actor_fixture, incident_status",
    [
        pytest.param(
            "test_user",
            IncidentStatus.OPEN,
            id="creator-open",
        ),
        pytest.param(
            "test_user",
            IncidentStatus.IN_PROGRESS,
            id="creator-in-progress",
        ),
        pytest.param(
            "admin_user",
            IncidentStatus.OPEN,
            id="admin-open",
        ),
        pytest.param(
            "admin_user",
            IncidentStatus.IN_PROGRESS,
            id="admin-in-progress",
        ),
    ],
)
def test_cannot_close_incident_before_resolution(
    request: pytest.FixtureRequest,
    actor_fixture: str,
    incident_status: IncidentStatus,
    db_session: Session,
    test_user: User,
    technician_user: User,
) -> None:
    actor: User = request.getfixturevalue(actor_fixture)

    with (
        make_client() as creator_client,
        make_client() as actor_client,
    ):
        login(creator_client, test_user)
        login(actor_client, actor)

        incident_id = create_incident(creator_client)

        prepare_incident(
            db_session,
            incident_id,
            assigned_to_id=technician_user.id,
            incident_status=incident_status,
        )

        audits_before = len(get_close_audits(db_session, actor.id))

        response = close_incident(
            actor_client,
            incident_id,
        )

        assert response.status_code == 409, response.text

        incident = get_incident_from_db(
            db_session,
            incident_id,
        )

        assert incident.status == incident_status
        assert incident.resolution is None
        assert incident.resolved_at is None
        assert incident.closed_at is None
        assert incident.assigned_to_id == technician_user.id

        assert (
            get_close_history(
                db_session,
                incident_id,
            )
            == []
        )

        assert len(get_close_audits(db_session, actor.id)) == audits_before


# ==========================================================
# 4. INCIDENT DÉJÀ CLOSED : 409
# ==========================================================


def test_cannot_close_already_closed_incident(
    db_session: Session,
    test_user: User,
    technician_user: User,
) -> None:
    with make_client() as creator_client:
        login(creator_client, test_user)

        incident_id = create_incident(creator_client)

        prepare_incident(
            db_session,
            incident_id,
            assigned_to_id=technician_user.id,
            incident_status=IncidentStatus.CLOSED,
        )

        before_incident = get_incident_from_db(
            db_session,
            incident_id,
        )

        old_closed_at = before_incident.closed_at
        old_resolved_at = before_incident.resolved_at
        old_resolution = before_incident.resolution

        audits_before = len(get_close_audits(db_session, test_user.id))

        response = close_incident(
            creator_client,
            incident_id,
        )

        assert response.status_code == 409, response.text

        incident = get_incident_from_db(
            db_session,
            incident_id,
        )

        assert incident.status == IncidentStatus.CLOSED
        assert incident.closed_at == old_closed_at
        assert incident.resolved_at == old_resolved_at
        assert incident.resolution == old_resolution

        assert (
            get_close_history(
                db_session,
                incident_id,
            )
            == []
        )

        assert len(get_close_audits(db_session, test_user.id)) == audits_before


# ==========================================================
# 5. DOUBLE CLÔTURE : 409
# ==========================================================


def test_incident_cannot_be_closed_twice(
    db_session: Session,
    test_user: User,
    technician_user: User,
) -> None:
    with make_client() as creator_client:
        login(creator_client, test_user)

        incident_id = create_incident(creator_client)

        prepare_incident(
            db_session,
            incident_id,
            assigned_to_id=technician_user.id,
        )

        first_response = close_incident(
            creator_client,
            incident_id,
        )

        assert first_response.status_code == 200, first_response.text

        before_incident = get_incident_from_db(
            db_session,
            incident_id,
        )

        old_closed_at = before_incident.closed_at
        old_resolution = before_incident.resolution
        old_resolved_at = before_incident.resolved_at

        history_before = len(get_close_history(db_session, incident_id))

        audits_before = len(get_close_audits(db_session, test_user.id))

        second_response = close_incident(
            creator_client,
            incident_id,
        )

        assert second_response.status_code == 409, second_response.text

        incident = get_incident_from_db(
            db_session,
            incident_id,
        )

        assert incident.status == IncidentStatus.CLOSED
        assert incident.closed_at == old_closed_at
        assert incident.resolution == old_resolution
        assert incident.resolved_at == old_resolved_at

        # Pas de nouvelle entrée d'historique.
        assert len(get_close_history(db_session, incident_id)) == history_before

        # Pas de nouvel audit de clôture.
        assert len(get_close_audits(db_session, test_user.id)) == audits_before


# ==========================================================
# 6. INCIDENT INEXISTANT : 404
# ==========================================================


def test_close_incident_not_found(
    test_user: User,
) -> None:
    with make_client() as creator_client:
        login(creator_client, test_user)

        response = close_incident(
            creator_client,
            incident_id=999999999,
        )

        assert response.status_code == 404, response.text


# ==========================================================
# 7. NON AUTHENTIFIÉ : 401
# ==========================================================


def test_close_incident_requires_authentication() -> None:
    with make_client() as client:
        response = close_incident(
            client,
            incident_id=999999999,
        )

        assert response.status_code == 401, response.text
