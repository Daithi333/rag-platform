import asyncio
from collections.abc import AsyncIterator

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.config import DevToSettings
from src.exceptions import (
    DevToAPIException,
    DevToAPITimeoutError,
    DevToParseError,
    DevToRateLimitError,
)
from src.schemas.devto.article import DevToArticle

logger = structlog.getLogger(__name__)


class DevToClient:
    def __init__(self, settings: DevToSettings):
        self._settings = settings

    @property
    def _headers(self) -> dict:
        headers = {"Accept": "application/vnd.forem.api-v1+json"}
        if self._settings.api_key:
            headers["api-key"] = self._settings.api_key
        return headers

    async def health_check(self) -> dict:
        async with httpx.AsyncClient(
            timeout=self._settings.timeout_seconds, headers=self._headers
        ) as client:
            response = await client.get(
                f"{self._settings.base_url}/articles", params={"per_page": 1}
            )
            response.raise_for_status()
        return {"status": "ok", "authenticated": bool(self._settings.api_key)}

    async def fetch_articles(self, tag: str, page: int = 1) -> list[DevToArticle]:
        """Fetch a single page of articles for a given tag."""
        url = f"{self._settings.base_url}/articles"
        params = {"tag": tag, "per_page": self._settings.per_page, "page": page}

        try:
            async with httpx.AsyncClient(
                timeout=self._settings.timeout_seconds, headers=self._headers
            ) as client:
                response = await self._get_with_retry(client, url, params)

            try:
                return [DevToArticle(**article) for article in response.json()]
            except (ValueError, KeyError) as e:
                raise DevToParseError(f"Failed to parse Dev.to response: {e}")

        except DevToRateLimitError:
            raise
        except httpx.TimeoutException as e:
            raise DevToAPITimeoutError(f"Dev.to API timed out fetching tag '{tag}': {e}")
        except Exception as e:
            raise DevToAPIException(f"Failed to fetch articles for tag '{tag}': {e}")

    async def fetch_articles_by_tag(self, tag: str) -> AsyncIterator[list[DevToArticle]]:
        """Yield pages of articles for a tag. Caller controls persistence."""
        page = 1
        max_pages = self._settings.max_pages

        logger.info("Starting fetch", tag=tag, max_pages=max_pages)

        while page <= max_pages:
            try:
                articles = await self.fetch_articles(tag=tag, page=page)
            except DevToAPIException as e:
                logger.error("Page fetch failed, stopping tag", tag=tag, page=page, error=str(e))
                break

            if not articles:
                break

            logger.info(
                "Page fetched",
                tag=tag,
                page=page,
                page_count=len(articles),
            )

            yield articles

            if len(articles) < self._settings.per_page:
                break

            page += 1
            await asyncio.sleep(self._settings.rate_limit_delay)

        logger.info("Tag complete", tag=tag, pages_fetched=page - 1)

    async def fetch_all_articles(self, tags: list[str] | None = None) -> list[DevToArticle]:
        """Fetch all articles across configured tags with pagination.

        Retained for non-pipeline callers (tests, health checks).
        For ingestion, prefer fetch_articles_by_tag for incremental persistence.
        """
        tags = tags or self._settings.tags
        all_articles: list[DevToArticle] = []
        seen_ids: set[int] = set()

        for tag in tags:
            async for page_articles in self.fetch_articles_by_tag(tag):
                for article in page_articles:
                    if article.id not in seen_ids:
                        seen_ids.add(article.id)
                        all_articles.append(article)

        logger.info("Fetch complete", total_unique=len(all_articles), tags=tags)
        return all_articles

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(
            (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError)
        ),
        reraise=True,
    )
    async def _get_with_retry(
        self, client: httpx.AsyncClient, url: str, params: dict
    ) -> httpx.Response:
        """Execute GET request with tenacity retry on transient errors."""
        response = await client.get(url, params=params)

        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 60))
            logger.warning("Rate limited by Dev.to", retry_after=retry_after)
            raise DevToRateLimitError(f"Rate limited, retry after {retry_after}s")

        response.raise_for_status()
        return response
