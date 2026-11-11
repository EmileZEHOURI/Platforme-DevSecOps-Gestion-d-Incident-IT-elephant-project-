from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.database import SessionLocal
from app.main import app
from app.models.enums import IncidentStatus, UserRole
from app.models.incident import Incident
from app.models.user import User

# ==========================================================
# HELPERS ET FIXTURES
# ==========================================================


@contextmanager
def temporary_user_fields(
    user_id: int,
    **changes: object,
) -> Iterator[None]:
    """Modifie temporairement un utilisateur en base."""

    with SessionLocal() as db:
        user = db.get(User, user_id)
        assert user is not None

        previous_values = {field: getattr(user, field) for field in changes}

        for field, value in changes.items():
            setattr(user, field, value)

        db.commit()

    try:
        yield
    finally:
        with SessionLocal() as db:
            user = db.get(User, user_id)

            if user is not None:
                for field, value in previous_values.items():
                    setattr(user, field, value)

                db.commit()


@pytest.fixture
def admin_user(technician_user: User) -> Iterator[User]:
    """Utilise temporairement technician_user comme ADMIN."""

    with temporary_user_fields(
        technician_user.id,
        role=UserRole.ADMIN,
    ):
        yield technician_user


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
            "title": "Incident de test US-07",
            "description": "Incident créé pour vérifier les assignations.",
            "category": "ANOMALY",
            "priority": "MEDIUM",
        },
    )

    assert response.status_code == 201, response.text
    return response.json()["id"]


def assign(
    client: TestClient,
    incident_id: int,
    assigned_to_id: int,
):
    return client.patch(
        f"/incidents/{incident_id}/assignment",
        json={"assigned_to_id": assigned_to_id},
    )


def get_assignee_in_db(incident_id: int) -> int | None:
    with SessionLocal() as db:
        incident = db.get(Incident, incident_id)
        assert incident is not None
        return incident.assigned_to_id


def get_assignment_history(incident_id: int) -> list[dict]:
    with SessionLocal() as db:
        rows = (
            db.execute(
                text("""
                SELECT action, actor_id, old_value, new_value
                FROM incident_history
                WHERE incident_id = :incident_id
                  AND action IN ('ASSIGNED', 'REASSIGNED')
                """),
                {"incident_id": incident_id},
            )
            .mappings()
            .all()
        )

        return [dict(row) for row in rows]


def count_assignment_audits(
    actor_id: int,
    event_type: str,
) -> int:
    with SessionLocal() as db:
        return db.execute(
            text("""
                SELECT COUNT(*)
                FROM audit_logs
                WHERE user_id = :actor_id
                  AND event_type = :event_type
                """),
            {
                "actor_id": actor_id,
                "event_type": event_type,
            },
        ).scalar_one()


def test_admin_assigns_incident_to_technician(
    other_technician_user: User,
    admin_user: User,
    test_user: User,
) -> None:
    with (
        TestClient(app) as creator,
        TestClient(app) as admin,
        TestClient(app) as technician,
    ):
        login(creator, test_user)
        login(admin, admin_user)
        login(technician, other_technician_user)

        incident_id = create_incident(creator)

        assert get_assignee_in_db(incident_id) is None

        audit_count_before = count_assignment_audits(
            admin_user.id,
            "INCIDENT_ASSIGNED",
        )

        response = assign(
            admin,
            incident_id,
            other_technician_user.id,
        )

        assert response.status_code == 200, response.text

        body = response.json()

        assert body["id"] == incident_id
        assert body["assigned_to_id"] == other_technician_user.id
        assert body["status"] == "OPEN"

        # Vérifier la persistance réelle
        assert get_assignee_in_db(incident_id) == other_technician_user.id

        # Vérifier l'historique
        history = get_assignment_history(incident_id)

        assert len(history) == 1
        assert history[0]["action"] == "ASSIGNED"
        assert history[0]["actor_id"] == admin_user.id
        assert history[0]["old_value"] is None
        assert history[0]["new_value"] == str(other_technician_user.id)

        # Vérifier l'audit
        audit_count_after = count_assignment_audits(
            admin_user.id,
            "INCIDENT_ASSIGNED",
        )
        assert audit_count_after == audit_count_before + 1

        # Le technicien retrouve l'incident dans sa file US-06
        assigned_response = technician.get("/incidents/assigned")

        assert assigned_response.status_code == 200

        returned_ids = [incident["id"] for incident in assigned_response.json()]

        assert incident_id in returned_ids


