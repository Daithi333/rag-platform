from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from src.config import Settings


@lru_cache
def get_settings() -> Settings:
    """Get application settings."""
    return Settings()


# Dependency annotations
SettingsDep = Annotated[Settings, Depends(get_settings)]
