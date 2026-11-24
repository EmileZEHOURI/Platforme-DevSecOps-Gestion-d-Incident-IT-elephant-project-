from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.main import app
from app.models.incident import Incident
from app.models.user import User
from app.models.enums import (
    IncidentStatus,
    IncidentPriority,
    IncidentCategory,
)
from app.repositories.incident_repository import IncidentRepository
from app.repositories.incident_history_repository import (
    IncidentHistoryRepository,
)
from app.services.incident_service import (
    IncidentService,
    UserNotFoundError,
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
    title: str,
    assigned_to_id: int | None = None,
    status: IncidentStatus = IncidentStatus.OPEN,
    priority: IncidentPriority = IncidentPriority.MEDIUM,
    category: IncidentCategory = IncidentCategory.SUPPORT,
    created_at: datetime | None = None,
) -> Incident:

    incident = Incident(
        title=title,
        description="Incident créé pour les tests API de filtrage et pagination.",
        category=category,
        priority=priority,
        status=IncidentStatus.OPEN,
        created_by_id=creator_id,
        assigned_to_id=assigned_to_id,
    )

    if created_at is not None:
        incident.created_at = created_at

    # Les incidents sont initialement créés avec OPEN
    # pour respecter les contraintes PostgreSQL.
    db_session.add(incident)
    db_session.flush()

    if status != IncidentStatus.OPEN:
        assert assigned_to_id is not None

    if status in (
        IncidentStatus.RESOLVED,
        IncidentStatus.CLOSED,
    ):
        incident.resolution = "Le problème a été résolu."

        incident.resolved_at = incident.created_at + timedelta(seconds=1)

    if status == IncidentStatus.CLOSED:
        incident.closed_at = incident.created_at + timedelta(seconds=2)

    incident.status = status

    db_session.flush()

    return incident


def get_incidents(
    client: TestClient,
    endpoint: str,
    **filters,
):
    return client.get(
        f"/incidents/{endpoint}",
        params={key: value for key, value in filters.items() if value is not None},
    )


def count_audits(db_session: Session) -> int:
    return db_session.execute(text("SELECT COUNT(*) FROM audit_logs")).scalar_one()


# ==========================================================
# FIXTURE : JEU DE DONNEES
# ==========================================================


@pytest.fixture
def filter_dataset(
    db_session: Session,
    test_user: User,
    technician_user: User,
    other_technician_user: User,
):

    base_time = datetime.now(timezone.utc) - timedelta(minutes=30)

    definitions = [
        (
            "A",
            IncidentStatus.OPEN,
            IncidentPriority.HIGH,
            IncidentCategory.SECURITY,
            technician_user.id,
        ),
        (
            "B",
            IncidentStatus.OPEN,
            IncidentPriority.HIGH,
            IncidentCategory.SUPPORT,
            technician_user.id,
        ),
        (
            "C",
            IncidentStatus.OPEN,
            IncidentPriority.MEDIUM,
            IncidentCategory.SECURITY,
            technician_user.id,
        ),
        (
            "D",
            IncidentStatus.OPEN,
            IncidentPriority.MEDIUM,
            IncidentCategory.SUPPORT,
            technician_user.id,
        ),
        (
            "E",
            IncidentStatus.IN_PROGRESS,
            IncidentPriority.HIGH,
            IncidentCategory.SECURITY,
            technician_user.id,
        ),
        (
            "F",
            IncidentStatus.IN_PROGRESS,
            IncidentPriority.HIGH,
            IncidentCategory.SUPPORT,
            technician_user.id,
        ),
        (
            "G",
            IncidentStatus.IN_PROGRESS,
            IncidentPriority.MEDIUM,
            IncidentCategory.SECURITY,
            technician_user.id,
        ),
        (
            "H",
            IncidentStatus.IN_PROGRESS,
            IncidentPriority.MEDIUM,
            IncidentCategory.SUPPORT,
            technician_user.id,
        ),
        (
            "I",
            IncidentStatus.OPEN,
            IncidentPriority.HIGH,
            IncidentCategory.SECURITY,
            other_technician_user.id,
        ),
        (
            "J",
            IncidentStatus.OPEN,
            IncidentPriority.HIGH,
            IncidentCategory.SECURITY,
            None,
        ),
    ]

    dataset = {}

    for index, definition in enumerate(definitions):

        (
            label,
            incident_status,
            priority,
            category,
            assigned_to_id,
        ) = definition

        incident = create_test_incident(
            db_session,
            test_user.id,
            title=f"Incident US-13 {label}",
            assigned_to_id=assigned_to_id,
            status=incident_status,
            priority=priority,
            category=category,
            created_at=(base_time + timedelta(minutes=index)),
        )

        dataset[label] = incident.id

    return dataset


