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
