"""Generic OpenSearch client for index management, document indexing, and search."""

from typing import Any

import structlog
from opensearchpy import OpenSearch, helpers

from src.config import OpenSearchSettings

logger = structlog.getLogger(__name__)


class OpenSearchClient:
    """OpenSearch client supporting BM25 and hybrid search with native RRF."""

    def __init__(self, settings: OpenSearchSettings):
        self._settings = settings
        self._client = OpenSearch(
            hosts=[settings.host],
            use_ssl=False,
            verify_certs=False,
            ssl_show_warn=False,
        )
        logger.info("OpenSearch client initialised", host=settings.host)

    @property
    def raw_client(self) -> OpenSearch:
        """Expose the underlying client for dependency injection."""
        return self._client

    def close(self) -> None:
        self._client.close()

    # -- Cluster operations --

    def health_check(self) -> dict[str, Any]:
        """Check cluster health. Returns the raw health response."""
        try:
            health = self._client.cluster.health()
            return {
                "status": health.get("status", "unknown"),
                "healthy": health.get("status") in ("green", "yellow"),
            }
        except Exception as e:
            logger.error("Health check failed", error=str(e))
            return {"status": "unreachable", "healthy": False, "error": str(e)}

    # -- Index operations --

    def index_exists(self, index_name: str) -> bool:
        return self._client.indices.exists(index=index_name)

    def document_exists(self, index_name: str, field: str, value: str) -> bool:
        """Check if any document with field=value exists in the index."""
        try:
            if not self.index_exists(index_name):
                return False
            response = self._client.count(
                index=index_name, body={"query": {"term": {field: value}}}
            )
            return response.get("count", 0) > 0
        except Exception:
            return False

    def get_indexed_ids(self, index_name: str, field: str) -> set[str]:
        """Get all unique values for a keyword field. Useful for bulk 'already indexed' checks."""
        try:
            if not self.index_exists(index_name):
                return set()
            result = self._client.search(
                index=index_name,
                body={
                    "size": 0,
                    "aggs": {"ids": {"terms": {"field": field, "size": 100000}}},
                },
            )
            return {bucket["key"] for bucket in result["aggregations"]["ids"]["buckets"]}
        except Exception as e:
            logger.error("Failed to get indexed IDs", error=str(e))
            return set()

    def get_ids_missing_field(self, index_name: str, field: str, id_field: str) -> set[str]:
        """Get unique IDs of documents where a field does not exist."""
        try:
            if not self.index_exists(index_name):
                return set()
            result = self._client.search(
                index=index_name,
                body={
                    "size": 0,
                    "query": {"bool": {"must_not": {"exists": {"field": field}}}},
                    "aggs": {"ids": {"terms": {"field": id_field, "size": 100000}}},
                },
            )
            ids = {bucket["key"] for bucket in result["aggregations"]["ids"]["buckets"]}
            logger.info(
                "Found documents missing field",
                index=index_name,
                field=field,
                count=len(ids),
            )
            return ids
        except Exception as e:
            logger.error("Failed to get IDs missing field", error=str(e))
            return set()

    def create_index(self, index_name: str, mapping: dict[str, Any], force: bool = False) -> bool:
        """Create an index with the given mapping. Returns True if created."""
        try:
            if force and self.index_exists(index_name):
                self._client.indices.delete(index=index_name)
                logger.info("Deleted existing index", index=index_name)

            if not self.index_exists(index_name):
                self._client.indices.create(index=index_name, body=mapping)
                logger.info("Created index", index=index_name)
                return True

            logger.info("Index already exists", index=index_name)
            return False

        except Exception as e:
            if "resource_already_exists_exception" in str(e):
                logger.info("Index created by another worker", index=index_name)
                return False
            logger.error("Failed to create index", index=index_name, error=str(e))
            raise

    def get_index_stats(self, index_name: str) -> dict[str, Any]:
        """Get document count and size for an index."""
        try:
            if not self.index_exists(index_name):
                return {"exists": False, "document_count": 0}

            stats = self._client.indices.stats(index=index_name)
            index_stats = stats["indices"][index_name]["total"]

            return {
                "exists": True,
                "document_count": index_stats["docs"]["count"],
                "deleted_count": index_stats["docs"]["deleted"],
                "size_in_bytes": index_stats["store"]["size_in_bytes"],
            }
        except Exception as e:
            logger.error("Failed to get index stats", index=index_name, error=str(e))
            return {"exists": False, "document_count": 0, "error": str(e)}

    # -- Search pipeline operations --

    def create_search_pipeline(
        self, pipeline_id: str, pipeline_body: dict[str, Any], force: bool = False
    ) -> bool:
        """Create a search pipeline (e.g. RRF for hybrid search). Returns True if created."""
        try:
            if force:
                try:
                    self._client.transport.perform_request(
                        "DELETE", f"/_search/pipeline/{pipeline_id}"
                    )
                    logger.info("Deleted existing pipeline", pipeline=pipeline_id)
                except Exception:
                    pass

            try:
                self._client.transport.perform_request("GET", f"/_search/pipeline/{pipeline_id}")
                logger.info("Pipeline already exists", pipeline=pipeline_id)
                return False
            except Exception:
                pass

            self._client.transport.perform_request(
                "PUT", f"/_search/pipeline/{pipeline_id}", body=pipeline_body
            )
            logger.info("Created search pipeline", pipeline=pipeline_id)
            return True

        except Exception as e:
            logger.error("Failed to create pipeline", pipeline=pipeline_id, error=str(e))
            raise

    # -- Document operations --

    def index_document(
        self, index_name: str, document: dict[str, Any], doc_id: str | None = None
    ) -> bool:
        """Index a single document. Returns True if successful."""
        try:
            kwargs: dict[str, Any] = {"index": index_name, "body": document, "refresh": True}
            if doc_id:
                kwargs["id"] = doc_id

            response = self._client.index(**kwargs)
            return response["result"] in ("created", "updated")
        except Exception as e:
            logger.error("Failed to index document", index=index_name, error=str(e))
            return False

    def bulk_index(self, index_name: str, documents: list[dict[str, Any]]) -> dict[str, int]:
        """Bulk index documents. Returns success/failed counts."""
        try:
            actions = [{"_index": index_name, "_source": doc} for doc in documents]
            success, failed = helpers.bulk(self._client, actions, refresh=True)

            logger.info(
                "Bulk index complete",
                index=index_name,
                success=success,
                failed=len(failed),
            )
            return {"success": success, "failed": len(failed)}
        except Exception as e:
            logger.error("Bulk index failed", index=index_name, error=str(e))
            raise

    def delete_by_query(self, index_name: str, query: dict[str, Any]) -> int:
        """Delete documents matching a query. Returns count deleted."""
        try:
            response = self._client.delete_by_query(
                index=index_name, body={"query": query}, refresh=True
            )
            deleted = response.get("deleted", 0)
            logger.info("Deleted documents", index=index_name, count=deleted)
            return deleted
        except Exception as e:
            logger.error("Delete by query failed", index=index_name, error=str(e))
            return 0

    # -- Search operations --

    def search(
        self,
        index_name: str,
        query_body: dict[str, Any],
        pipeline: str | None = None,
    ) -> dict[str, Any]:
        """Execute a search query. Returns hits and total count."""
        try:
            params = {}
            if pipeline:
                params["search_pipeline"] = pipeline

            response = self._client.search(index=index_name, body=query_body, params=params)

            hits = []
            for hit in response["hits"]["hits"]:
                doc = hit["_source"]
                doc["_score"] = hit["_score"]
                doc["_id"] = hit["_id"]
                if "highlight" in hit:
                    doc["_highlights"] = hit["highlight"]
                hits.append(doc)

            return {
                "total": response["hits"]["total"]["value"],
                "hits": hits,
            }
        except Exception as e:
            logger.error("Search failed", index=index_name, error=str(e))
            return {"total": 0, "hits": []}
