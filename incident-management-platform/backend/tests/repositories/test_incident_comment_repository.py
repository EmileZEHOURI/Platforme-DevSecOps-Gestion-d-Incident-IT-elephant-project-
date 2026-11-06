from unittest.mock import MagicMock

from sqlalchemy.orm import Session

from app.models.comment import IncidentComment
from app.repositories.incident_comment_repository import IncidentCommentRepository
from app.schemas.incident_comment import CommentCreate


def create_comment_data() -> IncidentComment:
    return IncidentComment(
        incident_id = 1,
        author_id = 1,
    )

def test_creeate_incident_comment_repository() -> None:
    db = MagicMock(spec=Session)
    repository = IncidentCommentRepository(db)
    comment_data = create_comment_data()

    data = CommentCreate(
        content="Mon commentaire",
    )

    comment_entry = repository.create(
        incident_id=comment_data.incident_id, author_id=comment_data.author_id, data=data
    )

    assert comment_entry.incident_id == 1
    assert comment_entry.author_id == 1
    assert comment_entry.content == data.content

    db.add.assert_called_once_with(comment_entry)
    db.flush.assert_called_once_with()
    db.commit.assert_not_called()