def test_admin_reassigns_incident(
    other_technician_user: User,
    admin_user: User,
    test_user: User,
) -> None:
    with (
        TestClient(app) as creator,
        TestClient(app) as admin,
    ):
        login(creator, test_user)
        login(admin, admin_user)

        incident_id = create_incident(creator)

        # Première assignation : ADMIN vers lui-même
        first_response = assign(
            admin,
            incident_id,
            admin_user.id,
        )
        assert first_response.status_code == 200

        # Réassignation : ADMIN vers TECHNICIAN
        response = assign(
            admin,
            incident_id,
            other_technician_user.id,
        )

        assert response.status_code == 200, response.text
        assert response.json()["assigned_to_id"] == other_technician_user.id

        assert get_assignee_in_db(incident_id) == other_technician_user.id

        history = get_assignment_history(incident_id)

        assert len(history) == 2

        actions = {entry["action"]: entry for entry in history}

        assert "ASSIGNED" in actions
        assert "REASSIGNED" in actions

        assert actions["REASSIGNED"]["actor_id"] == admin_user.id
        assert actions["REASSIGNED"]["old_value"] == str(admin_user.id)
        assert actions["REASSIGNED"]["new_value"] == str(other_technician_user.id)


def test_assigning_same_technician_is_idempotent(
    other_technician_user: User,
    admin_user: User,
    test_user: User,
) -> None:
    with (
        TestClient(app) as creator,
        TestClient(app) as admin,
    ):
        login(creator, test_user)
        login(admin, admin_user)

        incident_id = create_incident(creator)

        first_response = assign(
            admin,
            incident_id,
            other_technician_user.id,
        )
        assert first_response.status_code == 200

        history_before = get_assignment_history(incident_id)

        audit_before = count_assignment_audits(
            admin_user.id,
            "INCIDENT_ASSIGNED",
        )

        second_response = assign(
            admin,
            incident_id,
            other_technician_user.id,
        )

        assert second_response.status_code == 200
        assert second_response.json()["assigned_to_id"] == (other_technician_user.id)

        history_after = get_assignment_history(incident_id)

        audit_after = count_assignment_audits(
            admin_user.id,
            "INCIDENT_ASSIGNED",
        )

        assert len(history_before) == 1
        assert len(history_after) == 1
        assert audit_after == audit_before


def test_admin_can_assign_incident_to_self(
    admin_user: User,
    test_user: User,
) -> None:
    with (
        TestClient(app) as creator,
        TestClient(app) as admin,
    ):
        login(creator, test_user)
        login(admin, admin_user)

        incident_id = create_incident(creator)

        response = assign(
            admin,
            incident_id,
            admin_user.id,
        )

        assert response.status_code == 200, response.text
        assert response.json()["assigned_to_id"] == admin_user.id
        assert response.json()["status"] == "OPEN"

        assert get_assignee_in_db(incident_id) == admin_user.id


@pytest.mark.parametrize(
    "actor_type",
    ["USER", "TECHNICIAN"],
    ids=["user-forbidden", "technician-forbidden"],
)
def test_non_admin_cannot_assign(
    actor_type: str,
    other_technician_user: User,
    test_user: User,
) -> None:
    with (
        TestClient(app) as creator,
        TestClient(app) as actor_client,
    ):
        login(creator, test_user)

        incident_id = create_incident(creator)

        actor = test_user if actor_type == "USER" else other_technician_user

        login(actor_client, actor)

        response = assign(
            actor_client,
            incident_id,
            other_technician_user.id,
        )

        assert response.status_code == 403
        assert get_assignee_in_db(incident_id) is None
        assert get_assignment_history(incident_id) == []