# ==========================================================
# COMBINAISONS DE FILTRES
# ==========================================================


FILTER_CASES = [
    pytest.param(
        {},
        "ABCDEFGH",
        id="no-filters",
    ),
    pytest.param(
        {"status": "OPEN"},
        "ABCD",
        id="status-only",
    ),
    pytest.param(
        {"priority": "HIGH"},
        "ABEF",
        id="priority-only",
    ),
    pytest.param(
        {"category": "SECURITY"},
        "ACEG",
        id="category-only",
    ),
    pytest.param(
        {
            "status": "OPEN",
            "priority": "HIGH",
        },
        "AB",
        id="status-and-priority",
    ),
    pytest.param(
        {
            "status": "OPEN",
            "category": "SECURITY",
        },
        "AC",
        id="status-and-category",
    ),
    pytest.param(
        {
            "priority": "HIGH",
            "category": "SECURITY",
        },
        "AE",
        id="priority-and-category",
    ),
    pytest.param(
        {
            "status": "OPEN",
            "priority": "HIGH",
            "category": "SECURITY",
        },
        "A",
        id="all-filters",
    ),
]


# ==========================================================
# 1. FILTRAGE DES INCIDENTS ASSIGNES
# Total : 8 tests
# ==========================================================


@pytest.mark.parametrize(
    "filters, expected_labels",
    FILTER_CASES,
)
def test_assigned_incidents_filter_combinations(
    technician_user: User,
    filter_dataset,
    filters,
    expected_labels,
):

    expected_ids = [filter_dataset[label] for label in reversed(expected_labels)]

    with make_client() as client:
        login(client, technician_user)

        response = get_incidents(
            client,
            "assigned",
            **filters,
        )

        assert response.status_code == 200, response.text

        body = response.json()

        assert isinstance(body, dict)
        assert isinstance(body["items"], list)
        assert body["total"] == len(expected_ids)
        assert body["page"] == 1
        assert body["page_size"] == 20

        # Vérifie les résultats, leur nombre et leur tri.
        assert [incident["id"] for incident in body["items"]] == expected_ids

        for incident in body["items"]:

            assert incident["assigned_to_id"] == technician_user.id

            for field_name, expected_value in filters.items():
                assert incident[field_name] == expected_value

        returned_ids = {incident["id"] for incident in body["items"]}

        # L'incident I appartient à un autre technicien.
        assert filter_dataset["I"] not in returned_ids

        # L'incident J n'est pas assigné.
        assert filter_dataset["J"] not in returned_ids


# ==========================================================
# 2. FILTRAGE GLOBAL DES INCIDENTS
# Total : 8 tests
# ==========================================================


@pytest.mark.parametrize(
    "filters, expected_labels",
    FILTER_CASES,
)
def test_all_incidents_filter_combinations(
    admin_user: User,
    filter_dataset,
    filters,
    expected_labels,
):

    # I et J satisfont tous les filtres de FILTER_CASES.
    expected_labels = expected_labels + "IJ"

    expected_ids = [filter_dataset[label] for label in reversed(expected_labels)]

    with make_client() as client:
        login(client, admin_user)

        response = get_incidents(
            client,
            "all",
            **filters,
        )

        assert response.status_code == 200, response.text

        body = response.json()

        assert isinstance(body, dict)
        assert isinstance(body["items"], list)
        assert body["total"] == len(expected_ids)
        assert body["page"] == 1
        assert body["page_size"] == 20

        assert [incident["id"] for incident in body["items"]] == expected_ids

        for incident in body["items"]:
            for field_name, expected_value in filters.items():
                assert incident[field_name] == expected_value

        returned_ids = {incident["id"] for incident in body["items"]}

        assert filter_dataset["I"] in returned_ids
        assert filter_dataset["J"] in returned_ids

        # L'administrateur voit aussi les incidents non assignés.
        assert any(incident["assigned_to_id"] is None for incident in body["items"])


