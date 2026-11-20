
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.main import app
from app.models.incident import Incident
from app.models.user import User
from app.models.enums import (
    IncidentCategory,
    IncidentHistoryAction,
    IncidentPriority,
    IncidentStatus,
)
from app.repositories.incident_history_repository import (
    IncidentHistoryRepository,
)


# ==========================================================
# HELPERS
# ==========================================================


def make_client() -> TestClient:
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


def create_test_incident(
    db_session: Session,
    creator_id: int,
    *,
    assigned_to_id: int | None = None,
    status: IncidentStatus = IncidentStatus.OPEN,
) -> Incident:

    incident = Incident(
        title="Incident de test US-12",
        description="Incident créé pour tester son historique.",
        category=IncidentCategory.ANOMALY,
        priority=IncidentPriority.MEDIUM,
        status=IncidentStatus.OPEN,
        created_by_id=creator_id,
        assigned_to_id=assigned_to_id,
    )

    db_session.add(incident)
    db_session.flush()

    # Les dates sont définies après la création pour
    # respecter les contraintes PostgreSQL.
    if status in (
        IncidentStatus.RESOLVED,
        IncidentStatus.CLOSED,
    ):
        incident.resolution = "Le problème a été résolu."
        incident.resolved_at = (
            incident.created_at + timedelta(seconds=1)
        )

    if status == IncidentStatus.CLOSED:
        incident.closed_at = (
            incident.created_at + timedelta(seconds=2)
        )

    incident.status = status
    db_session.flush()

    return incident


def add_history_event(
    db_session: Session,
    incident_id: int,
    actor_id: int,
    action: IncidentHistoryAction,
    *,
    field_name: str | None = None,
    old_value: str | None = None,
    new_value: str | None = None,
) -> None:

    repository = IncidentHistoryRepository(db_session)

    repository.create(
        incident_id=incident_id,
        actor_id=actor_id,
        action=action,
        field_name=field_name,
        old_value=old_value,
        new_value=new_value,
    )


def get_history(
    client: TestClient,
    incident_id: int,
):
    return client.get(
        f"/incidents/{incident_id}/history"
    )


def count_audits(
    db_session: Session,
    actor_id: int,
) -> int:

    return db_session.execute(
        text("""
            SELECT COUNT(*)
            FROM audit_logs
            WHERE user_id = :actor_id
        """),
        {"actor_id": actor_id},
    ).scalar_one()


# ==========================================================
# 1. UTILISATEURS AUTORISES : 200
# ==========================================================


@pytest.mark.parametrize(
    "creator_fixture, actor_fixture, assignee_fixture",
    [
        pytest.param(
            "test_user",
            "test_user",
            None,
            id="user-creator",
        ),
        pytest.param(
            "technician_user",
            "technician_user",
            "other_technician_user",
            id="technician-creator",
        ),
        pytest.param(
            "test_user",
            "technician_user",
            "technician_user",
            id="technician-assigned",
        ),
        pytest.param(
            "test_user",
            "admin_user",
            "technician_user",
            id="admin-not-creator",
        ),
    ],
)
def test_authorized_actor_can_get_incident_history(
    request: pytest.FixtureRequest,
    db_session: Session,
    creator_fixture: str,
    actor_fixture: str,
    assignee_fixture: str | None,
) -> None:

    creator: User = request.getfixturevalue(
        creator_fixture
    )
    actor: User = request.getfixturevalue(
        actor_fixture
    )

    assignee = (
        request.getfixturevalue(assignee_fixture)
        if assignee_fixture is not None
        else None
    )

    incident = create_test_incident(
        db_session,
        creator.id,
        assigned_to_id=(
            assignee.id if assignee is not None else None
        ),
    )

    add_history_event(
        db_session,
        incident.id,
        creator.id,
        IncidentHistoryAction.INCIDENT_CREATED,
    )

    add_history_event(
        db_session,
        incident.id,
        creator.id,
        IncidentHistoryAction.PRIORITY_CHANGED,
        field_name="priority",
        old_value="LOW",
        new_value="MEDIUM",
    )

    with make_client() as client:
        login(client, actor)

        response = get_history(
            client,
            incident.id,
        )

        assert response.status_code == 200, response.text

        body = response.json()

        assert isinstance(body, list)
        assert len(body) == 2

        assert all(
            event["incident_id"] == incident.id
            for event in body
        )

        assert body[0]["action"] == "INCIDENT_CREATED"
        assert body[1]["action"] == "PRIORITY_CHANGED"

        # Vérification du schéma de réponse.
        for event in body:
            assert isinstance(event["id"], int)
            assert isinstance(event["actor_id"], int)
            assert event["created_at"] is not None

            assert "field_name" in event
            assert "old_value" in event
            assert "new_value" in event

        # Vérification des valeurs historiques.
        assert body[1]["field_name"] == "priority"
        assert body[1]["old_value"] == "LOW"
        assert body[1]["new_value"] == "MEDIUM"


