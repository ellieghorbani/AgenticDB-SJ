"""Environment-backed settings for the AgenticDB-SJ API."""

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables or ``.env``."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "AgenticDB-SJ API"
    app_version: str = "0.5.0"
    environment: str = "development"

    postgres_host: str = "127.0.0.1"
    postgres_port: int = 5435
    postgres_db: str = "agenticdb_sj"
    postgres_user: str = "agenticdb"
    postgres_password: SecretStr

    database_connect_timeout_seconds: int = Field(default=5, ge=1, le=60)
    database_statement_timeout_ms: int = Field(default=5000, ge=100, le=120000)

    api_host: str = "127.0.0.1"
    api_port: int = Field(default=8000, ge=1, le=65535)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return one cached settings object for the process."""

    return Settings()
