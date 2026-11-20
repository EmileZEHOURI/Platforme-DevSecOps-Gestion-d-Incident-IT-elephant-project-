
from datetime import timedelta

from sqlalchemy.orm import Session

from app.models.incident import Incident
from app.models.user import User
from app.models.enums import (
    IncidentCategory,
    IncidentPriority,
    IncidentStatus,
    IncidentHistoryAction,
)
from app.repositories.incident_history_repository import (
    IncidentHistoryRepository,
)


# ==========================================================
# HELPERS
# ==========================================================


def create_test_incident(
    db_session: Session,
    user_id: int,
    title: str,
) -> Incident:
    incident = Incident(
        title=title,
        description="Incident créé pour tester l'historique.",
        category=IncidentCategory.ANOMALY,
        priority=IncidentPriority.MEDIUM,
        status=IncidentStatus.OPEN,
        created_by_id=user_id,
        assigned_to_id=None,
    )

    db_session.add(incident)
    db_session.flush()

    return incident


def create_history_event(
    repository: IncidentHistoryRepository,
    incident_id: int,
    actor_id: int,
    action: IncidentHistoryAction,
) -> None:
    repository.create(
        incident_id=incident_id,
        actor_id=actor_id,
        action=action,
    )


# ==========================================================
# 1. RECUPERER L'HISTORIQUE D'UN INCIDENT
# ==========================================================


def test_list_by_incident_returns_history(
    db_session: Session,
    test_user: User,
) -> None:

    incident = create_test_incident(
        db_session,
        test_user.id,
        "Incident avec historique",
    )

    repository = IncidentHistoryRepository(db_session)

    create_history_event(
        repository,
        incident.id,
        test_user.id,
        IncidentHistoryAction.INCIDENT_CREATED,
    )

    create_history_event(
        repository,
        incident.id,
        test_user.id,
        IncidentHistoryAction.ASSIGNED,
    )

    create_history_event(
        repository,
        incident.id,
        test_user.id,
        IncidentHistoryAction.PRIORITY_CHANGED,
    )

    db_session.flush()

    history = repository.list_by_incident(
        incident_id=incident.id,
    )

    assert isinstance(history, list)
    assert len(history) == 3

    assert all(
        event.incident_id == incident.id
        for event in history
    )

    assert {
        event.action for event in history
    } == {
        IncidentHistoryAction.INCIDENT_CREATED,
        IncidentHistoryAction.ASSIGNED,
        IncidentHistoryAction.PRIORITY_CHANGED,
    }


# ==========================================================
# 2. ISOLATION ENTRE INCIDENTS
# ==========================================================


def test_list_by_incident_does_not_return_other_history(
    db_session: Session,
    test_user: User,
) -> None:

    incident_1 = create_test_incident(
        db_session,
        test_user.id,
        "Premier incident",
    )

    incident_2 = create_test_incident(
        db_session,
        test_user.id,
        "Deuxième incident",
    )

    repository = IncidentHistoryRepository(db_session)

    create_history_event(
        repository,
        incident_1.id,
        test_user.id,
        IncidentHistoryAction.INCIDENT_CREATED,
    )

    create_history_event(
        repository,
        incident_1.id,
        test_user.id,
        IncidentHistoryAction.ASSIGNED,
    )

    create_history_event(
        repository,
        incident_2.id,
        test_user.id,
        IncidentHistoryAction.INCIDENT_CREATED,
    )

    db_session.flush()

    history_1 = repository.list_by_incident(
        incident_id=incident_1.id,
    )

    history_2 = repository.list_by_incident(
        incident_id=incident_2.id,
    )

    assert len(history_1) == 2
    assert len(history_2) == 1

    assert all(
        event.incident_id == incident_1.id
        for event in history_1
    )

    assert all(
        event.incident_id == incident_2.id
        for event in history_2
    )

    assert history_1[0].id != history_2[0].id


# ==========================================================
# 3. TRI CHRONOLOGIQUE : CREATED_AT PUIS ID
# ==========================================================


def test_list_by_incident_returns_chronological_order(
    db_session: Session,
    test_user: User,
) -> None:

    incident = create_test_incident(
        db_session,
        test_user.id,
        "Incident avec ordre chronologique",
    )

    repository = IncidentHistoryRepository(db_session)

    for action in (
        IncidentHistoryAction.INCIDENT_CREATED,
        IncidentHistoryAction.ASSIGNED,
        IncidentHistoryAction.PRIORITY_CHANGED,
    ):
        create_history_event(
            repository,
            incident.id,
            test_user.id,
            action,
        )

    db_session.flush()

    # Récupérer les événements existants.
    events = repository.list_by_incident(
        incident_id=incident.id,
    )

    assert len(events) == 3

    # Les identifier par leur ID, indépendamment
    # de l'ordre initial retourné par le repository.
    first, second, third = sorted(
        events,
        key=lambda event: event.id,
    )

    # Construire volontairement un ordre temporel
    # différent de l'ordre d'insertion.
    base_time = incident.created_at + timedelta(seconds=1)

    first.created_at = base_time + timedelta(minutes=2)
    second.created_at = base_time
    third.created_at = base_time

    db_session.flush()
    db_session.expire_all()

    history = repository.list_by_incident(
        incident_id=incident.id,
    )

    # SECOND et THIRD possèdent la même date.
    # Ils sont donc départagés par leur ID croissant.
    # FIRST possède la date la plus récente.
    assert [event.id for event in history] == [
        second.id,
        third.id,
        first.id,
    ]

    assert history[0].created_at <= history[1].created_at
    assert history[1].created_at <= history[2].created_at


# ==========================================================
# 4. HISTORIQUE VIDE
# ==========================================================


def test_list_by_incident_returns_empty_list(
    db_session: Session,
    test_user: User,
) -> None:

    incident = create_test_incident(
        db_session,
        test_user.id,
        "Incident sans historique",
    )

    repository = IncidentHistoryRepository(db_session)

    history = repository.list_by_incident(
        incident_id=incident.id,
    )

    assert history == []
    assert isinstance(history, list)
