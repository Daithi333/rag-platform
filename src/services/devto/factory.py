from src.config import get_settings

from .client import DevToClient


def make_devto_client() -> DevToClient:
    settings = get_settings()
    return DevToClient(settings=settings.devto)
