from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CommentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(
        min_length=1,
        max_length=5000,
    )

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Le contenu ne doit pas être vide")

        return value


class CommentResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    incident_id: int
    author_id: int
    content: str = Field(
        min_length=1,
        max_length=5000,
    )

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Le contenu ne doit pas être vide")

        return value

    created_at: datetime
    updated_at: datetime | None = None
