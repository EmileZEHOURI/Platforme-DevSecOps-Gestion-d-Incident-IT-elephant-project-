from app.models.enums import AuditEventType, AuditResult, IncidentHistoryAction
from app.models.incident import Incident
from app.repositories.audit_repository import AuditRepository
from app.repositories.incident_history_repository import IncidentHistoryRepository
from app.repositories.incident_repository import IncidentRepository
from app.schemas.incident import IncidentCreate



class IncidentNotFoundError(Exception):
    """Incident Not Found"""


class IncidentService:
    def __init__(
        self,
        incident_repository: IncidentRepository,
        incident_history_repository: IncidentHistoryRepository,
        audit_repository: AuditRepository,
    ) -> None:
        self.incident_repository = incident_repository
        self.incident_history_repository = incident_history_repository
        self.audit_repository = audit_repository

    def create_incident(
        self,
        data: IncidentCreate,
        created_by_id: int,
    ) -> Incident:
        incident = self.incident_repository.create(
            data=data,
            created_by_id=created_by_id,
        )
        self.incident_history_repository.create(
            incident_id=incident.id,
            actor_id=created_by_id,
            action=IncidentHistoryAction.INCIDENT_CREATED,
        )
        self.audit_repository.create(
            event_type=AuditEventType.INCIDENT_CREATED,
            result=AuditResult.SUCCESS,
            user_id=created_by_id,
            resource_type="incident",
            resource_id=incident.id,
        )
        return incident

    def list_user_incidents(
        self,
        created_by_id: int,
    ) -> list[Incident]:

        return self.incident_repository.list_by_creator(created_by_id=created_by_id)

    def get_incident_detail(self, incident_id: int, created_by_id: int) -> Incident:
        incident = self.incident_repository.get_by_id_and_creator(
            created_by_id=created_by_id, incident_id=incident_id
        )

        if incident is None:
            raise IncidentNotFoundError("Incident introuvable")

        return incident 