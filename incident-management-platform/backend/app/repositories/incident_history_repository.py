from sqlalchemy.orm import Session

from app.models.enums import IncidentHistoryAction
from app.models.history import IncidentHistory


class IncidentHistoryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        incident_id: int,
        actor_id: int,
        action: IncidentHistoryAction,
        field_name: str | None = None,
        old_value: str | None = None,
        new_value: str | None = None,
    ) -> IncidentHistory:

        incident_history = IncidentHistory(
            incident_id=incident_id,
            actor_id=actor_id,
            action=IncidentHistoryAction.INCIDENT_CREATED,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
        )

        self.db.add(incident_history)
        self.db.flush()

        return incident_history
