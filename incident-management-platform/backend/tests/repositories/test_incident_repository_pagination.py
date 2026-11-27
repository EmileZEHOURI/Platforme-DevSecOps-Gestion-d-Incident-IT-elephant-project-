
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from app.models.enums import (
    IncidentCategory,
    IncidentPriority,
    IncidentStatus,
)
from app.models.incident import Incident
from app.models.user import User
from app.repositories.incident_repository import IncidentRepository

# ==========================================================
# HELPERS
# ==========================================================


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
) -> int:

    incident = Incident(
        title=title,
        description="Incident créé pour les tests US-14.",
        category=category,
        priority=priority,
        status=IncidentStatus.OPEN,
        created_by_id=creator_id,
        assigned_to_id=assigned_to_id,
    )

    if created_at is not None:
        incident.created_at = created_at

    db_session.add(incident)
    db_session.flush()

    # Respect des contraintes PostgreSQL.
    if status != IncidentStatus.OPEN:
        assert assigned_to_id is not None

    if status in (
        IncidentStatus.RESOLVED,
        IncidentStatus.CLOSED,
    ):
        incident.resolution = "Incident résolu."
        incident.resolved_at = (
            incident.created_at + timedelta(seconds=1)
        )

    if status == IncidentStatus.CLOSED:
        incident.closed_at = (
            incident.created_at + timedelta(seconds=2)
        )

    incident.status = status

    db_session.flush()

    return incident.id


def list_incidents(
    repository: IncidentRepository,
    scope: str,
    assignee_id: int,
    *,
    limit: int | None = None,
    offset: int = 0,
    status: IncidentStatus | None = None,
    priority: IncidentPriority | None = None,
    category: IncidentCategory | None = None,
) -> list[Incident]:

    filters = {
        "status": status,
        "priority": priority,
        "category": category,
        "limit": limit,
        "offset": offset,
    }

    if scope == "assigned":
        return repository.list_by_assignee(
            assignee_id=assignee_id,
            **filters,
        )

    if scope == "all":
        return repository.list_all(**filters)

    raise ValueError(f"Scope inconnu : {scope}")


def count_incidents(
    repository: IncidentRepository,
    scope: str,
    assignee_id: int,
    *,
    status: IncidentStatus | None = None,
    priority: IncidentPriority | None = None,
    category: IncidentCategory | None = None,
) -> int:

    filters = {
        "status": status,
        "priority": priority,
        "category": category,
    }

    if scope == "assigned":
        return repository.count_by_assignee(
            assignee_id=assignee_id,
            **filters,
        )

    if scope == "all":
        return repository.count_all(**filters)

    raise ValueError(f"Scope inconnu : {scope}")


def incident_ids(incidents: list[Incident]) -> list[int]:
    return [incident.id for incident in incidents]


# ==========================================================
# FIXTURE : JEU DE DONNEES
# ==========================================================


@pytest.fixture
def pagination_dataset(
    db_session: Session,
    test_user: User,
    technician_user: User,
    other_technician_user: User,
) -> dict[str, int]:

    base_time = (
        datetime.now(UTC)
        - timedelta(days=1)
    )

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
            assignee_id,
        ) = definition

        incident_id = create_test_incident(
            db_session,
            test_user.id,
            title=f"US14 Incident {label}",
            assigned_to_id=assignee_id,
            status=incident_status,
            priority=priority,
            category=category,
            created_at=(
                base_time + timedelta(minutes=index)
            ),
        )

        dataset[label] = incident_id

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
        {"status": IncidentStatus.OPEN},
        "ABCD",
        id="status-only",
    ),
    pytest.param(
        {"priority": IncidentPriority.HIGH},
        "ABEF",
        id="priority-only",
    ),
    pytest.param(
        {"category": IncidentCategory.SECURITY},
        "ACEG",
        id="category-only",
    ),
    pytest.param(
        {
            "status": IncidentStatus.OPEN,
            "priority": IncidentPriority.HIGH,
        },
        "AB",
        id="status-priority",
    ),
    pytest.param(
        {
            "status": IncidentStatus.OPEN,
            "category": IncidentCategory.SECURITY,
        },
        "AC",
        id="status-category",
    ),
    pytest.param(
        {
            "priority": IncidentPriority.HIGH,
            "category": IncidentCategory.SECURITY,
        },
        "AE",
        id="priority-category",
    ),
    pytest.param(
        {
            "status": IncidentStatus.OPEN,
            "priority": IncidentPriority.HIGH,
            "category": IncidentCategory.SECURITY,
        },
        "A",
        id="all-filters",
    ),
]


