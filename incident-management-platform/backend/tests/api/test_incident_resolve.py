
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
    """
    Utilise une adresse IP valide pour les tests API.

    PostgreSQL attend une adresse IP dans audit_logs.ip_address
    (colonne de type INET).

    Le TestClient par défaut utilise "testclient", qui n'est
    pas une adresse IP valide.
    """
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
            "title": "Incident de test US-10",
            "description": (
                "Incident créé pour vérifier "
                "la résolution par un responsable."
            ),
            "category": "ANOMALY",
            "priority": "MEDIUM",
        },
    )

    assert response.status_code == 201, response.text

    return response.json()["id"]


def resolve_incident(
    client: TestClient,
    incident_id: int,
    resolution: str,
):
    return client.patch(
        f"/incidents/{incident_id}/resolve",
        json={"resolution": resolution},
    )


def prepare_incident(
    db_session: Session,
    incident_id: int,
    *,
    assigned_to_id: int | None,
    incident_status: IncidentStatus = IncidentStatus.IN_PROGRESS,
) -> None:
    incident = db_session.get(Incident, incident_id)

    assert incident is not None

    incident.assigned_to_id = assigned_to_id
    incident.status = incident_status

    if incident_status in (
        IncidentStatus.RESOLVED,
        IncidentStatus.CLOSED,
    ):
        now = datetime.now(UTC)

        incident.resolution = "Incident déjà corrigé."
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


def get_resolution_history(
    db_session: Session,
    incident_id: int,
) -> list[IncidentHistory]:
    statement = (
        select(IncidentHistory)
        .where(
            IncidentHistory.incident_id == incident_id,
            IncidentHistory.action == IncidentHistoryAction.RESOLVED,
        )
        .order_by(IncidentHistory.id)
    )

    return list(db_session.scalars(statement).all())


def get_resolution_audits(
    db_session: Session,
    actor_id: int,
) -> list[AuditLog]:
    statement = select(AuditLog).where(
        AuditLog.user_id == actor_id,
        AuditLog.event_type == AuditEventType.INCIDENT_RESOLVED,
        AuditLog.result == AuditResult.SUCCESS,
    )

    return list(db_session.scalars(statement).all())


# ==========================================================
# 1. TECHNICIAN ET ADMIN RESPONSABLES : 200
# ==========================================================


@pytest.mark.parametrize(
    "actor_fixture",
    [
        pytest.param(
            "technician_user",
            id="technician-assigned",
        ),
        pytest.param(
            "admin_user",
            id="admin-self-assigned",
        ),
    ],
)
def test_assigned_actor_can_resolve_incident(
    request: pytest.FixtureRequest,
    actor_fixture: str,
    db_session: Session,
    test_user: User,
) -> None:
    actor: User = request.getfixturevalue(actor_fixture)

    with (
        make_client() as creator,
        make_client() as actor_client,
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
            get_resolution_audits(db_session, actor.id)
        )

        before = datetime.now(UTC)

        response = resolve_incident(
            actor_client,
            incident_id,
            "Correction du serveur effectuée.",
        )

        after = datetime.now(UTC)

        assert response.status_code == 200, response.text

        body = response.json()

        assert body["id"] == incident_id
        assert body["status"] == "RESOLVED"
        assert body["resolution"] == (
            "Correction du serveur effectuée."
        )
        assert body["resolved_at"] is not None
        assert body["closed_at"] is None
        assert body["priority"] == "MEDIUM"
        assert body["assigned_to_id"] == actor.id
        assert body["created_by_id"] == test_user.id

        # Vérification PostgreSQL
        incident = get_incident_from_db(
            db_session,
            incident_id,
        )

        assert incident.status == IncidentStatus.RESOLVED
        assert incident.resolution == (
            "Correction du serveur effectuée."
        )
        assert incident.resolved_at is not None
        assert incident.closed_at is None

        # Les autres propriétés doivent rester inchangées
        assert incident.priority == IncidentPriority.MEDIUM
        assert incident.assigned_to_id == actor.id
        assert incident.created_by_id == test_user.id

        # Date de résolution
        resolved_at = datetime.fromisoformat(
            body["resolved_at"].replace("Z", "+00:00")
        )

        assert resolved_at.tzinfo is not None
        assert before <= resolved_at <= after

        # Historique métier
        history = get_resolution_history(
            db_session,
            incident_id,
        )

        assert len(history) == 1
        assert history[0].actor_id == actor.id
        assert history[0].action == IncidentHistoryAction.RESOLVED
        assert history[0].field_name == "status"
        assert history[0].old_value == "IN_PROGRESS"
        assert history[0].new_value == "RESOLVED"

        # Audit applicatif
        audits_after = get_resolution_audits(
            db_session,
            actor.id,
        )

        assert len(audits_after) == audits_before + 1


