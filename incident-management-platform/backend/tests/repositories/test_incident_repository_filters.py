"""US-13 : tests d'intégration PostgreSQL du repository des incidents.

À placer dans backend/tests/repositories/.
Utilise uniquement les fixtures existantes de tests/conftest.py.
La variable TEST_DATABASE_URL doit viser la base de test *_test.
"""

from datetime import timedelta

import pytest
from sqlalchemy.orm import Session

from app.models.enums import IncidentCategory, IncidentPriority, IncidentStatus
from app.models.incident import Incident
from app.models.user import User
from app.repositories.incident_repository import IncidentRepository


def create_incident(
    db_session: Session,
    *,
    creator_id: int,
    label: str,
    assignee_id: int | None = None,
    status: IncidentStatus = IncidentStatus.OPEN,
    priority: IncidentPriority = IncidentPriority.MEDIUM,
    category: IncidentCategory = IncidentCategory.SUPPORT,
) -> Incident:
    """Créer un incident sans passer par l'API ni écrire un historique."""
    # Toujours créer en OPEN, puis renseigner les dates et le statut.
    # Évite les contraintes d'assignation et de chronologie PostgreSQL.
    if status != IncidentStatus.OPEN and assignee_id is None:
        raise ValueError("Un incident non OPEN doit être assigné.")

    incident = Incident(
        title=f"Incident US-13 {label}",
        description="Incident créé pour vérifier les filtres du repository.",
        created_by_id=creator_id,
        assigned_to_id=assignee_id,
        status=IncidentStatus.OPEN,
        priority=priority,
        category=category,
    )
    db_session.add(incident)
    db_session.flush()

    if status in (IncidentStatus.RESOLVED, IncidentStatus.CLOSED):
        incident.resolution = "Problème corrigé et solution vérifiée."
        incident.resolved_at = incident.created_at

    if status == IncidentStatus.CLOSED:
        incident.closed_at = incident.resolved_at

    if status != IncidentStatus.OPEN:
        incident.status = status
        db_session.flush()

    return incident


def result_ids(incidents: list[Incident]) -> set[int]:
    assert isinstance(incidents, list)
    ids = {incident.id for incident in incidents}
    assert len(ids) == len(incidents), "Des incidents sont dupliqués."
    return ids


@pytest.fixture
def filter_incidents(
    db_session: Session,
    test_user: User,
    technician_user: User,
    other_technician_user: User,
) -> dict[str, Incident]:
    """8 combinaisons dans le périmètre + 2 incidents hors périmètre.

    Les critères cibles sont OPEN, HIGH et SECURITY.
    Les deux incidents hors périmètre satisfont les trois critères :
    ils doivent apparaître dans list_all, jamais dans list_by_assignee.
    """
    fixtures = {}
    specs = [
        # label, statut, priorité, catégorie
        ("A", IncidentStatus.OPEN, IncidentPriority.HIGH, IncidentCategory.SECURITY),
        ("B", IncidentStatus.OPEN, IncidentPriority.HIGH, IncidentCategory.SUPPORT),
        ("C", IncidentStatus.OPEN, IncidentPriority.MEDIUM, IncidentCategory.SECURITY),
        ("D", IncidentStatus.OPEN, IncidentPriority.MEDIUM, IncidentCategory.SUPPORT),
        ("E", IncidentStatus.IN_PROGRESS, IncidentPriority.HIGH, IncidentCategory.SECURITY),
        ("F", IncidentStatus.IN_PROGRESS, IncidentPriority.HIGH, IncidentCategory.SUPPORT),
        ("G", IncidentStatus.IN_PROGRESS, IncidentPriority.MEDIUM, IncidentCategory.SECURITY),
        ("H", IncidentStatus.IN_PROGRESS, IncidentPriority.MEDIUM, IncidentCategory.SUPPORT),
    ]
    for label, status, priority, category in specs:
        fixtures[label] = create_incident(
            db_session,
            creator_id=test_user.id,
            assignee_id=technician_user.id,
            label=label,
            status=status,
            priority=priority,
            category=category,
        )

    for label, assignee_id in (
        ("OTHER", other_technician_user.id),
        ("UNASSIGNED", None),
    ):
        fixtures[label] = create_incident(
            db_session,
            creator_id=test_user.id,
            assignee_id=assignee_id,
            label=label,
            status=IncidentStatus.OPEN,
            priority=IncidentPriority.HIGH,
            category=IncidentCategory.SECURITY,
        )
    return fixtures


# Les résultats attendus sont définis explicitement, indépendamment du code testé.
FILTER_CASES = [
    pytest.param({}, "ABCDEFGH", id="no-filters"),
    pytest.param({"status": IncidentStatus.OPEN}, "ABCD", id="status"),
    pytest.param({"priority": IncidentPriority.HIGH}, "ABEF", id="priority"),
    pytest.param({"category": IncidentCategory.SECURITY}, "ACEG", id="category"),
    pytest.param(
        {"status": IncidentStatus.OPEN, "priority": IncidentPriority.HIGH},
        "AB", id="status-and-priority",
    ),
    pytest.param(
        {"status": IncidentStatus.OPEN, "category": IncidentCategory.SECURITY},
        "AC", id="status-and-category",
    ),
    pytest.param(
        {"priority": IncidentPriority.HIGH, "category": IncidentCategory.SECURITY},
        "AE", id="priority-and-category",
    ),
    pytest.param(
        {
            "status": IncidentStatus.OPEN,
            "priority": IncidentPriority.HIGH,
            "category": IncidentCategory.SECURITY,
        },
        "A", id="all-three-filters",
    ),
]


