from unittest.mock import MagicMock

from app.models.enums import (
    AuditEventType,
    AuditResult,
    IncidentCategory,
    IncidentHistoryAction,
    IncidentPriority,
    IncidentStatus,
)
from app.models.incident import Incident
from app.repositories.audit_repository import AuditRepository
from app.repositories.incident_history_repository import IncidentHistoryRepository
from app.repositories.incident_repository import IncidentRepository
from app.schemas.incident import IncidentCreate
from app.services.incident_service import IncidentService

# le repository incident est appelé avec data et created_by_id,


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


def test_success_create_with_data_and_created_by_id() -> None:
    incident_repository = MagicMock(spec=IncidentRepository)
    incident_history_repository = MagicMock(spec=IncidentHistoryRepository)
    audit_repository = MagicMock(spec=AuditRepository)

    # Simulation données envoyé par l'utilisateur
    incident_data = IncidentCreate(
        title="Erreur concernant bouton ENVOYE",
        description="Le bouton envoyé ne mène à aucun chemin",
        category=IncidentCategory.ANOMALY,
        priority=IncidentPriority.MEDIUM,
    )

    # simulation du retour du repository après cette création
    create_incident = Incident(
        id=42,
        title="Erreur concernant bouton ENVOYE",
        description="Le bouton envoyé ne mène à aucun chemin",
        category=IncidentCategory.ANOMALY,
        priority=IncidentPriority.MEDIUM,
        created_by_id=2,
        status=IncidentStatus.OPEN,
    )
    # service appel incident_repository.create(),
    # fais comme  repository avait créé l'incident en base
    # et retourne created_incident
    incident_repository.create.return_value = create_incident

    service = IncidentService(
        incident_repository,
        incident_history_repository,
        audit_repository,
    )

    result = service.create_incident(
        data=incident_data,
        created_by_id=2,
    )

    incident_repository.create.assert_called_once_with(
        data=incident_data, created_by_id=2
    )

    incident_history_repository.create.assert_called_once_with(
        incident_id=42, actor_id=2, action=IncidentHistoryAction.INCIDENT_CREATED
    )

    assert result is create_incident
    audit_repository.create.assert_called_once_with(
        event_type=AuditEventType.INCIDENT_CREATED,
        result=AuditResult.SUCCESS,
        user_id=2,
        resource_type="incident",
        resource_id=42,
    )


def test_recuperation_list() -> None:
    incident_repository = MagicMock(spec=IncidentRepository)
    incident_history_repository = MagicMock(spec=IncidentHistoryRepository)
    audit_repository = MagicMock(spec=AuditRepository)

    expected_incidents = create_incident_list()

    incident_repository.list_by_creator.return_value = expected_incidents

    service = IncidentService(
        incident_repository,
        incident_history_repository,
        audit_repository,
    )

    result = service.list_user_incidents(created_by_id=42)
    incident_repository.list_by_creator.assert_called_once_with(created_by_id=42)

    assert result is expected_incidents


def test_recuperation_empty_list() -> None:
    incident_repository = MagicMock(spec=IncidentRepository)
    incident_history_repository = MagicMock(spec=IncidentHistoryRepository)
    audit_repository = MagicMock(spec=AuditRepository)

    expected_incidents = []

    incident_repository.list_by_creator.return_value = expected_incidents

    service = IncidentService(
        incident_repository,
        incident_history_repository,
        audit_repository,
    )

    result = service.list_user_incidents(created_by_id=42)
    incident_repository.list_by_creator.assert_called_once_with(created_by_id=42)
    assert result is expected_incidents
