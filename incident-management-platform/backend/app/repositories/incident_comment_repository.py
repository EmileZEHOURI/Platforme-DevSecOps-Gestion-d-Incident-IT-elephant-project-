from sqlalchemy.orm import Session

from app.models.comment import IncidentComment
from app.schemas.incident_comment import CommentCreate


class IncidentCommentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        incident_id: int,
        author_id: int,
        data: CommentCreate,
    ) -> IncidentComment:

        incident_comment = IncidentComment(
            incident_id=incident_id, author_id=author_id, content=data.content
        )

        self.db.add(incident_comment)
        self.db.flush()

        return incident_comment
