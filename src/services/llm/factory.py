from src.config import LLMProvider, get_settings

from .base import BaseLLMClient
from .client import OllamaLLMClient
from .openai_client import OpenAILLMClient


def make_llm_client() -> BaseLLMClient:
    settings = get_settings()

    match settings.llm_provider:
        case LLMProvider.OLLAMA:
            return OllamaLLMClient(settings=settings.ollama)
        case LLMProvider.OPENAI:
            return OpenAILLMClient(settings=settings.openai)
        case LLMProvider.GROQ:
            return OpenAILLMClient(settings=settings.groq)
