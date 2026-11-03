from unittest.mock import MagicMock

from sqlalchemy.orm import Session

from app.models.enums import (
    IncidentHistoryAction,
)
from app.models.history import IncidentHistory
from app.repositories.incident_history_repository import IncidentHistoryRepository


def create_incident_history_data() -> IncidentHistory:
    return IncidentHistory(
        incident_id=42, actor_id=2, action=IncidentHistoryAction.INCIDENT_CREATED
    )


def test_create_adds_incident_and_flushes_session() -> None:
    db = MagicMock(spec=Session)
    repository = IncidentHistoryRepository(db)
    incident_data = create_incident_history_data()

    history_entry = repository.create(
        incident_id=incident_data.incident_id,
        actor_id=incident_data.actor_id,
        action=incident_data.action,
    )

    assert history_entry.incident_id == 42
    assert history_entry.actor_id == 2
    assert history_entry.action == IncidentHistoryAction.INCIDENT_CREATED

    db.add.assert_called_once_with(history_entry)
    db.flush.assert_called_once_with()
    db.commit.assert_not_called()
