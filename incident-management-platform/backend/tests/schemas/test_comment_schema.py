from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.schemas.incident_comment import CommentCreate, CommentResponse


def test_comment_create_accepts_valid_content() -> None:
    comment = CommentCreate(
        content="Voici un commentaire qui commente bien ce qu'il y a, bien sûr"
    )

    assert (
        comment.content
        == "Voici un commentaire qui commente bien ce qu'il y a, bien sûr"
    )


def test_comment_response_contains_backend_fields() -> None:
    comment = CommentResponse(
        id=1,
        incident_id=1,
        author_id=1,
        content="Voici un commentaire qui commente bien ce qu'il y a, bien sûr",
        created_at=datetime.now(UTC),
    )

    assert comment.id == 1
    assert comment.incident_id == 1
    assert comment.author_id == 1
    assert (
        comment.content
        == "Voici un commentaire qui commente bien ce qu'il y a, bien sûr"
    )
    assert comment.updated_at is None


def test_comment_create_rejects_blank_content() -> None:
    with pytest.raises(ValidationError):
        CommentCreate(content=" ")
