# 1. créer l'incident avec created_by_id
# 2. récupérer incident.id
# 3. créer une entrée d'historique
#    - incident_id = incident.id
#    - actor_id = created_by_id
#    - action = INCIDENT_CREATED
# 4. retourner l'incident

from app.models.enums import IncidentHistoryAction
from app.models.incident import Incident
from app.repositories.incident_history_repository import IncidentHistoryRepository
from app.repositories.incident_repository import IncidentRepository
from app.schemas.incident import IncidentCreate


class IncidentService:
    def __init__(
        self,
        incident_repository: IncidentRepository,
        incident_history_repository: IncidentHistoryRepository,
    ) -> None:
        self.incident_repository = incident_repository
        self.incident_history_repository = incident_history_repository

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
        return incident
