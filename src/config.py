from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).parent.parent
ENV_FILE_PATH = PROJECT_ROOT / ".env"


class BaseConfigSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[".env", str(ENV_FILE_PATH)],
        extra="ignore",
        frozen=True,
        env_nested_delimiter="__",
        case_sensitive=False,
    )


class PostgresSettings(BaseConfigSettings):
    model_config = SettingsConfigDict(
        env_file=[".env", str(ENV_FILE_PATH)],
        env_prefix="POSTGRES__",
        extra="ignore",
        frozen=True,
        case_sensitive=False,
    )

    database_url: str = (
        "postgresql://rag_platform_user:rag_platform_password@localhost:5432/rag_platform_db"
    )
    echo_sql: bool = False
    pool_size: int = 20
    max_overflow: int = 0

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if not (v.startswith("postgresql://") or v.startswith("postgresql+psycopg2://")):
            raise ValueError(
                "Database URL must start with 'postgresql://' or 'postgresql+psycopg2://'"
            )
        return v


class DevToSettings(BaseConfigSettings):
    model_config = SettingsConfigDict(
        env_file=[".env", str(ENV_FILE_PATH)],
        env_prefix="DEVTO__",
        extra="ignore",
        frozen=True,
        case_sensitive=False,
    )

    api_key: str = ""
    base_url: str = "https://dev.to/api"
    per_page: int = 30  # Max 1000
    rate_limit_delay: float = 0.5  # Seconds between requests
    timeout_seconds: int = 30
    max_retries: int = 3
    tags: list[str] = ["python", "webdev"]  # Tags to ingest


class Settings(BaseConfigSettings):
    app_version: str = "0.1.0"
    debug: bool = True
    environment: Literal["development", "staging", "production"] = "development"
    service_name: str = "rag-platform-api"

    postgres: PostgresSettings = Field(default_factory=PostgresSettings)
    devto: DevToSettings = Field(default_factory=DevToSettings)


def get_settings() -> Settings:
    return Settings()
