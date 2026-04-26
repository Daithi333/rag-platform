from src.config import get_settings

from .client import OpenSearchClient


def make_opensearch_client() -> OpenSearchClient:
    settings = get_settings()
    return OpenSearchClient(settings=settings.opensearch)