# ==========================================================
# 3. AUCUN RESULTAT CORRESPONDANT
# Total : 2 tests
# ==========================================================


@pytest.mark.parametrize(
    "endpoint, actor_fixture",
    [
        ("assigned", "technician_user"),
        ("all", "admin_user"),
    ],
)
def test_filters_return_empty_list(
    request: pytest.FixtureRequest,
    endpoint,
    actor_fixture,
):

    actor = request.getfixturevalue(actor_fixture)

    with make_client() as client:
        login(client, actor)

        response = get_incidents(
            client,
            endpoint,
            status="CLOSED",
            priority="CRITICAL",
            category="DATA",
        )

        assert response.status_code == 200, response.text
        body = response.json()

        assert body["items"] == []
        assert body["total"] == 0
        assert body["total_pages"] == 0


# ==========================================================
# 4. ADMINISTRATEUR : INCIDENTS ASSIGNES
# Total : 1 test
# ==========================================================


def test_admin_can_access_assigned_endpoint(
    admin_user: User,
):

    # Aucun incident du dataset n'est assigné à l'admin.
    with make_client() as client:
        login(client, admin_user)

        response = get_incidents(
            client,
            "assigned",
            status="OPEN",
            priority="HIGH",
            category="SECURITY",
        )

        assert response.status_code == 200, response.text
        body = response.json()

        assert body["items"] == []
        assert body["total"] == 0
        assert body["total_pages"] == 0


# ==========================================================
# 5. UTILISATEURS NON AUTORISES
# Total : 3 tests
# ==========================================================


@pytest.mark.parametrize(
    "endpoint, actor_fixture",
    [
        pytest.param(
            "assigned",
            "test_user",
            id="user-assigned",
        ),
        pytest.param(
            "all",
            "test_user",
            id="user-all",
        ),
        pytest.param(
            "all",
            "technician_user",
            id="technician-all",
        ),
    ],
)
def test_unauthorized_user_cannot_filter_incidents(
    request: pytest.FixtureRequest,
    endpoint,
    actor_fixture,
):

    actor = request.getfixturevalue(actor_fixture)

    with make_client() as client:
        login(client, actor)

        response = get_incidents(
            client,
            endpoint,
            status="OPEN",
            priority="HIGH",
            category="SECURITY",
        )

        assert response.status_code == 403, response.text


# ==========================================================
# 6. UTILISATEURS NON AUTHENTIFIES
# Total : 2 tests
# ==========================================================


@pytest.mark.parametrize(
    "endpoint",
    ["assigned", "all"],
)
def test_filter_endpoints_require_authentication(endpoint):

    with make_client() as client:

        response = get_incidents(
            client,
            endpoint,
            status="OPEN",
        )

        assert response.status_code == 401, response.text


# ==========================================================
# 7. FILTRES INVALIDES : 422
# Total : 6 tests
# ==========================================================


@pytest.mark.parametrize(
    "endpoint, actor_fixture",
    [
        ("assigned", "technician_user"),
        ("all", "admin_user"),
    ],
)
@pytest.mark.parametrize(
    "field_name, invalid_value",
    [
        pytest.param(
            "status",
            "INVALID_STATUS",
            id="invalid-status",
        ),
        pytest.param(
            "priority",
            "INVALID_PRIORITY",
            id="invalid-priority",
        ),
        pytest.param(
            "category",
            "INVALID_CATEGORY",
            id="invalid-category",
        ),
    ],
)
def test_invalid_filter_returns_422(
    request: pytest.FixtureRequest,
    endpoint,
    actor_fixture,
    field_name,
    invalid_value,
):

    actor = request.getfixturevalue(actor_fixture)

    with make_client() as client:
        login(client, actor)

        response = get_incidents(
            client,
            endpoint,
            **{field_name: invalid_value},
        )

        assert response.status_code == 422, response.text

        body = response.json()

        assert "detail" in body

        # Vérifie que FastAPI signale bien
        # le Query Parameter invalide.
        assert any(error["loc"] == ["query", field_name] for error in body["detail"])


