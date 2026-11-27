
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.enums import (
    IncidentCategory,
    IncidentPriority,
    IncidentStatus,
)
from app.models.incident import Incident
from app.models.user import User

# ============================================================
# FIXTURES
# ============================================================


@pytest.fixture
def api_client():
    # L'adresse IP est nécessaire pour les audits
    # stockés dans une colonne PostgreSQL INET.
    with TestClient(
        app,
        client=("127.0.0.1", 50000),
    ) as client:
        yield client


def login_as(client: TestClient, user: User):
    response = client.post(
        "/auth/login",
        json={
            "email": user.email,
            "password": "password",
        },
    )

    assert response.status_code == 200, response.text


@pytest.fixture
def pagination_incidents(
    db_session: Session,
    test_user: User,
    technician_user: User,
    other_technician_user: User,
):
    base_time = (
        datetime.now(UTC)
        - timedelta(days=2)
    )

    # A, B, C, D, E et H : technicien principal
    # F : autre technicien
    # G : incident non assigné

    definitions = [
        (
            "A",
            technician_user.id,
            IncidentStatus.OPEN,
            IncidentPriority.HIGH,
            IncidentCategory.SECURITY,
        ),
        (
            "B",
            technician_user.id,
            IncidentStatus.OPEN,
            IncidentPriority.HIGH,
            IncidentCategory.SECURITY,
        ),
        (
            "C",
            technician_user.id,
            IncidentStatus.OPEN,
            IncidentPriority.HIGH,
            IncidentCategory.SUPPORT,
        ),
        (
            "D",
            technician_user.id,
            IncidentStatus.OPEN,
            IncidentPriority.MEDIUM,
            IncidentCategory.SECURITY,
        ),
        (
            "E",
            technician_user.id,
            IncidentStatus.IN_PROGRESS,
            IncidentPriority.HIGH,
            IncidentCategory.SECURITY,
        ),
        (
            "F",
            other_technician_user.id,
            IncidentStatus.OPEN,
            IncidentPriority.HIGH,
            IncidentCategory.SECURITY,
        ),
        (
            "G",
            None,
            IncidentStatus.OPEN,
            IncidentPriority.HIGH,
            IncidentCategory.SECURITY,
        ),
        (
            "H",
            technician_user.id,
            IncidentStatus.OPEN,
            IncidentPriority.HIGH,
            IncidentCategory.SECURITY,
        ),
    ]

    ids = {}

    for index, (
        label,
        assignee_id,
        incident_status,
        priority,
        category,
    ) in enumerate(definitions):

        incident = Incident(
            title=f"US14 API incident {label}",
            description="Incident de test pour la pagination API.",
            created_by_id=test_user.id,
            assigned_to_id=assignee_id,
            status=incident_status,
            priority=priority,
            category=category,
            created_at=(
                base_time + timedelta(minutes=index)
            ),
        )

        db_session.add(incident)
        db_session.flush()

        ids[label] = incident.id

    return ids


def response_ids(data: dict) -> list[int]:
    return [
        incident["id"]
        for incident in data["items"]
    ]


API_SCOPES = [
    pytest.param(
        "/incidents/assigned",
        "technician_user",
        "HE DCBA".replace(" ", ""),
        id="assigned",
    ),
    pytest.param(
        "/incidents/all",
        "admin_user",
        "HGFEDCBA",
        id="all",
    ),
]


# ============================================================
# 1. STRUCTURE ET METADONNEES
# ============================================================