# ==========================================================
# 1. FILTRAGE + PAGINATION + COUNT
# 16 tests
# ==========================================================


@pytest.mark.parametrize("scope", ["assigned", "all"])
@pytest.mark.parametrize(
    "filters, expected_assigned_labels",
    FILTER_CASES,
)
def test_filters_pagination_and_count_are_consistent(
    db_session: Session,
    technician_user: User,
    pagination_dataset,
    scope,
    filters,
    expected_assigned_labels,
):

    repository = IncidentRepository(db_session)

    labels = expected_assigned_labels

    # I et J correspondent à tous les filtres prévus,
    # mais ne sont pas assignés au technicien principal.
    if scope == "all":
        labels += "IJ"

    # Les dates de création croissent de A vers J.
    # Le repository doit retourner l'ordre inverse.
    expected_ids = [
        pagination_dataset[label]
        for label in reversed(labels)
    ]

    # Vérifie la récupération sans pagination.
    all_matching = list_incidents(
        repository,
        scope,
        technician_user.id,
        **filters,
    )

    assert incident_ids(all_matching) == expected_ids

    # Vérifie une page partielle.
    page = list_incidents(
        repository,
        scope,
        technician_user.id,
        limit=2,
        offset=1,
        **filters,
    )

    assert incident_ids(page) == expected_ids[1:3]

    # COUNT doit compter avant LIMIT et OFFSET.
    total = count_incidents(
        repository,
        scope,
        technician_user.id,
        **filters,
    )

    assert total == len(expected_ids)

    # Les éléments d'une page ne peuvent jamais dépasser
    # le nombre total d'incidents correspondants.
    assert len(page) <= total


# ==========================================================
# 2. PREMIERES, DERNIERES ET PAGES INEXISTANTES
# 10 tests
# ==========================================================


@pytest.mark.parametrize("scope", ["assigned", "all"])
@pytest.mark.parametrize(
    "offset, limit",
    [
        pytest.param(0, 3, id="first-page"),
        pytest.param(3, 3, id="second-page"),
        pytest.param(6, 3, id="last-or-penultimate-page"),
        pytest.param(9, 3, id="partial-or-empty-page"),
        pytest.param(30, 3, id="out-of-range-page"),
    ],
)
def test_pagination_returns_correct_slice(
    db_session: Session,
    technician_user: User,
    pagination_dataset,
    scope,
    offset,
    limit,
):

    repository = IncidentRepository(db_session)

    labels = "ABCDEFGH"

    if scope == "all":
        labels += "IJ"

    expected_ids = [
        pagination_dataset[label]
        for label in reversed(labels)
    ]

    result = list_incidents(
        repository,
        scope,
        technician_user.id,
        limit=limit,
        offset=offset,
    )

    assert incident_ids(result) == (
        expected_ids[offset:offset + limit]
    )

    # La pagination ne doit pas modifier le COUNT.
    total = count_incidents(
        repository,
        scope,
        technician_user.id,
    )

    assert total == len(expected_ids)


# ==========================================================
# 3. AUCUN INCIDENT NE CORRESPOND
# 2 tests
# ==========================================================


@pytest.mark.parametrize("scope", ["assigned", "all"])
def test_no_matching_incidents_returns_empty_and_zero(
    db_session: Session,
    technician_user: User,
    pagination_dataset,
    scope,
):

    repository = IncidentRepository(db_session)

    filters = {
        "status": IncidentStatus.CLOSED,
        "priority": IncidentPriority.CRITICAL,
        "category": IncidentCategory.DATA,
    }

    result = list_incidents(
        repository,
        scope,
        technician_user.id,
        limit=10,
        offset=0,
        **filters,
    )

    total = count_incidents(
        repository,
        scope,
        technician_user.id,
        **filters,
    )

    assert result == []
    assert total == 0


