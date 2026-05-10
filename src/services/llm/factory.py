from src.config import get_settings

from .client import LLMClient


def make_llm_client() -> LLMClient:
    settings = get_settings()
    return LLMClient(settings=settings.ollama)
