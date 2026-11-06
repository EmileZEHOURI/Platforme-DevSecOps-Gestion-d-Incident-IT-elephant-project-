from sqlalchemy import select
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

    def list_by_creator(self, *, created_by_id: int) -> list[Incident]:
        statement = (
            select(Incident)
            .where(Incident.created_by_id == created_by_id)
            .order_by(Incident.created_at.desc())
        )

        return self.db.scalars(statement).all()

    def get_by_id_and_creator(
        self,
        *,
        incident_id: int,
        created_by_id: int,
    ) -> Incident | None:
        statement = (
            select(Incident)
            .where(Incident.id == incident_id)
            .where(Incident.created_by_id == created_by_id)
        )

        return self.db.execute(statement).scalar_one_or_none()

    def list_by_assignee(self, *, assigned_to_id: int) -> list[Incident]:
        statement = (
            select(Incident)
            .where(Incident.assigned_to_id == assigned_to_id)
            .order_by(Incident.created_at.desc())
        )

        return self.db.scalars(statement).all()
