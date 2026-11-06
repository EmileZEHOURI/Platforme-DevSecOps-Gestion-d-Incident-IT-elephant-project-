from unittest.mock import MagicMock
import pytest


from app.models.enums import (
    IncidentCategory,
    IncidentPriority,
    IncidentStatus,
    IncidentHistoryAction,
)


from app.models.incident import Incident
from app.models.comment import IncidentComment
from app.schemas.incident_comment import CommentCreate

from app.repositories.incident_history_repository import IncidentHistoryRepository
from app.repositories.incident_repository import (
    IncidentRepository,
)
from app.repositories.incident_comment_repository import IncidentCommentRepository
from app.services.incident_comment_service import (
    IncidentCommentService,
    IncidentClosedError,
)
from app.services.incident_service import (
    IncidentNotFoundError,
)


def test_successful_created_comment() -> None:
    incident_repository = MagicMock(spec=IncidentRepository)
    incident_history_repository = MagicMock(spec=IncidentHistoryRepository)
    incident_comment_repository = MagicMock(spec=IncidentCommentRepository)

    existing_incident = Incident(
        id=42,
        title="Erreur concernant bouton ENVOYE",
        description="Le bouton envoyé ne mène à aucun chemin",
        category=IncidentCategory.ANOMALY,
        priority=IncidentPriority.MEDIUM,
        created_by_id=2,
        status=IncidentStatus.OPEN,
    )

    incident_repository.get_by_id_and_creator.return_value = existing_incident

    comment_data = CommentCreate(content="Le problème est toujours présent.")

    created_comment = IncidentComment(
        incident_id=existing_incident.id,
        author_id=existing_incident.created_by_id,
        content=comment_data.content,
    )

    incident_comment_repository.create.return_value = created_comment

    service = IncidentCommentService(
        incident_repository,
        incident_history_repository,
        incident_comment_repository,
    )

    result = service.add_comment(
        incident_id=existing_incident.id,
        author_id=existing_incident.created_by_id,
        data=comment_data,
    )

    incident_comment_repository.create.assert_called_once_with(
        incident_id=existing_incident.id,
        author_id=existing_incident.created_by_id,
        data=comment_data,
    )

    incident_history_repository.create.assert_called_once_with(
        incident_id=42, actor_id=2, action=IncidentHistoryAction.COMMENT_ADDED
    )

    assert result is created_comment


def test_incident_not_accessible() -> None:
    incident_repository = MagicMock(spec=IncidentRepository)
    incident_history_repository = MagicMock(spec=IncidentHistoryRepository)
    incident_comment_repository = MagicMock(spec=IncidentCommentRepository)

    service = IncidentCommentService(
        incident_repository,
        incident_history_repository,
        incident_comment_repository,
    )

    incident_repository.get_by_id_and_creator.return_value = None

    comment_data = CommentCreate(content="Le problème est toujours présent.")

    with pytest.raises(IncidentNotFoundError, match="Incident introuvable"):
        service.add_comment(
            incident_id=42,
            author_id=2,
            data=comment_data,
        )

    incident_repository.get_by_id_and_creator.assert_called_once_with(
        incident_id=42,
        created_by_id=2,
    )

    incident_comment_repository.create.assert_not_called()
    incident_history_repository.create.assert_not_called()


def test_incident_closed() -> None:

    incident_repository = MagicMock(spec=IncidentRepository)
    incident_history_repository = MagicMock(spec=IncidentHistoryRepository)
    incident_comment_repository = MagicMock(spec=IncidentCommentRepository)

    existing_incident = Incident(
        id=42,
        title="Erreur concernant bouton ENVOYE",
        description="Le bouton envoyé ne mène à aucun chemin",
        category=IncidentCategory.ANOMALY,
        priority=IncidentPriority.MEDIUM,
        created_by_id=2,
        status=IncidentStatus.CLOSED,
    )

    service = IncidentCommentService(
        incident_repository,
        incident_history_repository,
        incident_comment_repository,
    )

    incident_repository.get_by_id_and_creator.return_value = existing_incident

    comment_data = CommentCreate(content="Le problème est toujours présent.")

    with pytest.raises(IncidentClosedError, match="Incident fermé"):
        service.add_comment(
            incident_id=42,
            author_id=2,
            data=comment_data,
        )

    incident_repository.get_by_id_and_creator.assert_called_once_with(
        incident_id=42,
        created_by_id=2,
    )

    incident_comment_repository.create.assert_not_called()
    incident_history_repository.create.assert_not_called()
