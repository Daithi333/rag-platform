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
    test_database_url: str = (
        "postgresql://rag_platform_user:rag_platform_password@localhost:5432/rag_platform_test_db"
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


class RetrySettings(BaseConfigSettings):
    """Shared retry configuration. Inherited by service settings that make HTTP calls."""

    max_retries: int = 3
    retry_multiplier: float = 2.0
    retry_min_wait: int = 2
    retry_max_wait: int = 20


class DevToSettings(RetrySettings):
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
    max_pages: int = 50  # Cap pagination depth per tag
    tags: list[str] = ["python", "webdev"]  # Tags to ingest


class OpenSearchSettings(BaseConfigSettings):
    model_config = SettingsConfigDict(
        env_file=[".env", str(ENV_FILE_PATH)],
        env_prefix="OPENSEARCH__",
        extra="ignore",
        frozen=True,
        case_sensitive=False,
    )

    host: str = "http://localhost:9200"
    index_name: str = "devto-articles"
    chunk_index_suffix: str = "chunks"
    max_text_size: int = 1_000_000

    # Vector search
    vector_dimension: int = 1024
    vector_space_type: str = "cosinesimil"

    # Hybrid search
    rrf_pipeline_name: str = "hybrid-rrf-pipeline"
    hybrid_search_size_multiplier: int = 2


class ChunkingSettings(BaseConfigSettings):
    model_config = SettingsConfigDict(
        env_file=[".env", str(ENV_FILE_PATH)],
        env_prefix="CHUNKING__",
        extra="ignore",
        frozen=True,
        case_sensitive=False,
    )

    chunk_size: int = 600  # Target words per chunk
    overlap_size: int = 100  # Words to overlap between chunks
    min_chunk_size: int = 100  # Minimum words for a valid chunk


class JinaSettings(RetrySettings):
    model_config = SettingsConfigDict(
        env_file=[".env", str(ENV_FILE_PATH)],
        env_prefix="JINA__",
        extra="ignore",
        frozen=True,
        case_sensitive=False,
    )

    api_key: str = ""
    model: str = "jina-embeddings-v3"
    base_url: str = "https://api.jina.ai/v1"
    batch_size: int = 32
    timeout_seconds: int = 60
    max_retries: int = 5


class OllamaSettings(BaseConfigSettings):
    model_config = SettingsConfigDict(
        env_file=[".env", str(ENV_FILE_PATH)],
        env_prefix="OLLAMA__",
        extra="ignore",
        frozen=True,
        case_sensitive=False,
    )

    host: str = "http://localhost:11434"
    model: str = "llama3.2:3b"
    timeout_seconds: int = 300
    temperature: float = 0.7
    top_p: float = 0.9


class Settings(BaseConfigSettings):
    app_version: str = "0.1.0"
    debug: bool = True
    environment: Literal["development", "staging", "production"] = "development"
    service_name: str = "rag-platform-api"

    cors_origins: list[str] = [
        "http://localhost:7860",
        "http://localhost:3000",
    ]
    cors_methods: list[str] = ["GET", "POST"]

    postgres: PostgresSettings = Field(default_factory=PostgresSettings)
    devto: DevToSettings = Field(default_factory=DevToSettings)
    opensearch: OpenSearchSettings = Field(default_factory=OpenSearchSettings)
    chunking: ChunkingSettings = Field(default_factory=ChunkingSettings)
    jina: JinaSettings = Field(default_factory=JinaSettings)
    ollama: OllamaSettings = Field(default_factory=OllamaSettings)


def get_settings() -> Settings:
    return Settings()
