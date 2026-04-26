from unittest.mock import MagicMock, patch

import pytest

from src.config import OpenSearchSettings
from src.services.opensearch.client import OpenSearchClient


@pytest.fixture
def settings():
    return OpenSearchSettings(host="http://localhost:9200")


@pytest.fixture
def client(settings):
    with patch("src.services.opensearch.client.OpenSearch") as mock_os:
        mock_instance = MagicMock()
        mock_os.return_value = mock_instance
        os_client = OpenSearchClient(settings=settings)
        os_client._mock = mock_instance
        yield os_client


class TestHealthCheck:
    def test_healthy_green(self, client):
        client._mock.cluster.health.return_value = {"status": "green"}
        result = client.health_check()
        assert result["healthy"] is True
        assert result["status"] == "green"

    def test_healthy_yellow(self, client):
        client._mock.cluster.health.return_value = {"status": "yellow"}
        result = client.health_check()
        assert result["healthy"] is True

    def test_unhealthy_red(self, client):
        client._mock.cluster.health.return_value = {"status": "red"}
        result = client.health_check()
        assert result["healthy"] is False

    def test_unreachable(self, client):
        client._mock.cluster.health.side_effect = Exception("refused")
        result = client.health_check()
        assert result["healthy"] is False
        assert result["status"] == "unreachable"
        assert "refused" in result["error"]


class TestCreateIndex:
    def test_creates_when_not_exists(self, client):
        client._mock.indices.exists.return_value = False
        client._mock.indices.create.return_value = {"acknowledged": True}

        assert client.create_index("test-idx", {"mappings": {}}) is True
        client._mock.indices.create.assert_called_once()

    def test_skips_when_exists(self, client):
        client._mock.indices.exists.return_value = True

        assert client.create_index("test-idx", {"mappings": {}}) is False
        client._mock.indices.create.assert_not_called()

    def test_force_deletes_then_creates(self, client):
        client._mock.indices.exists.side_effect = [True, False]
        client._mock.indices.create.return_value = {"acknowledged": True}

        assert client.create_index("test-idx", {"mappings": {}}, force=True) is True
        client._mock.indices.delete.assert_called_once_with(index="test-idx")
        client._mock.indices.create.assert_called_once()

    def test_race_condition_handled(self, client):
        client._mock.indices.exists.return_value = False
        client._mock.indices.create.side_effect = Exception("resource_already_exists_exception")

        assert client.create_index("test-idx", {"mappings": {}}) is False


class TestGetIndexStats:
    def test_returns_stats(self, client):
        client._mock.indices.exists.return_value = True
        client._mock.indices.stats.return_value = {
            "indices": {
                "test-idx": {
                    "total": {
                        "docs": {"count": 100, "deleted": 5},
                        "store": {"size_in_bytes": 50000},
                    }
                }
            }
        }

        stats = client.get_index_stats("test-idx")

        assert stats["exists"] is True
        assert stats["document_count"] == 100
        assert stats["size_in_bytes"] == 50000

    def test_not_exists(self, client):
        client._mock.indices.exists.return_value = False

        stats = client.get_index_stats("test-idx")

        assert stats["exists"] is False
        assert stats["document_count"] == 0


class TestIndexDocument:
    def test_success(self, client):
        client._mock.index.return_value = {"result": "created"}

        assert client.index_document("test-idx", {"title": "test"}) is True

    def test_with_doc_id(self, client):
        client._mock.index.return_value = {"result": "updated"}

        assert client.index_document("test-idx", {"title": "test"}, doc_id="123") is True
        call_kwargs = client._mock.index.call_args[1]
        assert call_kwargs["id"] == "123"

    def test_failure_returns_false(self, client):
        client._mock.index.side_effect = Exception("indexing error")

        assert client.index_document("test-idx", {"title": "test"}) is False


class TestBulkIndex:
    def test_success(self, client):
        with patch("src.services.opensearch.client.helpers") as mock_helpers:
            mock_helpers.bulk.return_value = (10, [])

            result = client.bulk_index("test-idx", [{"title": "a"}] * 10)

            assert result == {"success": 10, "failed": 0}

    def test_with_failures(self, client):
        with patch("src.services.opensearch.client.helpers") as mock_helpers:
            mock_helpers.bulk.return_value = (8, [{"error": "x"}, {"error": "y"}])

            result = client.bulk_index("test-idx", [{"title": "a"}] * 10)

            assert result == {"success": 8, "failed": 2}

    def test_raises_on_error(self, client):
        with patch("src.services.opensearch.client.helpers") as mock_helpers:
            mock_helpers.bulk.side_effect = Exception("bulk error")

            with pytest.raises(Exception, match="bulk error"):
                client.bulk_index("test-idx", [{"title": "a"}])


class TestDeleteByQuery:
    def test_returns_deleted_count(self, client):
        client._mock.delete_by_query.return_value = {"deleted": 5}

        assert client.delete_by_query("test-idx", {"term": {"id": "1"}}) == 5

    def test_error_returns_zero(self, client):
        client._mock.delete_by_query.side_effect = Exception("delete error")

        assert client.delete_by_query("test-idx", {"term": {"id": "1"}}) == 0


class TestSearch:
    def test_returns_hits(self, client):
        client._mock.search.return_value = {
            "hits": {
                "total": {"value": 2},
                "hits": [
                    {"_id": "1", "_score": 1.5, "_source": {"title": "A"}},
                    {"_id": "2", "_score": 1.2, "_source": {"title": "B"}},
                ],
            }
        }

        result = client.search("test-idx", {"query": {"match_all": {}}})

        assert result["total"] == 2
        assert len(result["hits"]) == 2
        assert result["hits"][0]["_score"] == 1.5
        assert result["hits"][0]["_id"] == "1"

    def test_includes_highlights(self, client):
        client._mock.search.return_value = {
            "hits": {
                "total": {"value": 1},
                "hits": [
                    {
                        "_id": "1",
                        "_score": 1.0,
                        "_source": {"title": "A"},
                        "highlight": {"title": ["<mark>A</mark>"]},
                    }
                ],
            }
        }

        result = client.search("test-idx", {"query": {}})

        assert "_highlights" in result["hits"][0]

    def test_with_pipeline(self, client):
        client._mock.search.return_value = {"hits": {"total": {"value": 0}, "hits": []}}

        client.search("test-idx", {"query": {}}, pipeline="my-pipeline")

        call_kwargs = client._mock.search.call_args[1]
        assert call_kwargs["params"]["search_pipeline"] == "my-pipeline"

    def test_error_returns_empty(self, client):
        client._mock.search.side_effect = Exception("search error")

        result = client.search("test-idx", {"query": {}})

        assert result["total"] == 0
        assert result["hits"] == []
