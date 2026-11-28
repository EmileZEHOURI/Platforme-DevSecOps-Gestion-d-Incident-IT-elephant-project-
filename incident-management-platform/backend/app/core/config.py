from functools import lru_cache
from typing import Literal, Self
from urllib.parse import urlsplit

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration générale de l'application."""

    app_name: str = "Incident Management API"

    environment: Literal["development", "test", "production"] = "development"

    sql_echo: bool = False

    database_url: str

    jwt_secret_key: str
    jwt_algorithm: Literal["HS256"] = "HS256"

    access_token_expire_minutes: int = Field(
        default=30,
        gt=0,
    )

    frontend_origin: str | None = None
    csrf_protection_enabled: bool = False

    redis_url: str | None = None
    login_rate_limit_enabled: bool = False
    jwt_revocation_enabled: bool = False

    @property
    def cors_origins(self) -> list[str]:
        if self.frontend_origin:
            return [self.frontend_origin]
        if self.environment == "production":
            return []
        return ["http://localhost:3000", "http://127.0.0.1:3000"]

    @property
    def jwt_revocation_required(self) -> bool:
        return self.environment == "production" or self.jwt_revocation_enabled

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        hide_input_in_errors=True,
    )

    @model_validator(mode="after")
    def validate_production_security(self) -> Self:
        """Refuse les configurations non sûres en production."""

        if (
            self.environment == "production"
            or self.login_rate_limit_enabled
            or self.jwt_revocation_enabled
        ) and not self.redis_url:
            raise ValueError(
                "REDIS_URL est obligatoire lorsque "
                "la limitation des connexions ou la révocation JWT est activée."
            )

        if self.environment != "production":
            return self

        if len(self.jwt_secret_key.encode("utf-8")) < 32:
            raise ValueError(
                "JWT_SECRET_KEY doit contenir au moins 32 octets en production."
            )

        origin = self.frontend_origin

        if not origin:
            raise ValueError("FRONTEND_ORIGIN est obligatoire en production.")

        try:
            parsed = urlsplit(origin)
            # Déclenche une erreur si le port est invalide.
            _ = parsed.port
        except ValueError as exc:
            raise ValueError("FRONTEND_ORIGIN est invalide.") from exc

        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or origin != f"https://{parsed.netloc}"
        ):
            raise ValueError(
                "FRONTEND_ORIGIN doit être une origine "
                "HTTPS exacte, sans chemin ni paramètres."
            )

        return self


@lru_cache
def get_settings() -> Settings:
    """Charge et met en cache la configuration."""

    return Settings()


settings = get_settings()