# ==========================================================
# 2. DESCRIPTION NETTOYÉE : 200
# ==========================================================


def test_resolution_description_is_trimmed(
    db_session: Session,
    test_user: User,
    technician_user: User,
) -> None:
    with (
        make_client() as creator,
        make_client() as technician,
    ):
        login(creator, test_user)
        login(technician, technician_user)

        incident_id = create_incident(creator)

        prepare_incident(
            db_session,
            incident_id,
            assigned_to_id=technician_user.id,
        )

        response = resolve_incident(
            technician,
            incident_id,
            "   Le service a été redémarré.   ",
        )

        assert response.status_code == 200, response.text

        assert response.json()["resolution"] == (
            "Le service a été redémarré."
        )

        incident = get_incident_from_db(
            db_session,
            incident_id,
        )

        assert incident.status == IncidentStatus.RESOLVED
        assert incident.resolution == (
            "Le service a été redémarré."
        )


# ==========================================================
# 3. UTILISATEURS NON AUTORISÉS : 403
# ==========================================================


@pytest.mark.parametrize(
    "actor_fixture, assignee_fixture",
    [
        pytest.param(
            "test_user",
            "test_user",
            id="user-forbidden",
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
def test_unauthorized_actor_cannot_resolve_incident(
    request: pytest.FixtureRequest,
    actor_fixture: str,
    assignee_fixture: str,
    db_session: Session,
    test_user: User,
) -> None:
    actor: User = request.getfixturevalue(actor_fixture)
    assignee: User = request.getfixturevalue(assignee_fixture)

    with (
        make_client() as creator,
        make_client() as actor_client,
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
            get_resolution_audits(db_session, actor.id)
        )

        response = resolve_incident(
            actor_client,
            incident_id,
            "Correction effectuée.",
        )

        assert response.status_code == 403, response.text

        incident = get_incident_from_db(
            db_session,
            incident_id,
        )

        assert incident.status == IncidentStatus.IN_PROGRESS
        assert incident.resolution is None
        assert incident.resolved_at is None
        assert incident.closed_at is None
        assert incident.assigned_to_id == assignee.id

        assert get_resolution_history(
            db_session,
            incident_id,
        ) == []

        assert len(
            get_resolution_audits(db_session, actor.id)
        ) == audits_before


# ==========================================================
# 4. INCIDENT SANS RESPONSABLE : 409
# ==========================================================


def test_cannot_resolve_unassigned_incident(
    db_session: Session,
    test_user: User,
    technician_user: User,
) -> None:
    with (
        make_client() as creator,
        make_client() as technician,
    ):
        login(creator, test_user)
        login(technician, technician_user)

        incident_id = create_incident(creator)

        prepare_incident(
            db_session,
            incident_id,
            assigned_to_id=None,
            incident_status=IncidentStatus.OPEN,
        )

        response = resolve_incident(
            technician,
            incident_id,
            "Correction effectuée.",
        )

        assert response.status_code == 409, response.text

        incident = get_incident_from_db(
            db_session,
            incident_id,
        )

        assert incident.status == IncidentStatus.OPEN
        assert incident.assigned_to_id is None
        assert incident.resolution is None
        assert incident.resolved_at is None

        assert get_resolution_history(
            db_session,
            incident_id,
        ) == []

        assert get_resolution_audits(
            db_session,
            technician_user.id,
        ) == []


# ==========================================================
# 5. STATUTS INTERDITS : 409
# ==========================================================


@pytest.mark.parametrize(
    "incident_status",
    [
        pytest.param(
            IncidentStatus.OPEN,
            id="incident-open",
        ),
        pytest.param(
            IncidentStatus.RESOLVED,
            id="incident-already-resolved",
        ),
        pytest.param(
            IncidentStatus.CLOSED,
            id="incident-closed",
        ),
    ],
)
def test_cannot_resolve_incident_with_invalid_status(
    incident_status: IncidentStatus,
    db_session: Session,
    test_user: User,
    technician_user: User,
) -> None:
    with (
        make_client() as creator,
        make_client() as technician,
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

        incident_before = get_incident_from_db(
            db_session,
            incident_id,
        )

        old_resolution = incident_before.resolution
        old_resolved_at = incident_before.resolved_at
        old_closed_at = incident_before.closed_at

        audits_before = len(
            get_resolution_audits(
                db_session,
                technician_user.id,
            )
        )

        response = resolve_incident(
            technician,
            incident_id,
            "Nouvelle correction effectuée.",
        )

        assert response.status_code == 409, response.text

        incident = get_incident_from_db(
            db_session,
            incident_id,
        )

        assert incident.status == incident_status
        assert incident.resolution == old_resolution
        assert incident.resolved_at == old_resolved_at
        assert incident.closed_at == old_closed_at
        assert incident.assigned_to_id == technician_user.id

        assert get_resolution_history(
            db_session,
            incident_id,
        ) == []

        assert len(
            get_resolution_audits(
                db_session,
                technician_user.id,
            )
        ) == audits_before


# ==========================================================
# 6. DOUBLE RÉSOLUTION : 409
# ==========================================================


def test_incident_cannot_be_resolved_twice(
    db_session: Session,
    test_user: User,
    technician_user: User,
) -> None:
    with (
        make_client() as creator,
        make_client() as technician,
    ):
        login(creator, test_user)
        login(technician, technician_user)

        incident_id = create_incident(creator)

        prepare_incident(
            db_session,
            incident_id,
            assigned_to_id=technician_user.id,
        )

        first_response = resolve_incident(
            technician,
            incident_id,
            "Première résolution.",
        )

        assert first_response.status_code == 200, first_response.text

        incident_before = get_incident_from_db(
            db_session,
            incident_id,
        )

        resolved_at_before = incident_before.resolved_at

        history_before = len(
            get_resolution_history(
                db_session,
                incident_id,
            )
        )

        audits_before = len(
            get_resolution_audits(
                db_session,
                technician_user.id,
            )
        )

        second_response = resolve_incident(
            technician,
            incident_id,
            "Deuxième résolution.",
        )

        assert second_response.status_code == 409, second_response.text

        incident_after = get_incident_from_db(
            db_session,
            incident_id,
        )

        assert incident_after.status == IncidentStatus.RESOLVED
        assert incident_after.resolution == "Première résolution."
        assert incident_after.resolved_at == resolved_at_before

        assert len(
            get_resolution_history(
                db_session,
                incident_id,
            )
        ) == history_before

        assert len(
            get_resolution_audits(
                db_session,
                technician_user.id,
            )
        ) == audits_before


# ==========================================================
# 7. INCIDENT INEXISTANT : 404
# ==========================================================


def test_resolve_incident_not_found(
    technician_user: User,
) -> None:
    with make_client() as technician:
        login(technician, technician_user)

        response = resolve_incident(
            technician,
            incident_id=999999999,
            resolution="Correction effectuée.",
        )

        assert response.status_code == 404, response.text


# ==========================================================
# 8. PAYLOAD INVALIDE : 422
# ==========================================================


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param(
            {},
            id="missing-resolution",
        ),
        pytest.param(
            {"resolution": ""},
            id="empty-resolution",
        ),
        pytest.param(
            {"resolution": "     "},
            id="spaces-only",
        ),
        pytest.param(
            {"resolution": "\n\t  "},
            id="whitespace-only",
        ),
        pytest.param(
            {"resolution": None},
            id="null-resolution",
        ),
        pytest.param(
            {"resolution": 123},
            id="numeric-resolution",
        ),
        pytest.param(
            {
                "resolution": "Correction effectuée.",
                "unexpected_field": True,
            },
            id="extra-field",
        ),
    ],
)
def test_resolve_incident_invalid_payload(
    payload: dict,
    db_session: Session,
    test_user: User,
    technician_user: User,
) -> None:
    with (
        make_client() as creator,
        make_client() as technician,
    ):
        login(creator, test_user)
        login(technician, technician_user)

        incident_id = create_incident(creator)

        prepare_incident(
            db_session,
            incident_id,
            assigned_to_id=technician_user.id,
        )

        audits_before = len(
            get_resolution_audits(
                db_session,
                technician_user.id,
            )
        )

        response = technician.patch(
            f"/incidents/{incident_id}/resolve",
            json=payload,
        )

        assert response.status_code == 422, response.text

        incident = get_incident_from_db(
            db_session,
            incident_id,
        )

        assert incident.status == IncidentStatus.IN_PROGRESS
        assert incident.resolution is None
        assert incident.resolved_at is None
        assert incident.closed_at is None
        assert incident.assigned_to_id == technician_user.id

        assert get_resolution_history(
            db_session,
            incident_id,
        ) == []

        assert len(
            get_resolution_audits(
                db_session,
                technician_user.id,
            )
        ) == audits_before


# ==========================================================
# 9. UTILISATEUR NON AUTHENTIFIÉ : 401
# ==========================================================


def test_resolve_incident_requires_authentication() -> None:
    with make_client() as client:
        response = client.patch(
            "/incidents/999999999/resolve",
            json={
                "resolution": "Correction effectuée.",
            },
        )

        assert response.status_code == 401, response.text
