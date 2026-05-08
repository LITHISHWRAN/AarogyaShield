from __future__ import annotations

import re
from dataclasses import dataclass

# Split on sentence endings followed by whitespace, preserving the delimiter context.
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")


@dataclass(frozen=True)
class Chunk:
    text: str
    chunk_index: int
    char_start: int   # approximate char offset in cleaned source text
    char_end: int     # approximate char offset end
    token_count: int  # word count (proxy for token count)


def chunk_text(
    text: str,
    max_words: int = 400,
    overlap_words: int = 40,
) -> list[Chunk]:
    """Split text into sentence-aware, overlapping chunks.

    Sentence-awareness: the splitter never cuts mid-sentence, preserving
    complete thoughts per chunk so embeddings capture full semantic units.

    Overlap: the last `overlap_words` words of chunk N become the first words
    of chunk N+1. This ensures cross-boundary context is not lost for queries
    that fall near a chunk seam.

    char_start / char_end are approximate positions in the cleaned source text,
    useful for future "highlight source" / citation features. They point to the
    start of the first sentence that belongs exclusively to this chunk (not
    carried-over overlap), making them semantically meaningful for navigation.
    """
    sentences = [s.strip() for s in _SENTENCE_BOUNDARY.split(text) if s.strip()]

    chunks: list[Chunk] = []
    window: list[str] = []
    anchor_char: int = 0   # char pos of the first sentence added to this window
    search_from: int = 0   # advancing cursor for position lookups

    for sentence in sentences:
        # Find where this sentence actually starts in the source
        pos = text.find(sentence, search_from)
        sent_start = pos if pos >= 0 else search_from
        search_from = sent_start + len(sentence)

        words = sentence.split()
        if not words:
            continue

        if window and len(window) + len(words) > max_words:
            _emit(chunks, window, anchor_char)
            window = window[-overlap_words:] if len(window) > overlap_words else window[:]
            anchor_char = sent_start
        elif not window:
            anchor_char = sent_start

        window.extend(words)

    if window:
        _emit(chunks, window, anchor_char)

    return chunks


def _emit(chunks: list[Chunk], words: list[str], anchor_char: int) -> None:
    chunk_str = " ".join(words)
    chunks.append(
        Chunk(
            text=chunk_str,
            chunk_index=len(chunks),
            char_start=anchor_char,
            char_end=anchor_char + len(chunk_str),
            token_count=len(words),
        )
    )
