"""RAG prompt construction."""

from src.schemas.api.search import ChunkHit

SYSTEM_PROMPT = """You are an AI assistant that answers questions about software development articles. Base your answer STRICTLY on the provided article excerpts.

Instructions:
1. Answer based ONLY on the provided excerpts
2. If the excerpts don't contain enough information, say so clearly
3. Cite sources by title when providing information
4. Be concise - limit your response to 300 words maximum
5. If multiple articles discuss the topic, synthesise the information
6. Use direct quotes when particularly relevant
7. Do NOT make up information not present in the excerpts
8. Acknowledge uncertainty when excerpts are ambiguous"""


def build_rag_prompt(query: str, chunks: list[ChunkHit]) -> str:
    """Build a RAG prompt from a query and retrieved chunks."""
    context_parts = []

    for i, chunk in enumerate(chunks, 1):
        source = f"[{i}. {chunk.title}]"
        context_parts.append(f"{source}\n{chunk.chunk_text}\n")

    context = "\n".join(context_parts)

    return f"""{SYSTEM_PROMPT}

### Context from Articles:

{context}

### Question:
{query}

### Answer:"""
