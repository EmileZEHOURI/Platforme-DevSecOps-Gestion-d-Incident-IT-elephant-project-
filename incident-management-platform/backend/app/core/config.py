from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration générale de l'application."""

    app_name: str = "Incident Management API"
    environment: str = "development"
    sql_echo: bool = False

    database_url: str
    
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Charge et met en cache la configuration."""

    return Settings()


settings = get_settings()
