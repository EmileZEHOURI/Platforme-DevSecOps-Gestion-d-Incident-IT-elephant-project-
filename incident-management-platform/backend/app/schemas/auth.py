from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class LoginRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    email: EmailStr
    password: str = Field(
        min_length=1,
        max_length=128,
    )

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: Any) -> Any:

        if isinstance(value, str):
            return value.strip().lower()

        return value
