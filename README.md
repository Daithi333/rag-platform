# Content RAG Platform

A production-ready Retrieval-Augmented Generation (RAG) platform for ingesting, indexing, and querying technical content from multiple sources using hybrid search (BM25 + vector embeddings).

## Planned Features

- **Multi-source ingestion**: Dev.to articles, Stack Overflow Q&A, GitHub discussions
- **Hybrid search**: Combines BM25 keyword search with semantic vector embeddings
- **Airflow orchestration**: Scheduled daily ingestion pipelines with retry logic
- **OpenSearch indexing**: Scalable full-text and vector search with RRF ranking
- **FastAPI backend**: Modern async Python API with dependency injection
- **Structured logging**: Request tracing and observability with structlog
- **Production patterns**: Exception handling, testing, CI/CD ready

## Docker

```bash
docker compose up                                        # start api and db
docker compose exec api pytest -v                        # all run tests
docker compose exec api pytest tests/unit -v             # run unit tests
docker compose exec api pytest tests/api -v              # run api tests
docker compose exec api pytest tests/integration -v      # run integration tests (requires devto connectivity)
docker compose logs airflow-webserver | grep -i password # obtain Airflow admin password after 1st time init
docker compose down                                      # stop and remove containers
```

## Architecture

### Ingestion Pipeline (Airflow)

Articles are fetched daily from the Dev.to API, upserted into PostgreSQL with content-hash-based change detection, then chunked and indexed into OpenSearch. Only new or updated articles are indexed on each run.

The daily DAG flow:

```
setup_environment --> fetch_and_store_articles --+--> index_articles --> generate_daily_report
                 \--> setup_opensearch_index ----+
```

A separate manual backfill DAG allows indexing existing articles by date range.

### Search (OpenSearch)

Articles are split into ~600-word overlapping chunks and indexed into OpenSearch for full-text (BM25) and vector search. Hybrid search combines both using Reciprocal Rank Fusion (RRF).

See [docs/opensearch.md](docs/opensearch.md) for detailed configuration and mapping documentation.

### API (FastAPI)

Health endpoint checks liveness of PostgreSQL and OpenSearch. Services are initialised via a lifespan and injected into routes via FastAPI dependencies.

## Future Enhancements

- Weekly "deep refresh" DAG with higher `max_pages` to catch edits to older articles that the daily ingestion (capped at 50 pages per tag) would miss
- Additional data sources: Stack Overflow Q&A, GitHub discussions
- Langfuse tracing and Redis caching for production monitoring and performance
