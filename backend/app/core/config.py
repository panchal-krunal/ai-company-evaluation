from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, loaded from environment variables / `.env`.

    Separate dev / UAT / prod values come from each environment's secrets store;
    never commit real credentials.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Company Evaluation Platform"
    environment: Literal["local", "uat", "production", "test"] = "local"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:5173"]

    database_url: PostgresDsn = PostgresDsn(
        "postgresql+asyncpg://evaluation:evaluation@localhost:5433/evaluation"
    )
    # Create missing tables on startup (local dev convenience). Set false in UAT/production,
    # where `alembic upgrade head` owns the schema.
    auto_create_tables: bool = True
    redis_url: RedisDsn = RedisDsn("redis://localhost:6379/0")

    # Immutable source documents: local folder in development, S3 in UAT/production.
    storage_backend: Literal["local", "s3"] = "local"
    local_storage_dir: str = "storage/objects"
    s3_bucket: str = "evaluation-source-documents"
    s3_endpoint_url: str | None = None
    aws_region: str = "ap-south-1"

    # LLM + embeddings. The LLM interprets evidence; it never computes financial figures.
    anthropic_api_key: SecretStr | None = None
    llm_model: str = "claude-opus-5-5"
    llm_effort: Literal["low", "medium", "high", "xhigh", "max"] = "high"
    voyage_api_key: SecretStr | None = None
    embedding_model: str = "voyage-3.5"
    embedding_dimensions: int = Field(default=1024)

    # Versioned so every evaluation records which rule set produced it.
    formula_version: str = "2026.1"
    warning_review_years: int = 3

    # Research jobs: "background" runs them in the API process (local dev); "queue" sends them to
    # the arq worker via Redis.
    research_execution: Literal["background", "queue"] = "background"
    retrieval_passages_per_query: int = 6
    retrieval_max_passages: int = 18
    prompt_version: str = "2026.1"


@lru_cache
def get_settings() -> Settings:
    return Settings()
