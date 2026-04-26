"""Index mappings and search pipeline definitions.

Each content source defines its own mapping. The OpenSearch client
is generic and accepts these as parameters.
"""

from src.config import OpenSearchSettings


def get_chunk_index_name(settings: OpenSearchSettings) -> str:
    return f"{settings.index_name}-{settings.chunk_index_suffix}"


DEVTO_CHUNKS_MAPPING = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "index.knn": True,
        "index.knn.space_type": "cosinesimil",
        "analysis": {
            "analyzer": {
                "text_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "stop", "snowball"],
                },
            }
        },
    },
    "mappings": {
        "dynamic": "strict",
        "properties": {
            "chunk_id": {"type": "keyword"},
            "article_id": {"type": "keyword"},
            "source_id": {"type": "keyword"},
            "chunk_index": {"type": "integer"},
            "chunk_text": {
                "type": "text",
                "analyzer": "text_analyzer",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "chunk_word_count": {"type": "integer"},
            "embedding": {
                "type": "knn_vector",
                "dimension": 1024,
                "method": {
                    "name": "hnsw",
                    "space_type": "cosinesimil",
                    "engine": "nmslib",
                    "parameters": {
                        "ef_construction": 512,
                        "m": 16,
                    },
                },
            },
            "title": {
                "type": "text",
                "analyzer": "text_analyzer",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "description": {"type": "text", "analyzer": "text_analyzer"},
            "author": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "tags": {"type": "keyword"},
            "url": {"type": "keyword"},
            "published_date": {"type": "date"},
            "embedding_model": {"type": "keyword"},
            "created_at": {"type": "date"},
        },
    },
}


HYBRID_RRF_PIPELINE = {
    "description": "Post processor for hybrid RRF search",
    "phase_results_processors": [
        {
            "score-ranker-processor": {
                "combination": {
                    "technique": "rrf",
                    "rank_constant": 60,
                }
            }
        }
    ],
}
