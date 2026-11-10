"""Environment-backed settings for the AgenticDB-SJ API."""

from functools import lru_cache
from typing import Literal

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
    app_version: str = "0.11.0"
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

    # Day 10 / 11 configurable embedding providers
    embedding_provider: Literal["local", "openai"] = "local"
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimensions: int = Field(default=384, ge=1, le=4096)
    embedding_device: str = "cpu"
    embedding_batch_size: int = Field(default=32, ge=1, le=256)
    openai_embedding_model: str = "text-embedding-3-small"
    openai_embedding_dimensions: int = Field(default=384, ge=1, le=3072)
    openai_embedding_batch_size: int = Field(default=100, ge=1, le=2048)
    vector_search_timeout_ms: int = Field(default=15000, ge=100, le=120000)
    vector_hnsw_ef_search: int = Field(default=80, ge=1, le=1000)

    # Day 11 OpenAI Responses API planning
    planning_provider: Literal["deterministic", "openai"] = "deterministic"
    openai_api_key: SecretStr | None = None
    openai_llm_model: str = "gpt-5.6-terra"
    openai_llm_timeout_seconds: float = Field(default=45.0, gt=0, le=300)
    openai_llm_max_output_tokens: int = Field(default=1200, ge=128, le=8000)
    openai_fallback_to_deterministic: bool = True
    openai_input_cost_per_million: float = Field(default=0.0, ge=0)
    openai_output_cost_per_million: float = Field(default=0.0, ge=0)

    api_host: str = "127.0.0.1"
    api_port: int = Field(default=8000, ge=1, le=65535)


    @property
    def openai_api_key_value(self) -> str:
        """Return a stripped API key or an empty string when not configured."""

        if self.openai_api_key is None:
            return ""
        return self.openai_api_key.get_secret_value().strip()

    @property
    def openai_api_key_configured(self) -> bool:
        """Whether a non-empty OpenAI API key is configured."""

        return bool(self.openai_api_key_value)

    @property
    def active_embedding_dimensions(self) -> int:
        """Return the dimensions for the configured embedding provider."""

        if self.embedding_provider == "openai":
            return self.openai_embedding_dimensions
        return self.embedding_dimensions

    @property
    def active_embedding_model_key(self) -> str:
        """Return the database key for the configured embedding model."""

        if self.embedding_provider == "openai":
            return (
                f"openai:{self.openai_embedding_model}:"
                f"{self.openai_embedding_dimensions}"
            )
        return self.embedding_model_name


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return one cached settings object for the process."""

    return Settings()