# 1. Les huit combinaisons de filtres pour chaque méthode publique (16 tests).
@pytest.mark.parametrize("filters, expected_labels", FILTER_CASES)
def test_list_by_assignee_filter_combinations(
    db_session: Session,
    technician_user: User,
    filter_incidents: dict[str, Incident],
    filters: dict,
    expected_labels: str,
) -> None:
    repository = IncidentRepository(db_session)
    incidents = repository.list_by_assignee(technician_user.id, **filters)
    expected = {filter_incidents[label].id for label in expected_labels}

    assert result_ids(incidents) == expected
    assert all(incident.assigned_to_id == technician_user.id for incident in incidents)


@pytest.mark.parametrize("filters, expected_labels", FILTER_CASES)
def test_list_all_filter_combinations(
    db_session: Session,
    filter_incidents: dict[str, Incident],
    filters: dict,
    expected_labels: str,
) -> None:
    repository = IncidentRepository(db_session)
    incidents = repository.list_all(**filters)
    expected = {filter_incidents[label].id for label in expected_labels}
    expected.update(
        (filter_incidents["OTHER"].id, filter_incidents["UNASSIGNED"].id)
    )

    assert result_ids(incidents) == expected
    assert any(incident.assigned_to_id is None for incident in incidents)


# 2. Aucun résultat malgré une valeur de filtre valide (2 tests).
@pytest.mark.parametrize("method", ["assigned", "all"])
def test_filters_return_empty_list(
    db_session: Session,
    technician_user: User,
    filter_incidents: dict[str, Incident],
    method: str,
) -> None:
    repository = IncidentRepository(db_session)
    if method == "assigned":
        incidents = repository.list_by_assignee(
            technician_user.id, priority=IncidentPriority.CRITICAL
        )
    else:
        incidents = repository.list_all(priority=IncidentPriority.CRITICAL)
    assert incidents == []
    assert isinstance(incidents, list)


# 3. Supprimer les filtres restaure la liste initiale (2 tests).
@pytest.mark.parametrize("method", ["assigned", "all"])
def test_removing_filters_restores_default_list(
    db_session: Session,
    technician_user: User,
    filter_incidents: dict[str, Incident],
    method: str,
) -> None:
    repository = IncidentRepository(db_session)
    if method == "assigned":
        original = repository.list_by_assignee(technician_user.id)
        filtered = repository.list_by_assignee(
            technician_user.id, status=IncidentStatus.OPEN
        )
        restored = repository.list_by_assignee(
            technician_user.id, status=None, priority=None, category=None
        )
    else:
        original = repository.list_all()
        filtered = repository.list_all(status=IncidentStatus.OPEN)
        restored = repository.list_all(status=None, priority=None, category=None)
    assert result_ids(filtered) < result_ids(original)
    assert result_ids(restored) == result_ids(original)


# 4. Le tri décroissant est conservé après filtrage (2 tests).
@pytest.mark.parametrize("method", ["assigned", "all"])
def test_filtered_incidents_are_sorted_by_creation_desc(
    db_session: Session,
    test_user: User,
    technician_user: User,
    method: str,
) -> None:
    incidents = [
        create_incident(
            db_session,
            creator_id=test_user.id,
            assignee_id=technician_user.id,
            priority=IncidentPriority.HIGH,
            label=f"sort-{index}",
        )
        for index in range(3)
    ]
    first, second, third = incidents
    # Dates distinctes, volontairement différentes de l'ordre d'insertion.
    base = min(incident.created_at for incident in incidents)
    first.created_at = base - timedelta(minutes=1)
    second.created_at = base - timedelta(minutes=3)
    third.created_at = base - timedelta(minutes=2)
    db_session.flush()
    expected_ids = [first.id, third.id, second.id]
    db_session.expire_all()

    repository = IncidentRepository(db_session)
    if method == "assigned":
        results = repository.list_by_assignee(
            technician_user.id, priority=IncidentPriority.HIGH
        )
    else:
        results = repository.list_all(priority=IncidentPriority.HIGH)
    assert [incident.id for incident in results] == expected_ids


# 5. Les statuts RESOLVED et CLOSED sont aussi filtrables (4 tests).
@pytest.mark.parametrize("method", ["assigned", "all"])
@pytest.mark.parametrize("target_status", [IncidentStatus.RESOLVED, IncidentStatus.CLOSED])
def test_filter_resolved_and_closed_incidents(
    db_session: Session,
    test_user: User,
    technician_user: User,
    method: str,
    target_status: IncidentStatus,
) -> None:
    created = {}
    for status in IncidentStatus:
        created[status] = create_incident(
            db_session,
            creator_id=test_user.id,
            assignee_id=technician_user.id,
            status=status,
            label=status.name,
            priority=IncidentPriority.LOW,
            category=IncidentCategory.DATA,
        )
    db_session.expire_all()
    repository = IncidentRepository(db_session)
    if method == "assigned":
        results = repository.list_by_assignee(
            technician_user.id, status=target_status
        )
    else:
        results = repository.list_all(status=target_status)
    assert result_ids(results) == {created[target_status].id}
    assert results[0].status == target_status


# 6. Technicien sans incident correspondant : liste vide (1 test).
def test_other_technician_does_not_receive_matching_incidents(
    db_session: Session,
    test_user: User,
    technician_user: User,
    other_technician_user: User,
) -> None:
    create_incident(
        db_session,
        creator_id=test_user.id,
        assignee_id=technician_user.id,
        label="private-scope",
        status=IncidentStatus.OPEN,
        priority=IncidentPriority.HIGH,
        category=IncidentCategory.SECURITY,
    )
    repository = IncidentRepository(db_session)
    assert repository.list_by_assignee(other_technician_user.id) == []
    assert repository.list_by_assignee(
        other_technician_user.id,
        status=IncidentStatus.OPEN,
        priority=IncidentPriority.HIGH,
        category=IncidentCategory.SECURITY,
    ) == []
