from unittest.mock import MagicMock

from sqlalchemy.orm import Session

from app.models.enums import IncidentCategory, IncidentPriority, IncidentStatus
from app.repositories.incident_repository import IncidentRepository
from app.schemas.incident import IncidentCreate


def create_incident_data() -> IncidentCreate:
    return IncidentCreate(
        title="Erreur concernant bouton ENVOYE",
        description="Le bouton envoyé ne mène à aucun chemin",
        category=IncidentCategory.ANOMALY,
        priority=IncidentPriority.MEDIUM,
    )


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
