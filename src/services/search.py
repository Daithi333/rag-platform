"""Search service orchestrating query building, embedding, and OpenSearch."""

import structlog

from src.config import OpenSearchSettings
from src.schemas.api.search import ChunkHit, SearchMode
from src.services.embeddings.client import EmbeddingClient
from src.services.opensearch.client import OpenSearchClient
from src.services.opensearch.index_config import get_chunk_index_name
from src.services.opensearch.query_builder import QueryBuilder

logger = structlog.getLogger(__name__)


class SearchService:
    def __init__(
        self,
        opensearch: OpenSearchClient,
        embedding_client: EmbeddingClient,
        settings: OpenSearchSettings,
    ):
        self._opensearch = opensearch
        self._embedding_client = embedding_client
        self._settings = settings
        self._index_name = get_chunk_index_name(settings)

    async def search(
        self,
        query: str,
        mode: SearchMode = SearchMode.HYBRID,
        tags: list[str] | None = None,
        size: int = 10,
        from_: int = 0,
        sort_by_date: bool = False,
    ) -> dict:
        """Execute a search and return total count and typed hits."""
        builder = QueryBuilder(
            query=query,
            size=size,
            from_=from_,
            tags=tags,
            sort_by_date=sort_by_date,
        )

        pipeline = None
        embedding = None

        if mode in (SearchMode.VECTOR, SearchMode.HYBRID):
            embedding = await self._embedding_client.embed_single(query)

        if mode == SearchMode.BM25:
            query_body = builder.build_bm25()
        elif mode == SearchMode.VECTOR:
            query_body = builder.build_vector(embedding)
        else:
            query_body = builder.build_hybrid(
                embedding,
                size_multiplier=self._settings.hybrid_search_size_multiplier,
            )
            pipeline = self._settings.rrf_pipeline_name

        logger.info(
            "Executing search",
            query=query,
            mode=mode,
            index=self._index_name,
        )

        results = self._opensearch.search(self._index_name, query_body, pipeline=pipeline)

        hits = [self._to_chunk_hit(hit) for hit in results["hits"]]

        return {"total": results["total"], "hits": hits}

    @staticmethod
    def _to_chunk_hit(hit: dict) -> ChunkHit:
        return ChunkHit(
            chunk_id=hit.get("chunk_id") or hit.get("_id"),
            article_id=hit.get("article_id"),
            source_id=hit.get("source_id"),
            chunk_index=hit.get("chunk_index"),
            chunk_text=hit.get("chunk_text", ""),
            chunk_word_count=hit.get("chunk_word_count"),
            title=hit.get("title", ""),
            description=hit.get("description"),
            author=hit.get("author"),
            tags=hit.get("tags", []),
            url=hit.get("url"),
            published_date=hit.get("published_date"),
            score=hit.get("_score", 0.0),
            highlights=hit.get("_highlights"),
        )
