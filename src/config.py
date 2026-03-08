from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings

PROJECT_ROOT = Path(__file__).parent.parent
ENV_FILE_PATH = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    app_version: str = "0.1.0"
    debug: bool = True
    environment: Literal["development", "staging", "production"] = "development"
    service_name: str = "rag-platform-api"


def get_settings() -> Settings:
    return Settings()