# ==========================================================
# 8. INCIDENTS RESOLUS ET CLOTURES
# Total : 4 tests
# ==========================================================


@pytest.mark.parametrize(
    "endpoint, actor_fixture",
    [
        ("assigned", "technician_user"),
        ("all", "admin_user"),
    ],
)
@pytest.mark.parametrize(
    "incident_status",
    [
        IncidentStatus.RESOLVED,
        IncidentStatus.CLOSED,
    ],
)
def test_filter_resolved_and_closed_incidents(
    request: pytest.FixtureRequest,
    db_session: Session,
    test_user: User,
    technician_user: User,
    endpoint,
    actor_fixture,
    incident_status,
):

    base_time = datetime.now(timezone.utc) - timedelta(minutes=10)

    resolved_incident = create_test_incident(
        db_session,
        test_user.id,
        title="Incident résolu US-13",
        assigned_to_id=technician_user.id,
        status=IncidentStatus.RESOLVED,
        priority=IncidentPriority.HIGH,
        category=IncidentCategory.SECURITY,
        created_at=base_time,
    )

    closed_incident = create_test_incident(
        db_session,
        test_user.id,
        title="Incident clôturé US-13",
        assigned_to_id=technician_user.id,
        status=IncidentStatus.CLOSED,
        priority=IncidentPriority.HIGH,
        category=IncidentCategory.SECURITY,
        created_at=base_time,
    )

    create_test_incident(
        db_session,
        test_user.id,
        title="Incident ouvert US-13",
        assigned_to_id=technician_user.id,
        status=IncidentStatus.OPEN,
        priority=IncidentPriority.HIGH,
        category=IncidentCategory.SECURITY,
        created_at=base_time,
    )

    expected_id = (
        resolved_incident.id
        if incident_status == IncidentStatus.RESOLVED
        else closed_incident.id
    )

    actor = request.getfixturevalue(actor_fixture)

    with make_client() as client:
        login(client, actor)

        response = get_incidents(
            client,
            endpoint,
            status=incident_status.value,
        )

        assert response.status_code == 200, response.text

        body = response.json()

        assert len(body["items"]) == 1
        assert body["total"] == 1
        assert body["items"][0]["id"] == expected_id

        assert body["items"][0]["status"] == incident_status.value


# ==========================================================
# 9. SECURITE : MANIPULATION DE L'ASSIGNATION
# Total : 1 test
# ==========================================================


def test_technician_cannot_override_assignee_id(
    technician_user: User,
    other_technician_user: User,
    filter_dataset,
):

    with make_client() as client:
        login(client, technician_user)

        response = client.get(
            "/incidents/assigned",
            params={
                "status": "OPEN",
                "priority": "HIGH",
                "category": "SECURITY",
                # Tentative de récupération des incidents
                # d'un autre technicien.
                "assignee_id": other_technician_user.id,
                "assigned_to_id": other_technician_user.id,
                "actor_id": other_technician_user.id,
            },
        )

        assert response.status_code == 200, response.text

        body = response.json()

        returned_ids = [incident["id"] for incident in body["items"]]

        assert returned_ids == [filter_dataset["A"]]

        assert filter_dataset["I"] not in returned_ids
        assert filter_dataset["J"] not in returned_ids

        assert all(
            incident["assigned_to_id"] == technician_user.id for incident in body["items"]
        )


# ==========================================================
# 10. UTILISATEUR INTROUVABLE PAR LE SERVICE : 404
# Total : 2 tests
# ==========================================================