@pytest.mark.parametrize(
    "endpoint, user_fixture, expected_labels",
    API_SCOPES,
)
def test_api_returns_paginated_object(
    request,
    api_client,
    pagination_incidents,
    endpoint,
    user_fixture,
    expected_labels,
):
    user = request.getfixturevalue(user_fixture)
    login_as(api_client, user)

    response = api_client.get(
        endpoint,
        params={"page": 1, "page_size": 3},
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert isinstance(data, dict)

    assert set(data) == {
        "items",
        "total",
        "page",
        "page_size",
        "total_pages",
        "has_next",
        "has_previous",
    }

    assert isinstance(data["items"], list)
    assert data["total"] == len(expected_labels)
    assert data["page"] == 1
    assert data["page_size"] == 3
    assert data["total_pages"] == (
        len(expected_labels) + 2
    ) // 3

    assert data["has_next"] is True
    assert data["has_previous"] is False

    expected_ids = [
        pagination_incidents[label]
        for label in expected_labels[:3]
    ]

    assert response_ids(data) == expected_ids


# ============================================================
# 2. DEUXIEME PAGE
# ============================================================


@pytest.mark.parametrize(
    "endpoint, user_fixture, expected_labels",
    API_SCOPES,
)
def test_api_second_page(
    request,
    api_client,
    pagination_incidents,
    endpoint,
    user_fixture,
    expected_labels,
):
    user = request.getfixturevalue(user_fixture)
    login_as(api_client, user)

    response = api_client.get(
        endpoint,
        params={"page": 2, "page_size": 3},
    )

    assert response.status_code == 200, response.text

    data = response.json()

    expected_ids = [
        pagination_incidents[label]
        for label in expected_labels[3:6]
    ]

    assert response_ids(data) == expected_ids
    assert data["total"] == len(expected_labels)
    assert data["page"] == 2
    assert data["has_previous"] is True


# ============================================================
# 3. FILTRES COMBINES
# ============================================================


@pytest.mark.parametrize(
    "endpoint, user_fixture, expected_labels",
    [
        pytest.param(
            "/incidents/assigned",
            "technician_user",
            "HBA",
            id="assigned-filtered",
        ),
        pytest.param(
            "/incidents/all",
            "admin_user",
            "HGFBA",
            id="all-filtered",
        ),
    ],
)
def test_api_filters_affect_items_and_total(
    request,
    api_client,
    pagination_incidents,
    endpoint,
    user_fixture,
    expected_labels,
):
    user = request.getfixturevalue(user_fixture)
    login_as(api_client, user)

    filters = {
        "status": "OPEN",
        "priority": "HIGH",
        "category": "SECURITY",
        "page": 1,
        "page_size": 2,
    }

    response = api_client.get(
        endpoint,
        params=filters,
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["total"] == len(expected_labels)
    assert data["total_pages"] == (
        len(expected_labels) + 1
    ) // 2

    expected_first_page = [
        pagination_incidents[label]
        for label in expected_labels[:2]
    ]

    assert response_ids(data) == expected_first_page

    # Vérifie la page suivante avec les mêmes filtres.
    filters["page"] = 2

    response_page_2 = api_client.get(
        endpoint,
        params=filters,
    )

    assert response_page_2.status_code == 200
    data_page_2 = response_page_2.json()

    expected_second_page = [
        pagination_incidents[label]
        for label in expected_labels[2:4]
    ]

    assert response_ids(data_page_2) == expected_second_page
    assert data_page_2["total"] == len(expected_labels)


# ============================================================
# 4. DERNIERE PAGE PARTIELLE
# ============================================================


@pytest.mark.parametrize(
    "endpoint, user_fixture, expected_labels",
    API_SCOPES,
)
def test_api_last_partial_page(
    request,
    api_client,
    pagination_incidents,
    endpoint,
    user_fixture,
    expected_labels,
):
    user = request.getfixturevalue(user_fixture)
    login_as(api_client, user)

    response = api_client.get(
        endpoint,
        params={"page": 2, "page_size": 5},
    )

    assert response.status_code == 200, response.text

    data = response.json()

    expected_ids = [
        pagination_incidents[label]
        for label in expected_labels[5:]
    ]

    assert response_ids(data) == expected_ids
    assert data["total"] == len(expected_labels)
    assert data["total_pages"] == 2
    assert data["has_next"] is False
    assert data["has_previous"] is True


# ============================================================
# 5. PAGE INEXISTANTE
# ============================================================


@pytest.mark.parametrize(
    "endpoint, user_fixture, expected_labels",
    API_SCOPES,
)
def test_api_out_of_range_page(
    request,
    api_client,
    pagination_incidents,
    endpoint,
    user_fixture,
    expected_labels,
):
    user = request.getfixturevalue(user_fixture)
    login_as(api_client, user)

    response = api_client.get(
        endpoint,
        params={"page": 99, "page_size": 3},
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["items"] == []
    assert data["total"] == len(expected_labels)
    assert data["page"] == 99
    assert data["has_next"] is False
    assert data["has_previous"] is True


# ============================================================
# 6. AUCUN INCIDENT CORRESPONDANT AUX FILTRES
# ============================================================


@pytest.mark.parametrize(
    "endpoint, user_fixture, expected_labels",
    API_SCOPES,
)
def test_api_no_matching_incidents(
    request,
    api_client,
    pagination_incidents,
    endpoint,
    user_fixture,
    expected_labels,
):
    user = request.getfixturevalue(user_fixture)
    login_as(api_client, user)

    response = api_client.get(
        endpoint,
        params={
            "status": "CLOSED",
            "page": 1,
            "page_size": 20,
        },
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["items"] == []
    assert data["total"] == 0
    assert data["total_pages"] == 0
    assert data["has_next"] is False
    assert data["has_previous"] is False


# ============================================================
# 7. PARAMETRES DE PAGINATION INVALIDES
# ============================================================


@pytest.mark.parametrize(
    "endpoint, user_fixture, expected_labels",
    API_SCOPES,
)
@pytest.mark.parametrize(
    "params",
    [
        pytest.param({"page": 0}, id="page-zero"),
        pytest.param({"page": -1}, id="negative-page"),
        pytest.param({"page_size": 0}, id="size-zero"),
        pytest.param({"page_size": 101}, id="size-over-100"),
        pytest.param({"page": "abc"}, id="page-not-integer"),
        pytest.param({"page_size": "abc"}, id="size-not-integer"),
    ],
)
def test_api_rejects_invalid_pagination(
    request,
    api_client,
    pagination_incidents,
    endpoint,
    user_fixture,
    expected_labels,
    params,
):
    user = request.getfixturevalue(user_fixture)
    login_as(api_client, user)

    response = api_client.get(
        endpoint,
        params=params,
    )

    assert response.status_code == 422, response.text


# ============================================================
# 8. FILTRES INVALIDES
# ============================================================


@pytest.mark.parametrize(
    "endpoint, user_fixture, expected_labels",
    API_SCOPES,
)
@pytest.mark.parametrize(
    "params",
    [
        pytest.param(
            {"status": "INVALID_STATUS"},
            id="invalid-status",
        ),
        pytest.param(
            {"priority": "INVALID_PRIORITY"},
            id="invalid-priority",
        ),
        pytest.param(
            {"category": "INVALID_CATEGORY"},
            id="invalid-category",
        ),
    ],
)
def test_api_rejects_invalid_filters(
    request,
    api_client,
    pagination_incidents,
    endpoint,
    user_fixture,
    expected_labels,
    params,
):
    user = request.getfixturevalue(user_fixture)
    login_as(api_client, user)

    response = api_client.get(
        endpoint,
        params=params,
    )

    assert response.status_code == 422, response.text


# ============================================================
# 9. AUTORISATIONS
# ============================================================


@pytest.mark.parametrize(
    "endpoint, user_fixture",
    [
        pytest.param(
            "/incidents/assigned",
            "test_user",
            id="user-assigned-denied",
        ),
        pytest.param(
            "/incidents/all",
            "test_user",
            id="user-all-denied",
        ),
        pytest.param(
            "/incidents/all",
            "technician_user",
            id="technician-all-denied",
        ),
    ],
)
def test_api_forbidden_roles(
    request,
    api_client,
    pagination_incidents,
    endpoint,
    user_fixture,
):
    user = request.getfixturevalue(user_fixture)
    login_as(api_client, user)

    response = api_client.get(endpoint)

    assert response.status_code == 403, response.text


# ============================================================
# 10. UTILISATEUR NON AUTHENTIFIE
# ============================================================


@pytest.mark.parametrize(
    "endpoint",
    [
        "/incidents/assigned",
        "/incidents/all",
    ],
)
def test_api_requires_authentication(
    api_client,
    endpoint,
):
    response = api_client.get(endpoint)

    assert response.status_code == 401, response.text


# ============================================================
# 11. L'ADMINISTRATEUR NE VOIT PAS AUTOMATIQUEMENT
# TOUS LES INCIDENTS VIA /assigned
# ============================================================


def test_admin_assigned_endpoint_uses_own_assignment(
    api_client,
    pagination_incidents,
    admin_user: User,
):
    login_as(api_client, admin_user)

    assigned_response = api_client.get(
        "/incidents/assigned",
    )

    all_response = api_client.get(
        "/incidents/all",
    )

    assert assigned_response.status_code == 200
    assert all_response.status_code == 200

    assigned_data = assigned_response.json()
    all_data = all_response.json()

    # Aucun des huit incidents n'est assigné à l'admin.
    assert assigned_data["total"] == 0
    assert assigned_data["items"] == []

    # L'admin voit les huit incidents via /all.
    assert all_data["total"] == 8


# ============================================================
# 12. ISOLATION ENTRE TECHNICIENS
# ============================================================


def test_assigned_endpoint_never_exposes_other_assignees(
    api_client,
    pagination_incidents,
    technician_user: User,
    other_technician_user: User,
):
    login_as(api_client, technician_user)

    response = api_client.get(
        "/incidents/assigned",
        params={
            "page": 1,
            "page_size": 20,
        },
    )

    assert response.status_code == 200, response.text

    data = response.json()

    allowed_ids = {
        pagination_incidents[label]
        for label in "ABCDEH"
    }

    returned_ids = set(response_ids(data))

    assert returned_ids == allowed_ids
    assert data["total"] == 6

    # F appartient à l'autre technicien.
    assert pagination_incidents["F"] not in returned_ids

    # G n'est assigné à aucun technicien.
    assert pagination_incidents["G"] not in returned_ids


# ============================================================
# 13. REPONSE PAR DEFAUT
# ============================================================


@pytest.mark.parametrize(
    "endpoint, user_fixture, expected_labels",
    API_SCOPES,
)
def test_api_default_pagination(
    request,
    api_client,
    pagination_incidents,
    endpoint,
    user_fixture,
    expected_labels,
):
    user = request.getfixturevalue(user_fixture)
    login_as(api_client, user)

    response = api_client.get(endpoint)

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["page"] == 1
    assert data["page_size"] == 20
    assert data["total"] == len(expected_labels)
    assert data["total_pages"] == 1
    assert data["has_next"] is False
    assert data["has_previous"] is False

    expected_ids = [
        pagination_incidents[label]
        for label in expected_labels
    ]

    assert response_ids(data) == expected_ids
