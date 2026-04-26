from src.config import ChunkingSettings
from src.services.chunking import chunk_text


def _settings(**overrides) -> ChunkingSettings:
    defaults = {"chunk_size": 10, "overlap_size": 3, "min_chunk_size": 4}
    defaults.update(overrides)
    return ChunkingSettings(**defaults)


class TestChunkText:
    def test_empty_string_returns_empty(self):
        assert chunk_text("", _settings()) == []

    def test_none_returns_empty(self):
        assert chunk_text(None, _settings()) == []

    def test_whitespace_only_returns_empty(self):
        assert chunk_text("   ", _settings()) == []

    def test_short_text_single_chunk(self):
        text = "one two three four five"
        chunks = chunk_text(text, _settings())

        assert len(chunks) == 1
        assert chunks[0]["chunk_index"] == 0
        assert chunks[0]["chunk_word_count"] == 5

    def test_exact_chunk_size_single_chunk(self):
        text = " ".join(f"word{i}" for i in range(10))
        chunks = chunk_text(text, _settings())

        assert len(chunks) == 1

    def test_splits_into_multiple_chunks(self):
        text = " ".join(f"word{i}" for i in range(25))
        chunks = chunk_text(text, _settings())

        assert len(chunks) > 1
        assert all(c["chunk_index"] == i for i, c in enumerate(chunks))

    def test_overlap_between_chunks(self):
        text = " ".join(f"w{i}" for i in range(25))
        settings = _settings(chunk_size=10, overlap_size=3)
        chunks = chunk_text(text, settings)

        first_words = set(chunks[0]["chunk_text"].split())
        second_words = set(chunks[1]["chunk_text"].split())
        overlap = first_words & second_words

        assert len(overlap) >= 3

    def test_short_trailing_fragment_merged(self):
        # 13 words with chunk_size=10, min_chunk_size=4
        # Second chunk would be 3 words (below min), so merged into first
        text = " ".join(f"w{i}" for i in range(13))
        settings = _settings(chunk_size=10, overlap_size=0, min_chunk_size=4)
        chunks = chunk_text(text, settings)

        assert len(chunks) == 1
        assert chunks[0]["chunk_word_count"] == 13

    def test_trailing_fragment_kept_if_above_min(self):
        # 15 words with chunk_size=10, min_chunk_size=4
        # Second chunk is 5 words (above min), kept separate
        text = " ".join(f"w{i}" for i in range(15))
        settings = _settings(chunk_size=10, overlap_size=0, min_chunk_size=4)
        chunks = chunk_text(text, settings)

        assert len(chunks) == 2
        assert chunks[1]["chunk_word_count"] == 5

    def test_chunk_word_counts_are_accurate(self):
        text = " ".join(f"w{i}" for i in range(30))
        chunks = chunk_text(text, _settings(chunk_size=10, overlap_size=2))

        for chunk in chunks:
            actual = len(chunk["chunk_text"].split())
            assert chunk["chunk_word_count"] == actual

    def test_real_world_settings(self):
        text = " ".join(f"word{i}" for i in range(1500))
        settings = ChunkingSettings(chunk_size=600, overlap_size=100, min_chunk_size=100)
        chunks = chunk_text(text, settings)

        assert len(chunks) == 3
        assert all(c["chunk_word_count"] >= 100 for c in chunks)