@pytest.mark.parametrize(
    "endpoint, actor_fixture, service_method",
    [
        (
            "assigned",
            "technician_user",
            "paginate_assigned_incidents",
        ),
        (
            "all",
            "admin_user",
            "paginate_all_incidents",
        ),
    ],
)
def test_user_not_found_returns_404(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
    endpoint,
    actor_fixture,
    service_method,
):

    actor = request.getfixturevalue(actor_fixture)

    def missing_user(*args, **kwargs):
        raise UserNotFoundError("Utilisateur inexistant")

    with make_client() as client:
        login(client, actor)

        # On simule uniquement l'erreur métier du service,
        # sans modifier le fonctionnement de l'authentification.
        monkeypatch.setattr(
            IncidentService,
            service_method,
            missing_user,
        )

        response = get_incidents(
            client,
            endpoint,
            status="OPEN",
        )

        assert response.status_code == 404, response.text


# ==========================================================
# 11. ERREURS SQLALCHEMY : 500
# Total : 2 tests
# ==========================================================


@pytest.mark.parametrize(
    "endpoint, actor_fixture, repository_method",
    [
        (
            "assigned",
            "technician_user",
            "list_by_assignee",
        ),
        (
            "all",
            "admin_user",
            "list_all",
        ),
    ],
)
def test_database_error_returns_500(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
    endpoint,
    actor_fixture,
    repository_method,
):

    actor = request.getfixturevalue(actor_fixture)

    def failing_repository(*args, **kwargs):
        raise SQLAlchemyError("Erreur PostgreSQL simulée")

    with make_client() as client:
        login(client, actor)

        monkeypatch.setattr(
            IncidentRepository,
            repository_method,
            failing_repository,
        )

        response = get_incidents(
            client,
            endpoint,
            status="OPEN",
            priority="HIGH",
        )

        assert response.status_code == 500, response.text


# ==========================================================
# 12. CONSULTATION SANS MODIFICATION EN BASE
# Total : 2 tests
# ==========================================================


@pytest.mark.parametrize(
    "endpoint, actor_fixture",
    [
        ("assigned", "technician_user"),
        ("all", "admin_user"),
    ],
)
def test_filtering_does_not_modify_database(
    request: pytest.FixtureRequest,
    db_session: Session,
    filter_dataset,
    endpoint,
    actor_fixture,
):

    actor = request.getfixturevalue(actor_fixture)

    history_repository = IncidentHistoryRepository(db_session)

    incident_repository = IncidentRepository(db_session)

    def get_incident_snapshot():

        snapshot = {}

        for incident_id in filter_dataset.values():

            incident = incident_repository.get_by_id(incident_id=incident_id)

            assert incident is not None

            snapshot[incident_id] = (
                incident.status,
                incident.priority,
                incident.category,
                incident.assigned_to_id,
                incident.created_by_id,
                incident.title,
                incident.description,
                incident.resolution,
                incident.created_at,
                incident.updated_at,
                incident.resolved_at,
                incident.closed_at,
            )

        return snapshot

    def get_history_snapshot():

        snapshot = {}

        for incident_id in filter_dataset.values():

            events = history_repository.list_by_incident(incident_id=incident_id)

            snapshot[incident_id] = [
                (
                    event.id,
                    event.action,
                    event.field_name,
                    event.old_value,
                    event.new_value,
                )
                for event in events
            ]

        return snapshot

    with make_client() as client:
        login(client, actor)

        # Les mesures sont réalisées après le login,
        # car l'authentification peut créer un audit.
        incidents_before = get_incident_snapshot()
        history_before = get_history_snapshot()
        audits_before = count_audits(db_session)

        response = get_incidents(
            client,
            endpoint,
            status="OPEN",
            priority="HIGH",
            category="SECURITY",
        )

        assert response.status_code == 200, response.text

        db_session.expire_all()

        incidents_after = get_incident_snapshot()
        history_after = get_history_snapshot()
        audits_after = count_audits(db_session)

        # Aucun incident existant ne doit être modifié.
        assert incidents_after == incidents_before

        # Aucun événement d'historique ne doit être créé.
        assert history_after == history_before

        # Aucun audit supplémentaire ne doit être créé.
        assert audits_after == audits_before
