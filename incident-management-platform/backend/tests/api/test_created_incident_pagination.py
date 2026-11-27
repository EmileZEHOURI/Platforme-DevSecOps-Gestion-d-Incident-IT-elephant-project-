from contextlib import ExitStack
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.enums import IncidentCategory, IncidentPriority, IncidentStatus
from app.models.incident import Incident


@pytest.fixture
def client_as():
    with ExitStack() as stack:
        def make_client(user):
            client = stack.enter_context(TestClient(app, client=("127.0.0.1", 50000)))
            response = client.post("/auth/login", json={"email": user.email, "password": "password"})
            assert response.status_code == 200
            return client
        yield make_client


@pytest.mark.parametrize("actor_fixture", ["test_user", "technician_user", "admin_user"])
def test_created_pagination_is_scoped_and_filtered(request, client_as, db_session, actor_fixture, other_technician_user):
    actor = request.getfixturevalue(actor_fixture)
    incidents = []
    created_at = datetime.now(UTC) - timedelta(days=1)
    for index in range(13):
        item = Incident(
            title=f"Pagination incident {index}", description="Description de test suffisamment longue.",
            category=IncidentCategory.ANOMALY,
            priority=IncidentPriority.HIGH if index % 2 else IncidentPriority.MEDIUM,
            status=IncidentStatus.CLOSED if index % 2 else IncidentStatus.OPEN,
            assigned_to_id=other_technician_user.id if index % 2 else None,
            created_at=created_at,
            resolved_at=created_at + timedelta(hours=1) if index % 2 else None,
            closed_at=created_at + timedelta(hours=2) if index % 2 else None,
            resolution="Incident corrigé" if index % 2 else None,
            created_by_id=actor.id if index < 12 else other_technician_user.id,
        )
        db_session.add(item)
        incidents.append(item)
    db_session.flush()
    client = client_as(actor)
    first = client.get("/incidents", params={"page": 1, "page_size": 10, "created_by_id": other_technician_user.id})
    assert first.status_code == 200
    data = first.json()
    assert data["total"] == 12
    assert len(data["items"]) == 10
    assert data["has_next"]
    assert all(i["created_by_id"] == actor.id for i in data["items"])
    second = client.get("/incidents?page=2&page_size=10").json()
    assert len(second["items"]) == 2
    ids = [i["id"] for i in data["items"] + second["items"]]
    assert ids == [i.id for i in reversed(incidents[:12])]
    filtered = client.get("/incidents?page=1&page_size=10&status=CLOSED&priority=HIGH&category=ANOMALY").json()
    assert filtered["total"] == 6
    assert all(i["status"] == "CLOSED" and i["priority"] == "HIGH" for i in filtered["items"])
    assert client.get("/incidents?page=99").json()["items"] == []
    legacy = client.get("/incidents").json()
    assert isinstance(legacy, list)
    assert len(legacy) == 12


@pytest.mark.parametrize("query", ["page=0", "page=-1", "page=1&page_size=0", "page=1&page_size=101", "page=1&status=INVALID"])
def test_created_pagination_rejects_invalid_parameters(client_as, test_user, query):
    assert client_as(test_user).get(f"/incidents?{query}").status_code == 422


def test_created_pagination_requires_authentication():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as client:
        assert client.get("/incidents?page=1").status_code == 401