# ==========================================================
# 4. OFFSET SANS LIMIT
# 2 tests
# ==========================================================


@pytest.mark.parametrize("scope", ["assigned", "all"])
def test_offset_without_limit(
    db_session: Session,
    technician_user: User,
    pagination_dataset,
    scope,
):

    repository = IncidentRepository(db_session)

    labels = "ABCDEFGH"

    if scope == "all":
        labels += "IJ"

    expected_ids = [
        pagination_dataset[label]
        for label in reversed(labels)
    ]

    result = list_incidents(
        repository,
        scope,
        technician_user.id,
        limit=None,
        offset=4,
    )

    assert incident_ids(result) == expected_ids[4:]


# ==========================================================
# 5. TRI DETERMINISTE : DATE IDENTIQUE
# 2 tests
# ==========================================================


@pytest.mark.parametrize("scope", ["assigned", "all"])
def test_same_creation_date_is_sorted_by_id_desc(
    db_session: Session,
    test_user: User,
    technician_user: User,
    scope,
):

    repository = IncidentRepository(db_session)

    same_date = (
        datetime.now(UTC)
        - timedelta(days=1)
    )

    ids = []

    for index in range(3):

        incident_id = create_test_incident(
            db_session,
            test_user.id,
            title=f"Incident même date {index}",
            assigned_to_id=technician_user.id,
            status=IncidentStatus.OPEN,
            created_at=same_date,
        )

        ids.append(incident_id)

    result = list_incidents(
        repository,
        scope,
        technician_user.id,
        limit=3,
        offset=0,
    )

    assert incident_ids(result) == sorted(
        ids,
        reverse=True,
    )

    # Page intermédiaire : un seul incident.
    second_result = list_incidents(
        repository,
        scope,
        technician_user.id,
        limit=1,
        offset=1,
    )

    expected_middle_id = sorted(ids, reverse=True)[1]

    assert incident_ids(second_result) == [
        expected_middle_id
    ]

    assert count_incidents(
        repository,
        scope,
        technician_user.id,
    ) == 3


# ==========================================================
# 6. INCIDENTS RESOLUS ET CLOTURES
# 4 tests
# ==========================================================


@pytest.mark.parametrize("scope", ["assigned", "all"])
@pytest.mark.parametrize(
    "incident_status",
    [
        IncidentStatus.RESOLVED,
        IncidentStatus.CLOSED,
    ],
)
def test_count_and_paginate_resolved_closed_incidents(
    db_session: Session,
    test_user: User,
    technician_user: User,
    scope,
    incident_status,
):

    repository = IncidentRepository(db_session)

    base_time = (
        datetime.now(UTC)
        - timedelta(days=1)
    )

    target_id = create_test_incident(
        db_session,
        test_user.id,
        title="Incident avec statut recherché",
        assigned_to_id=technician_user.id,
        status=incident_status,
        priority=IncidentPriority.HIGH,
        category=IncidentCategory.SECURITY,
        created_at=base_time,
    )

    # Incident supplémentaire ne correspondant pas
    # au filtre de statut.
    create_test_incident(
        db_session,
        test_user.id,
        title="Incident ouvert",
        assigned_to_id=technician_user.id,
        status=IncidentStatus.OPEN,
        priority=IncidentPriority.HIGH,
        category=IncidentCategory.SECURITY,
        created_at=base_time,
    )

    filters = {
        "status": incident_status,
        "priority": IncidentPriority.HIGH,
        "category": IncidentCategory.SECURITY,
    }

    result = list_incidents(
        repository,
        scope,
        technician_user.id,
        limit=5,
        offset=0,
        **filters,
    )

    total = count_incidents(
        repository,
        scope,
        technician_user.id,
        **filters,
    )

    assert incident_ids(result) == [target_id]
    assert total == 1


