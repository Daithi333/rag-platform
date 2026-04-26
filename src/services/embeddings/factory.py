from src.config import get_settings

from .client import EmbeddingClient


def make_embedding_client() -> EmbeddingClient:
    settings = get_settings()
    return EmbeddingClient(settings=settings.jina)