# ==========================================================
# 2. UTILISATEURS NON AUTORISES : 403
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
            None,
            id="technician-not-assigned",
        ),
        pytest.param(
            "technician_user",
            "other_technician_user",
            id="technician-assigned-to-someone-else",
        ),
    ],
)
def test_unauthorized_actor_cannot_get_history(
    request: pytest.FixtureRequest,
    db_session: Session,
    test_user: User,
    actor_fixture: str,
    assignee_fixture: str | None,
) -> None:

    actor: User = request.getfixturevalue(
        actor_fixture
    )

    assignee = (
        request.getfixturevalue(assignee_fixture)
        if assignee_fixture is not None
        else None
    )

    incident = create_test_incident(
        db_session,
        test_user.id,
        assigned_to_id=(
            assignee.id if assignee is not None else None
        ),
    )

    add_history_event(
        db_session,
        incident.id,
        test_user.id,
        IncidentHistoryAction.INCIDENT_CREATED,
    )

    with make_client() as client:
        login(client, actor)

        response = get_history(
            client,
            incident.id,
        )

        assert response.status_code == 403, response.text

        # L'historique existe mais reste inaccessible.
        db_session.expire_all()

        repository = IncidentHistoryRepository(db_session)
        history = repository.list_by_incident(
            incident_id=incident.id
        )

        assert len(history) == 1


# ==========================================================
# 3. UTILISATEUR NON AUTHENTIFIE : 401
# ==========================================================


def test_history_requires_authentication(
    db_session: Session,
    test_user: User,
) -> None:

    incident = create_test_incident(
        db_session,
        test_user.id,
    )

    with make_client() as client:
        response = get_history(
            client,
            incident.id,
        )

        assert response.status_code == 401, response.text


# ==========================================================
# 4. INCIDENT INEXISTANT : 404
# ==========================================================


def test_history_incident_not_found(
    admin_user: User,
) -> None:

    with make_client() as client:
        login(client, admin_user)

        response = get_history(
            client,
            999_999_999,
        )

        assert response.status_code == 404, response.text


# ==========================================================
# 5. HISTORIQUE VIDE : 200 []
# ==========================================================


def test_history_returns_empty_list(
    db_session: Session,
    test_user: User,
) -> None:

    incident = create_test_incident(
        db_session,
        test_user.id,
    )

    # Création directe en base :
    # aucun événement métier n'a été enregistré.
    with make_client() as client:
        login(client, test_user)

        response = get_history(
            client,
            incident.id,
        )

        assert response.status_code == 200, response.text
        assert response.json() == []


# ==========================================================
# 6. ISOLATION ENTRE INCIDENTS
# ==========================================================


def test_history_does_not_include_other_incidents(
    db_session: Session,
    test_user: User,
) -> None:

    incident_1 = create_test_incident(
        db_session,
        test_user.id,
    )

    incident_2 = create_test_incident(
        db_session,
        test_user.id,
    )

    add_history_event(
        db_session,
        incident_1.id,
        test_user.id,
        IncidentHistoryAction.INCIDENT_CREATED,
    )

    add_history_event(
        db_session,
        incident_1.id,
        test_user.id,
        IncidentHistoryAction.PRIORITY_CHANGED,
    )

    add_history_event(
        db_session,
        incident_2.id,
        test_user.id,
        IncidentHistoryAction.INCIDENT_CREATED,
    )

    with make_client() as client:
        login(client, test_user)

        response_1 = get_history(
            client,
            incident_1.id,
        )

        response_2 = get_history(
            client,
            incident_2.id,
        )

        assert response_1.status_code == 200
        assert response_2.status_code == 200

        body_1 = response_1.json()
        body_2 = response_2.json()

        assert len(body_1) == 2
        assert len(body_2) == 1

        assert all(
            event["incident_id"] == incident_1.id
            for event in body_1
        )

        assert all(
            event["incident_id"] == incident_2.id
            for event in body_2
        )


# ==========================================================
# 7. TRI CHRONOLOGIQUE : DATE PUIS ID
# ==========================================================


