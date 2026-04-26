"""Text chunking with word-based splitting and overlap."""

from src.config import ChunkingSettings


def chunk_text(
    text: str,
    settings: ChunkingSettings,
) -> list[dict]:
    """Split text into overlapping word-based chunks.

    Returns a list of dicts with chunk_text, chunk_index, and chunk_word_count.
    """
    if not text or not text.strip():
        return []

    words = text.split()

    if len(words) <= settings.chunk_size:
        return [
            {
                "chunk_text": text.strip(),
                "chunk_index": 0,
                "chunk_word_count": len(words),
            }
        ]

    chunks = []
    start = 0
    chunk_index = 0

    while start < len(words):
        end = start + settings.chunk_size
        chunk_words = words[start:end]

        if len(chunk_words) < settings.min_chunk_size and chunks:
            prev = chunks[-1]
            prev["chunk_text"] += " " + " ".join(chunk_words)
            prev["chunk_word_count"] = len(prev["chunk_text"].split())
            break

        chunks.append(
            {
                "chunk_text": " ".join(chunk_words),
                "chunk_index": chunk_index,
                "chunk_word_count": len(chunk_words),
            }
        )

        chunk_index += 1
        start = end - settings.overlap_size

    return chunks
