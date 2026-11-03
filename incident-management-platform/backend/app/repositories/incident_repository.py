from sqlalchemy.orm import Session

from app.models.enums import IncidentStatus
from app.models.incident import Incident
from app.schemas.incident import IncidentCreate


class IncidentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, *, data: IncidentCreate, created_by_id: int) -> Incident:

        incident = Incident(
            title=data.title,
            description=data.description,
            category=data.category,
            priority=data.priority,
            created_by_id=created_by_id,
            status=IncidentStatus.OPEN,
        )
        self.db.add(incident)
        self.db.flush()

        return incident