def test_history_is_chronologically_sorted(
    db_session: Session,
    test_user: User,
) -> None:

    incident = create_test_incident(
        db_session,
        test_user.id,
    )

    repository = IncidentHistoryRepository(db_session)

    for action in (
        IncidentHistoryAction.INCIDENT_CREATED,
        IncidentHistoryAction.ASSIGNED,
        IncidentHistoryAction.PRIORITY_CHANGED,
    ):
        add_history_event(
            db_session,
            incident.id,
            test_user.id,
            action,
        )

    events = repository.list_by_incident(
        incident_id=incident.id
    )

    assert len(events) == 3

    first, second, third = sorted(
        events,
        key=lambda event: event.id,
    )

    # Dates volontairement différentes de l'ordre d'insertion.
    base_time = incident.created_at + timedelta(seconds=1)

    first.created_at = base_time + timedelta(minutes=2)
    second.created_at = base_time
    third.created_at = base_time

    db_session.flush()

    expected_ids = [
        second.id,
        third.id,
        first.id,
    ]

    db_session.expire_all()

    with make_client() as client:
        login(client, test_user)

        response = get_history(
            client,
            incident.id,
        )

        assert response.status_code == 200, response.text

        body = response.json()

        assert [event["id"] for event in body] == expected_ids

        # Les deux événements de même date
        # sont triés par identifiant croissant.
        assert body[0]["created_at"] == body[1]["created_at"]


# ==========================================================
# 8. HISTORIQUE DISPONIBLE QUEL QUE SOIT LE STATUT
# ==========================================================


@pytest.mark.parametrize(
    "incident_status",
    [
        pytest.param(
            IncidentStatus.OPEN,
            id="open",
        ),
        pytest.param(
            IncidentStatus.IN_PROGRESS,
            id="in-progress",
        ),
        pytest.param(
            IncidentStatus.RESOLVED,
            id="resolved",
        ),
        pytest.param(
            IncidentStatus.CLOSED,
            id="closed",
        ),
    ],
)
def test_creator_can_read_history_for_any_status(
    db_session: Session,
    test_user: User,
    technician_user: User,
    incident_status: IncidentStatus,
) -> None:

    incident = create_test_incident(
        db_session,
        test_user.id,
        assigned_to_id=technician_user.id,
        status=incident_status,
    )

    add_history_event(
        db_session,
        incident.id,
        test_user.id,
        IncidentHistoryAction.INCIDENT_CREATED,
    )

    with make_client() as client:
        login(client, test_user)

        response = get_history(
            client,
            incident.id,
        )

        assert response.status_code == 200, response.text
        assert len(response.json()) == 1


# ==========================================================
# 9. CONSULTATION SANS ECRITURE EN BASE
# ==========================================================


def test_history_read_does_not_create_events_or_audits(
    db_session: Session,
    test_user: User,
) -> None:

    incident = create_test_incident(
        db_session,
        test_user.id,
    )

    add_history_event(
        db_session,
        incident.id,
        test_user.id,
        IncidentHistoryAction.INCIDENT_CREATED,
    )

    repository = IncidentHistoryRepository(db_session)

    with make_client() as client:
        login(client, test_user)

        history_before = repository.list_by_incident(
            incident_id=incident.id
        )
        audit_before = count_audits(
            db_session,
            test_user.id,
        )

        response = get_history(
            client,
            incident.id,
        )

        assert response.status_code == 200, response.text

        db_session.expire_all()

        history_after = repository.list_by_incident(
            incident_id=incident.id
        )
        audit_after = count_audits(
            db_session,
            test_user.id,
        )

        assert len(history_after) == len(history_before)
        assert audit_after == audit_before


# ==========================================================
# 10. IDENTIFIANT INVALIDE : 422
# ==========================================================


def test_history_invalid_incident_id(
    test_user: User,
) -> None:

    with make_client() as client:
        login(client, test_user)

        response = client.get(
            "/incidents/not-an-integer/history"
        )

        assert response.status_code == 422, response.text


# ==========================================================
# 11. ERREUR SQLALCHEMY : 500
# ==========================================================


def test_history_database_error_returns_500(
    monkeypatch: pytest.MonkeyPatch,
    db_session: Session,
    test_user: User,
) -> None:

    incident = create_test_incident(
        db_session,
        test_user.id,
    )

    def failing_list_by_incident(
        self,
        incident_id: int,
    ):
        raise SQLAlchemyError("Erreur SQL simulée")

    monkeypatch.setattr(
        IncidentHistoryRepository,
        "list_by_incident",
        failing_list_by_incident,
    )

    with make_client() as client:
        login(client, test_user)

        response = get_history(
            client,
            incident.id,
        )

        assert response.status_code == 500, response.text