def test_admin_cannot_assign_to_another_admin(
    other_technician_user: User,
    admin_user: User,
    test_user: User,
) -> None:
    with temporary_user_fields(
        other_technician_user.id,
        role=UserRole.ADMIN,
    ):
        with (
            TestClient(app) as creator,
            TestClient(app) as admin,
        ):
            login(creator, test_user)
            login(admin, admin_user)

            incident_id = create_incident(creator)

            response = assign(
                admin,
                incident_id,
                other_technician_user.id,
            )

            assert response.status_code == 403
            assert get_assignee_in_db(incident_id) is None
            assert get_assignment_history(incident_id) == []


def test_admin_cannot_assign_to_user(
    admin_user: User,
    test_user: User,
) -> None:
    with (
        TestClient(app) as creator,
        TestClient(app) as admin,
    ):
        login(creator, test_user)
        login(admin, admin_user)

        incident_id = create_incident(creator)

        response = assign(
            admin,
            incident_id,
            test_user.id,
        )

        # Contrat HTTP actuel de ta route
        assert response.status_code == 403

        assert get_assignee_in_db(incident_id) is None
        assert get_assignment_history(incident_id) == []


def test_admin_cannot_assign_to_inactive_technician(
    other_technician_user: User,
    admin_user: User,
    test_user: User,
) -> None:
    with (
        TestClient(app) as creator,
        TestClient(app) as admin,
    ):
        login(creator, test_user)
        login(admin, admin_user)

        incident_id = create_incident(creator)

        with temporary_user_fields(
            other_technician_user.id,
            is_active=False,
        ):
            response = assign(
                admin,
                incident_id,
                other_technician_user.id,
            )

            assert response.status_code == 409

        assert get_assignee_in_db(incident_id) is None
        assert get_assignment_history(incident_id) == []


def test_admin_cannot_assign_closed_incident(
    other_technician_user: User,
    admin_user: User,
    test_user: User,
) -> None:
    with (
        TestClient(app) as creator,
        TestClient(app) as admin,
    ):
        login(creator, test_user)
        login(admin, admin_user)

        incident_id = create_incident(creator)

        # US-11 pas encore implémentée :
        # on prépare donc un incident CLOSED en base.
        with SessionLocal() as db:
            incident = db.get(Incident, incident_id)
            assert incident is not None

            now = datetime.now(timezone.utc)

            incident.assigned_to_id = other_technician_user.id
            incident.status = IncidentStatus.CLOSED
            incident.resolution = "Le problème a été résolu."
            incident.resolved_at = now
            incident.closed_at = now

            db.commit()

        response = assign(
            admin,
            incident_id,
            admin_user.id,
        )

        assert response.status_code == 409

        # L'assignation existante ne doit pas changer
        assert get_assignee_in_db(incident_id) == other_technician_user.id
        assert get_assignment_history(incident_id) == []


def test_assignment_to_nonexistent_incident(
    other_technician_user: User,
    admin_user: User,
) -> None:
    with TestClient(app) as admin:
        login(admin, admin_user)

        response = assign(
            admin,
            999_999_999,
            other_technician_user.id,
        )

        assert response.status_code == 404


def test_assignment_to_nonexistent_user(
    admin_user: User,
    test_user: User,
) -> None:
    with (
        TestClient(app) as creator,
        TestClient(app) as admin,
    ):
        login(creator, test_user)
        login(admin, admin_user)

        incident_id = create_incident(creator)

        response = assign(
            admin,
            incident_id,
            999_999_999,
        )

        assert response.status_code == 404
        assert get_assignee_in_db(incident_id) is None
        assert get_assignment_history(incident_id) == []


def test_assignment_requires_authentication() -> None:
    with TestClient(app) as client:
        response = client.patch(
            "/incidents/999999999/assignment",
            json={"assigned_to_id": 12},
        )

        assert response.status_code == 401


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"assigned_to_id": "not-an-integer"},
        {"assigned_to_id": 12, "unexpected_field": True},
    ],
    ids=[
        "missing-assignee",
        "invalid-assignee-type",
        "forbidden-extra-field",
    ],
)
def test_assignment_invalid_payload_returns_422(
    payload: dict,
    admin_user: User,
) -> None:
    with TestClient(app) as admin:
        login(admin, admin_user)

        response = admin.patch(
            "/incidents/999999999/assignment",
            json=payload,
        )

        assert response.status_code == 422
