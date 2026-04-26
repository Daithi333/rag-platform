# Chunking and Embeddings

## Chunking Strategies

### Fixed-size (current approach)
Split by word count with overlap. Simple, works well for unstructured prose like blog articles. Blind to document structure -- will split a code block in half.

### Section/heading-based
Split on markdown headings, HTML sections, or document structure. Each section becomes a chunk. Good for well-structured content like documentation, tutorials, or compliance benchmarks where each control is a self-contained unit.

### Semantic
Use an LLM or sentence embeddings to detect topic shifts and split there. More expensive but produces the most coherent chunks. LangChain provides `SemanticChunker` for this.

### Recursive
Try to split by paragraphs first, then sentences, then words. Respects natural boundaries where possible, falls back to smaller units when a paragraph is too long. LangChain's `RecursiveCharacterTextSplitter` is the common implementation.

### Domain-specific
For structured documents (CIS benchmarks, API specs, legal contracts), parse the document format and extract each logical unit as its own chunk with structured metadata. The chunking is really parsing at that point.

## Current Configuration

| Setting | Value | Rationale |
|---|---|---|
| `chunk_size` | 600 words | Roughly a page of text. Large enough for a coherent idea, small enough for a focused embedding. Well within Jina v3's 8192 token limit. |
| `overlap_size` | 100 words | Prevents concepts at chunk boundaries from being split. ~17% storage overhead. |
| `min_chunk_size` | 100 words | Short trailing fragments get merged into the previous chunk rather than indexed separately. |

## Evaluating Retrieval Quality

Metrics for measuring whether search returns the right chunks:

| Metric | What it measures |
|---|---|
| Precision@k | Of the top k results, how many are actually relevant? |
| Recall@k | Of all relevant chunks in the index, how many appeared in the top k? |
| MRR (Mean Reciprocal Rank) | How far down the results list is the first relevant hit? |
| NDCG (Normalised Discounted Cumulative Gain) | Are the most relevant results ranked highest? |

These require labelled data -- a set of queries with known-good answers. Can be built manually or generated synthetically using an LLM to create question-answer pairs from articles.

## Evaluating Chunk Quality

| Signal | What to look for |
|---|---|
| Size distribution | Are chunks consistently sized or wildly variable? |
| Semantic coherence | Embed each chunk and measure intra-chunk similarity. Low coherence suggests the chunk spans multiple topics. |
| Boundary quality | Do chunks start/end mid-sentence or mid-thought? Spot-check or use an LLM to score. |

## Evaluating Embedding Quality

| Signal | What to look for |
|---|---|
| Nearest-neighbour sanity | Embed a query, check top results. Do they make sense? |
| Similarity distribution | If all chunks have very similar embeddings, the model is not differentiating. If all very different, it may not capture shared concepts. |
| A/B comparison | Try two models, run the same queries, compare retrieval metrics. |

## End-to-End RAG Quality

| Metric | What it measures |
|---|---|
| Faithfulness | Does the generated answer reflect what the retrieved chunks say? (Not hallucinated) |
| Relevance | Does the answer address the question? |
| Context relevance | Were the retrieved chunks actually useful for answering? |

## Tooling

| Tool | Purpose |
|---|---|
| Langfuse | Traces the full RAG pipeline: query, retrieval, generation. See which chunks were retrieved, what the LLM saw, what it produced. Good for debugging individual queries. |
| RAGAS | Open-source RAG evaluation framework. Computes faithfulness, answer relevance, context precision/recall using an LLM as judge. |
| DeepEval | Similar to RAGAS with additional metrics and a dashboard. |
| OpenSearch Dashboards | Already running in the stack. Inspect index stats, run test queries, eyeball results. |

## Suggested Evaluation Path

1. Start with manual spot-checks in OpenSearch Dashboards
2. Add Langfuse tracing when the RAG pipeline is built
3. Consider RAGAS for systematic comparison of chunking strategies or embedding models
