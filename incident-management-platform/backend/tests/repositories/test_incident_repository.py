from unittest.mock import MagicMock

from sqlalchemy.orm import Session

from app.models.enums import IncidentCategory, IncidentPriority, IncidentStatus
from app.models.incident import Incident
from app.repositories.incident_repository import IncidentRepository
from app.schemas.incident import IncidentCreate


def create_incident_data() -> IncidentCreate:
    return IncidentCreate(
        title="Erreur concernant bouton ENVOYE",
        description="Le bouton envoyé ne mène à aucun chemin",
        category=IncidentCategory.ANOMALY,
        priority=IncidentPriority.MEDIUM,
    )


def create_incident_list() -> list[Incident]:
    return [
        Incident(
            id=number,
            title=f"Incident {number}",
            description="Incident de test",
            category=IncidentCategory.ANOMALY,
            priority=IncidentPriority.MEDIUM,
            status=IncidentStatus.OPEN,
            created_by_id=42,
        )
        for number in range(1, 4)
    ]


def test_create_adds_incident_and_flushes_session() -> None:
    db = MagicMock(spec=Session)
    repository = IncidentRepository(db)
    incident_data = create_incident_data()

    incident = repository.create(data=incident_data, created_by_id=42)

    assert incident.title == "Erreur concernant bouton ENVOYE"
    assert incident.description == "Le bouton envoyé ne mène à aucun chemin"
    assert incident.category == IncidentCategory.ANOMALY
    assert incident.priority == IncidentPriority.MEDIUM
    assert incident.status == IncidentStatus.OPEN

    assert incident.created_by_id == 42

    db.add.assert_called_once_with(incident)
    db.flush.assert_called_once_with()
    db.commit.assert_not_called()


def test_checking_incident_list() -> None:
    db = MagicMock(spec=Session)
    repository = IncidentRepository(db)

    expected_incidents = create_incident_list()
    db.scalars.return_value.all.return_value = expected_incidents

    incidents_list = repository.list_by_creator(created_by_id=42)

    assert len(incidents_list) == 3
    assert all(incident.created_by_id == 42 for incident in incidents_list)
    assert [incident.id for incident in incidents_list] == [1, 2, 3]
    db.scalars.assert_called_once()


def test_list_by_creator_returns_empty_list() -> None:
    db = MagicMock(spec=Session)
    db.scalars.return_value.all.return_value = []

    repository = IncidentRepository(db)

    result = repository.list_by_creator(created_by_id=42)

    assert result == []
    db.scalars.assert_called_once()
    db.scalars.return_value.all.assert_called_once_with()


def test_incident_found() -> None:
    db= MagicMock(spec=Session)
    repository = IncidentRepository(db)

    expected_incident = Incident(
                id=1,
                title="Incident 1",
                description="Incident de test",
                category=IncidentCategory.ANOMALY,
                priority=IncidentPriority.MEDIUM,
                status=IncidentStatus.OPEN,
                created_by_id=42,
            )
    db.execute.return_value.scalar_one_or_none.return_value = expected_incident

    incidents_find = repository.get_by_id_and_creator(incident_id=1, created_by_id=42)

    assert incidents_find is expected_incident
    db.execute.assert_called_once()
    
def test_incident_not_found_or_not_authorized() -> None:
    db= MagicMock(spec=Session)
    repository = IncidentRepository(db)

    expected_incident = None
    db.execute.return_value.scalar_one_or_none.return_value = expected_incident

    incidents_find = repository.get_by_id_and_creator(incident_id=1, created_by_id=42)

    assert incidents_find is None
    db.execute.assert_called_once()
    

    
