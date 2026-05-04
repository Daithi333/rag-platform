"""Query builder for OpenSearch supporting BM25, vector, and hybrid search."""

from typing import Any


class QueryBuilder:
    """Builds OpenSearch query bodies for chunk-level search."""

    DEFAULT_FIELDS = ["chunk_text^3", "title^2", "description^1"]

    def __init__(
        self,
        query: str,
        size: int = 10,
        from_: int = 0,
        fields: list[str] | None = None,
        tags: list[str] | None = None,
        sort_by_date: bool = False,
    ):
        self.query = query
        self.size = size
        self.from_ = from_
        self.fields = fields or self.DEFAULT_FIELDS
        self.tags = tags
        self.sort_by_date = sort_by_date

    def build_bm25(self) -> dict[str, Any]:
        """Build a BM25 keyword search query."""
        body = {
            "query": self._build_bool_query(),
            "size": self.size,
            "from": self.from_,
            "track_total_hits": True,
            "_source": {"excludes": ["embedding"]},
            "highlight": self._build_highlight(),
        }

        sort = self._build_sort()
        if sort:
            body["sort"] = sort

        return body

    def build_vector(self, embedding: list[float]) -> dict[str, Any]:
        """Build a pure vector (knn) search query."""
        knn_query = {"knn": {"embedding": {"vector": embedding, "k": self.size}}}

        if self._build_filters():
            knn_query = {"bool": {"must": [knn_query], "filter": self._build_filters()}}

        return {
            "query": knn_query,
            "size": self.size,
            "_source": {"excludes": ["embedding"]},
        }

    def build_hybrid(self, embedding: list[float], size_multiplier: int = 2) -> dict[str, Any]:
        """Build a hybrid query combining BM25 and vector search for RRF."""
        bm25_query = self._build_bool_query()
        knn_query = {"knn": {"embedding": {"vector": embedding, "k": self.size * size_multiplier}}}

        return {
            "query": {
                "hybrid": {
                    "queries": [bm25_query, knn_query],
                }
            },
            "size": self.size,
            "_source": {"excludes": ["embedding"]},
            "highlight": self._build_highlight(),
        }

    def _build_bool_query(self) -> dict[str, Any]:
        """Build the bool query with text match and filters."""
        must = []
        if self.query.strip():
            must.append(self._build_text_query())
        else:
            must.append({"match_all": {}})

        bool_query: dict[str, Any] = {"bool": {"must": must}}

        filters = self._build_filters()
        if filters:
            bool_query["bool"]["filter"] = filters

        return bool_query

    def _build_text_query(self) -> dict[str, Any]:
        """Build multi-match text query with field boosting."""
        return {
            "multi_match": {
                "query": self.query,
                "fields": self.fields,
                "type": "best_fields",
                "operator": "or",
                "fuzziness": "AUTO",
                "prefix_length": 2,
            }
        }

    def _build_filters(self) -> list[dict[str, Any]]:
        """Build filter clauses."""
        filters = []
        if self.tags:
            filters.append({"terms": {"tags": self.tags}})
        return filters

    def _build_highlight(self) -> dict[str, Any]:
        """Build highlighting for search results."""
        return {
            "fields": {
                "chunk_text": {
                    "fragment_size": 150,
                    "number_of_fragments": 2,
                    "pre_tags": ["<mark>"],
                    "post_tags": ["</mark>"],
                },
                "title": {
                    "fragment_size": 0,
                    "number_of_fragments": 0,
                    "pre_tags": ["<mark>"],
                    "post_tags": ["</mark>"],
                },
            },
            "require_field_match": False,
        }

    def _build_sort(self) -> list[dict[str, Any]] | None:
        """Build sort config. None means sort by relevance score."""
        if self.sort_by_date:
            return [{"published_date": {"order": "desc"}}, "_score"]
        if not self.query.strip():
            return [{"published_date": {"order": "desc"}}, "_score"]
        return None
