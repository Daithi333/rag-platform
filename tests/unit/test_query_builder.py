from src.services.opensearch.query_builder import QueryBuilder


class TestBuildBM25:
    def test_basic_query_structure(self):
        qb = QueryBuilder(query="python errors")
        body = qb.build_bm25()

        assert body["size"] == 10
        assert body["from"] == 0
        assert body["track_total_hits"] is True
        assert "embedding" in body["_source"]["excludes"]

    def test_text_query_with_boosting(self):
        qb = QueryBuilder(query="python errors")
        body = qb.build_bm25()

        text_query = body["query"]["bool"]["must"][0]["multi_match"]
        assert text_query["query"] == "python errors"
        assert "chunk_text^3" in text_query["fields"]
        assert "title^2" in text_query["fields"]
        assert text_query["fuzziness"] == "AUTO"

    def test_empty_query_uses_match_all(self):
        qb = QueryBuilder(query="")
        body = qb.build_bm25()

        must = body["query"]["bool"]["must"]
        assert must == [{"match_all": {}}]

    def test_tag_filter(self):
        qb = QueryBuilder(query="python", tags=["python", "webdev"])
        body = qb.build_bm25()

        filters = body["query"]["bool"]["filter"]
        assert {"terms": {"tags": ["python", "webdev"]}} in filters

    def test_no_filter_when_no_tags(self):
        qb = QueryBuilder(query="python")
        body = qb.build_bm25()

        assert "filter" not in body["query"]["bool"]

    def test_pagination(self):
        qb = QueryBuilder(query="python", size=5, from_=20)
        body = qb.build_bm25()

        assert body["size"] == 5
        assert body["from"] == 20

    def test_sort_by_relevance_when_query_present(self):
        qb = QueryBuilder(query="python")
        body = qb.build_bm25()

        assert "sort" not in body

    def test_sort_by_date_when_requested(self):
        qb = QueryBuilder(query="python", sort_by_date=True)
        body = qb.build_bm25()

        assert body["sort"][0] == {"published_date": {"order": "desc"}}

    def test_sort_by_date_when_empty_query(self):
        qb = QueryBuilder(query="")
        body = qb.build_bm25()

        assert body["sort"][0] == {"published_date": {"order": "desc"}}

    def test_highlight_config(self):
        qb = QueryBuilder(query="python")
        body = qb.build_bm25()

        highlight = body["highlight"]
        assert "chunk_text" in highlight["fields"]
        assert "title" in highlight["fields"]
        assert highlight["require_field_match"] is False

    def test_custom_fields(self):
        qb = QueryBuilder(query="python", fields=["title^5", "author^1"])
        body = qb.build_bm25()

        fields = body["query"]["bool"]["must"][0]["multi_match"]["fields"]
        assert fields == ["title^5", "author^1"]


class TestBuildVector:
    def test_basic_structure(self):
        qb = QueryBuilder(query="python")
        embedding = [0.1] * 1024
        body = qb.build_vector(embedding)

        assert body["size"] == 10
        assert "embedding" in body["_source"]["excludes"]

    def test_knn_query(self):
        qb = QueryBuilder(query="python")
        embedding = [0.1] * 1024
        body = qb.build_vector(embedding)

        knn = body["query"]["knn"]["embedding"]
        assert knn["vector"] == embedding
        assert knn["k"] == 10

    def test_with_tag_filter(self):
        qb = QueryBuilder(query="python", tags=["python"])
        embedding = [0.1] * 1024
        body = qb.build_vector(embedding)

        assert "bool" in body["query"]
        filters = body["query"]["bool"]["filter"]
        assert {"terms": {"tags": ["python"]}} in filters


class TestBuildHybrid:
    def test_basic_structure(self):
        qb = QueryBuilder(query="python")
        embedding = [0.1] * 1024
        body = qb.build_hybrid(embedding)

        queries = body["query"]["hybrid"]["queries"]
        assert len(queries) == 2

    def test_contains_bm25_and_knn(self):
        qb = QueryBuilder(query="python")
        embedding = [0.1] * 1024
        body = qb.build_hybrid(embedding)

        queries = body["query"]["hybrid"]["queries"]
        assert "bool" in queries[0]
        assert "knn" in queries[1]

    def test_size_multiplier(self):
        qb = QueryBuilder(query="python", size=10)
        embedding = [0.1] * 1024
        body = qb.build_hybrid(embedding, size_multiplier=3)

        knn = body["query"]["hybrid"]["queries"][1]
        assert knn["knn"]["embedding"]["k"] == 30

    def test_includes_highlight(self):
        qb = QueryBuilder(query="python")
        embedding = [0.1] * 1024
        body = qb.build_hybrid(embedding)

        assert "highlight" in body
