# OpenSearch

## Overview

A fork of Elasticsearch 7.10 (from when Elastic changed their license in 2021). AWS led the fork, now maintained by the OpenSearch community under Apache 2.0. It is a distributed search and analytics engine built on Apache Lucene.

## Architecture

- Cluster of nodes, each holding shards (partitions) of an index
- Documents are JSON objects stored in indices (like tables in a DB)
- Each index has a mapping (schema) defining field types and how they are analysed
- Shards can be primary or replica for redundancy
- For a single-node dev setup, 1 shard and 0 replicas is fine -- no need for distribution

## Configuration

| Setting | Description |
|---|---|
| `host` | Cluster address. In Docker: `http://opensearch:9200` |
| `index_name` | Base name for the index (`devto-articles`) |
| `chunk_index_suffix` | Appended to form the actual index name (`devto-articles-chunks`) |
| `vector_dimension` | Size of embedding vectors. Jina v3 produces 1024-dim vectors |
| `vector_space_type` | Similarity metric. Cosine similarity is standard for text embeddings |
| `rrf_pipeline_name` | RRF pipeline for hybrid search. Combines BM25 and vector scores without manual weight tuning |
| `hybrid_search_size_multiplier` | Fetch N x results from each search method before RRF merges, for better recall |

## Search Modes

### BM25 (keyword search)
Classic full-text search. Lucene tokenises text, builds an inverted index, scores by term frequency / inverse document frequency. Good for exact matches, specific terms, code snippets.

### Vector (semantic search)
Embed the query and find nearest neighbours in vector space using the HNSW algorithm. Good for conceptual similarity -- "how to handle errors in Python" matches articles about exception handling even without those exact words.

### Hybrid (BM25 + vector with RRF)
Run both searches, merge with Reciprocal Rank Fusion. BM25 catches exact matches that vectors miss, vectors catch semantic matches that keywords miss. This is the end goal.

## Why Chunking Matters

A 2000-word article is too long to embed as a single vector -- the meaning gets diluted. Splitting into ~500-word chunks and embedding each separately means search returns the most relevant sections, not whole articles. Each chunk carries metadata (article ID, title, tags) so results trace back to the source.

One article becomes 4-5 chunk documents in OpenSearch. The index name `devto-articles-chunks` distinguishes chunk documents from any future whole-article index (`devto-articles`).

## Index Mapping

### Settings

```json
{
  "number_of_shards": 1,
  "number_of_replicas": 0,
  "index.knn": true,
  "index.knn.space_type": "cosinesimil"
}
```

Shards and replicas are distribution concerns. Single shard, zero replicas is correct for a single-node dev setup. In production, increase both.

### Text Analyser

```json
{
  "text_analyzer": {
    "type": "custom",
    "tokenizer": "standard",
    "filter": ["lowercase", "stop", "snowball"]
  }
}
```

The text processing pipeline for BM25 search. Both indexed documents and queries go through the same analyser so terms match:

- `standard` tokenizer: splits on whitespace and punctuation
- `lowercase`: "Python" becomes "python"
- `stop`: removes common words ("the", "is", "a")
- `snowball`: stemming -- "running" becomes "run", "containers" matches "container"

### Field Types

#### Keyword fields (exact match, no analysis)

| Field | Purpose |
|---|---|
| `chunk_id` | Unique chunk identifier |
| `article_id` | Links chunk back to the source article (UUID) |
| `source_id` | The Dev.to article ID |
| `tags` | Filterable tags |
| `url` | Article URL |

#### Text fields (full-text searchable via analyser)

| Field | Purpose |
|---|---|
| `chunk_text` | The chunk content, primary search target |
| `title` | Article title, boosted in queries |
| `description` | Article description |
| `author` | Author name |

Text fields also have a `.keyword` sub-field for exact-match aggregations. `ignore_above: 256` skips the keyword version for long values.

#### Other fields

| Field | Type | Purpose |
|---|---|---|
| `chunk_index` | `integer` | Position within the article (0, 1, 2...) |
| `chunk_word_count` | `integer` | Word count for the chunk |
| `published_date` | `date` | Article publication date |
| `embedding_model` | `keyword` | Which model generated the embedding |
| `created_at` | `date` | When the chunk was indexed |

### Vector Field (knn_vector)

```json
{
  "embedding": {
    "type": "knn_vector",
    "dimension": 1024,
    "method": {
      "name": "hnsw",
      "space_type": "cosinesimil",
      "engine": "nmslib",
      "parameters": {
        "ef_construction": 512,
        "m": 16
      }
    }
  }
}
```

- `dimension`: must match the embedding model output (Jina v3 = 1024)
- `hnsw`: Hierarchical Navigable Small World -- an approximate nearest-neighbour algorithm
- `ef_construction`: build-time quality (higher = better recall, slower indexing)
- `m`: graph connectivity (higher = more memory, better recall)

HNSW builds a graph structure at index time for fast approximate lookups at query time. The tradeoff is index speed and memory vs search recall. These are reasonable defaults from the reference implementation.

## RRF Pipeline

```json
{
  "phase_results_processors": [{
    "score-ranker-processor": {
      "combination": {
        "technique": "rrf",
        "rank_constant": 60
      }
    }
  }]
}
```

When running a hybrid query, OpenSearch executes BM25 and vector searches independently, then RRF merges the results. For each document it computes:

```
score = 1/(k + bm25_rank) + 1/(k + vector_rank)
```

Documents that rank well in both searches bubble to the top. The constant `k=60` is the standard default -- it dampens the influence of very high ranks so a document that is #1 in BM25 but #50 in vector does not dominate.

## Competitors

| Engine | License | Vector Search | Managed Offering |
|---|---|---|---|
| Elasticsearch | Elastic License (not OSS) | Yes (since 8.x) | Elastic Cloud |
| OpenSearch | Apache 2.0 | Yes (k-NN plugin) | AWS OpenSearch Service |
| Meilisearch | MIT | Experimental | Meilisearch Cloud |
| Typesense | GPL-3 | Yes | Typesense Cloud |
| Weaviate | BSD-3 | Native (vector-first) | Weaviate Cloud |
| Pinecone | Proprietary | Native (vector-only) | SaaS only |
| Qdrant | Apache 2.0 | Native (vector-only) | Qdrant Cloud |
| pgvector | PostgreSQL License | Yes (extension) | Any managed PG |

OpenSearch is a good fit here because it supports both keyword and vector search natively with hybrid RRF, is self-hosted and open source, and has mature full-text analysis capabilities that pure vector databases lack.
