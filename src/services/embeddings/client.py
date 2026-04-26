"""Jina AI embeddings client."""

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.config import JinaSettings
from src.exceptions import ExternalServiceError

logger = structlog.getLogger(__name__)


class EmbeddingClient:
    """Client for generating text embeddings via the Jina API."""

    def __init__(self, settings: JinaSettings):
        self._settings = settings

    @property
    def _headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._settings.api_key}",
        }

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts, handling batching internally.

        Returns a list of embedding vectors in the same order as the input.
        """
        if not texts:
            return []

        all_embeddings: list[list[float]] = []
        batch_size = self._settings.batch_size

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            embeddings = await self._embed_batch(batch)
            all_embeddings.extend(embeddings)

            logger.info(
                "Embedding batch complete",
                batch=i // batch_size + 1,
                texts_in_batch=len(batch),
                total_done=len(all_embeddings),
                total_remaining=len(texts) - len(all_embeddings),
            )

        return all_embeddings

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(
            (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError)
        ),
        reraise=True,
    )
    async def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a single batch of texts."""
        url = f"{self._settings.base_url}/embeddings"
        payload = {
            "model": self._settings.model,
            "input": texts,
            "normalized": True,
            "embedding_type": "float",
        }

        async with httpx.AsyncClient(timeout=self._settings.timeout_seconds) as client:
            response = await client.post(url, json=payload, headers=self._headers)

            if response.status_code == 402:
                raise ExternalServiceError(
                    "Jina", "Insufficient tokens. Top up at https://jina.ai/embeddings"
                )

            response.raise_for_status()

        data = response.json()
        sorted_embeddings = sorted(data["data"], key=lambda x: x["index"])
        return [item["embedding"] for item in sorted_embeddings]

    async def embed_single(self, text: str) -> list[float]:
        """Embed a single text. Convenience wrapper for search queries."""
        results = await self._embed_batch([text])
        return results[0]
