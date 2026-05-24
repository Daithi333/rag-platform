import structlog

from src.config import RedisSettings

from .client import CacheClient

logger = structlog.getLogger(__name__)


def make_cache_client(settings: RedisSettings) -> CacheClient | None:
    """Create a Redis-backed cache client. Returns None if Redis is unavailable."""
    try:
        import redis

        client = redis.Redis(
            host=settings.host,
            port=settings.port,
            password=settings.password or None,
            db=settings.db,
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5,
            retry_on_timeout=True,
        )
        client.ping()
        logger.info("Redis cache connected", host=settings.host, port=settings.port)
        return CacheClient(redis_client=client, settings=settings)
    except Exception as e:
        logger.warning("Redis unavailable, caching disabled", error=str(e))
        return None
