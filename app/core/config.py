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
    app_version: str = "0.10.0"
    environment: str = "development"

    postgres_host: str = "127.0.0.1"
    postgres_port: int = 5435
    postgres_db: str = "agenticdb_sj"
    postgres_user: str = "agenticdb"
    postgres_password: SecretStr

    database_connect_timeout_seconds: int = Field(default=5, ge=1, le=60)
    database_statement_timeout_ms: int = Field(default=5000, ge=100, le=120000)

    copilot_execution_role: str = Field(
        default="agenticdb_reader",
        pattern=r"^[a-z_][a-z0-9_]*$",
    )
    copilot_execution_timeout_ms: int = Field(
        default=15000,
        ge=100,
        le=120000,
    )
    copilot_lock_timeout_ms: int = Field(default=2000, ge=0, le=30000)
    copilot_max_result_rows: int = Field(default=1000, ge=1, le=5000)
    agent_default_evidence_rows: int = Field(default=5, ge=0, le=20)

    # Day 10 local embedding and pgvector retrieval
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimensions: int = Field(default=384, ge=1, le=4096)
    embedding_device: str = "cpu"
    embedding_batch_size: int = Field(default=32, ge=1, le=256)
    vector_search_timeout_ms: int = Field(default=15000, ge=100, le=120000)
    vector_hnsw_ef_search: int = Field(default=80, ge=1, le=1000)

    api_host: str = "127.0.0.1"
    api_port: int = Field(default=8000, ge=1, le=65535)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return one cached settings object for the process."""

    return Settings()
