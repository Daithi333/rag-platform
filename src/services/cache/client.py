"""Redis-based exact-match cache for RAG responses."""

import hashlib
import json

import structlog

from src.config import RedisSettings
from src.schemas.api.rag import AskRequest, AskResponse

logger = structlog.getLogger(__name__)


class CacheClient:
    """Exact-match cache keyed on normalised request parameters."""

    def __init__(self, redis_client, settings: RedisSettings):
        self._redis = redis_client
        self._ttl = settings.ttl_seconds

    def _cache_key(self, request: AskRequest) -> str:
        key_data = json.dumps(
            {
                "question": request.question.strip().lower(),
                "mode": request.mode.value,
                "num_chunks": request.num_chunks,
                "tags": sorted(request.tags) if request.tags else [],
            },
            sort_keys=True,
        )
        key_hash = hashlib.sha256(key_data.encode()).hexdigest()[:16]
        return f"rag:ask:{key_hash}"

    async def get(self, request: AskRequest) -> AskResponse | None:
        """Look up a cached response. Returns None on miss or error."""
        try:
            cached = self._redis.get(self._cache_key(request))
            if cached:
                logger.info("Cache hit")
                return AskResponse.model_validate_json(cached)
            return None
        except Exception as e:
            logger.warning("Cache read failed", error=str(e))
            return None

    async def set(self, request: AskRequest, response: AskResponse) -> None:
        """Store a response in cache. Fails silently."""
        try:
            self._redis.set(
                self._cache_key(request),
                response.model_dump_json(),
                ex=self._ttl,
            )
        except Exception as e:
            logger.warning("Cache write failed", error=str(e))
