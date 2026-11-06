# IncidentCommentService → gérer les commentaires d’un incident
from typing import TYPE_CHECKING

from app.models.comment import IncidentComment
from app.models.enums import IncidentStatus
from app.models.enums import IncidentHistoryAction
from app.repositories.incident_repository import IncidentRepository

from app.services.incident_service import IncidentNotFoundError
from app.repositories.incident_history_repository import IncidentHistoryRepository
from app.repositories.incident_comment_repository import IncidentCommentRepository

if TYPE_CHECKING:
    from app.schemas.incident_comment import CommentCreate


class IncidentClosedError(Exception):
    """L'incident fermé ne peut plus être modifié."""


class IncidentCommentService:
    def __init__(
        self,
        incident_repository: IncidentRepository,
        incident_history_repository: IncidentHistoryRepository,
        incident_comment_repository: IncidentCommentRepository,
    ) -> None:

        self.incident_repository = incident_repository
        self.incident_history_repository = incident_history_repository
        self.incident_comment_repository = incident_comment_repository

    def add_comment(
        self,
        *,
        incident_id: int,
        author_id: int,
        data: CommentCreate,
    ) -> IncidentComment:
        incident = self.incident_repository.get_by_id_and_creator(
            incident_id=incident_id,
            created_by_id=author_id,
        )

        if incident is None:
            raise IncidentNotFoundError("Incident introuvable")

        if incident.status == IncidentStatus.CLOSED:
            raise IncidentClosedError("Incident fermé")

        created_comment = self.incident_comment_repository.create(
            incident_id=incident_id,
            author_id=author_id,
            data=data,
        )

        self.incident_history_repository.create(
            incident_id=created_comment.incident_id,
            actor_id=created_comment.author_id,
            action=IncidentHistoryAction.COMMENT_ADDED,
        )

        return created_comment