# ==========================================================
# 7. ISOLATION ENTRE TECHNICIENS
# 1 test
# ==========================================================


def test_count_respects_assignee_restriction(
    db_session: Session,
    technician_user: User,
    other_technician_user: User,
    pagination_dataset,
):

    repository = IncidentRepository(db_session)

    # Huit incidents pour le technicien principal.
    assert repository.count_by_assignee(
        assignee_id=technician_user.id,
    ) == 8

    # Un seul incident pour l'autre technicien.
    assert repository.count_by_assignee(
        assignee_id=other_technician_user.id,
    ) == 1

    # Dix incidents au total, dont un non assigné.
    assert repository.count_all() == 10

    # Ces trois incidents correspondent aux mêmes filtres :
    # A pour le technicien 1, I pour le technicien 2,
    # J non assigné.
    filters = {
        "status": IncidentStatus.OPEN,
        "priority": IncidentPriority.HIGH,
        "category": IncidentCategory.SECURITY,
    }

    assert repository.count_by_assignee(
        assignee_id=technician_user.id,
        **filters,
    ) == 1

    assert repository.count_by_assignee(
        assignee_id=other_technician_user.id,
        **filters,
    ) == 1

    assert repository.count_all(**filters) == 3

    # La liste globale inclut l'incident non assigné.
    result = repository.list_all(**filters)

    assert pagination_dataset["J"] in incident_ids(result)


# ==========================================================
# 8. BASE SANS INCIDENT
# 2 tests
# ==========================================================


@pytest.mark.parametrize("scope", ["assigned", "all"])
def test_empty_incident_table_returns_zero(
    db_session: Session,
    technician_user: User,
    scope,
):

    repository = IncidentRepository(db_session)

    result = list_incidents(
        repository,
        scope,
        technician_user.id,
        limit=20,
        offset=0,
    )

    total = count_incidents(
        repository,
        scope,
        technician_user.id,
    )

    assert result == []
    assert total == 0


# ==========================================================
# 9. COUNT EXECUTE UNE SEULE REQUETE SCALAR
# 1 test
# ==========================================================


def test_count_methods_call_scalar_only_once(
    db_session: Session,
    test_user: User,
    technician_user: User,
    monkeypatch: pytest.MonkeyPatch,
):

    create_test_incident(
        db_session,
        test_user.id,
        title="Incident test COUNT unique",
        assigned_to_id=technician_user.id,
    )

    repository = IncidentRepository(db_session)

    original_scalar = db_session.scalar
    scalar_calls = []

    def counting_scalar(*args, **kwargs):
        scalar_calls.append((args, kwargs))
        return original_scalar(*args, **kwargs)

    monkeypatch.setattr(
        db_session,
        "scalar",
        counting_scalar,
    )

    total_assigned = repository.count_by_assignee(
        assignee_id=technician_user.id,
    )

    assert total_assigned == 1

    # Détecte notre ancienne erreur :
    # deux appels successifs à self.db.scalar(statement).
    assert len(scalar_calls) == 1

    scalar_calls.clear()

    total_all = repository.count_all()

    assert total_all == 1
    assert len(scalar_calls) == 1


# ==========================================================
# 10. RETROCOMPATIBILITE AVEC L'US-13
# 2 tests
# ==========================================================


@pytest.mark.parametrize("scope", ["assigned", "all"])
def test_previous_calls_work_without_pagination_parameters(
    db_session: Session,
    technician_user: User,
    pagination_dataset,
    scope,
):

    repository = IncidentRepository(db_session)

    # On appelle volontairement les méthodes sans
    # limit et sans offset, comme avant l'US-14.
    if scope == "assigned":
        result = repository.list_by_assignee(
            assignee_id=technician_user.id,
        )
        expected_labels = "ABCDEFGH"

    else:
        result = repository.list_all()
        expected_labels = "ABCDEFGHIJ"

    expected_ids = [
        pagination_dataset[label]
        for label in reversed(expected_labels)
    ]

    assert incident_ids(result) == expected_ids
