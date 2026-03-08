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
