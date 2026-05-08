from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ContextChunk:
    index: int          # 1-based label used in LLM citations [N]
    policy_id: str
    policy_name: str
    insurer: str
    chunk_index: int    # position within the source document
    text: str
    score: float        # retrieval similarity score


def build_numbered_context(
    raw_chunks: list[dict],
) -> tuple[list[ContextChunk], str]:
    """Deduplicate, rank, and format raw Qdrant results for the LLM prompt.

    Returns:
        chunks  — ContextChunk list (1-indexed) used for post-generation validation
        context_str — formatted string injected into the LLM prompt

    Deduplication key: (policy_id, chunk_index).
    A chunk retrieved by multiple queries appears once (highest score kept).
    """
    # Keep the highest-scoring occurrence of each (policy_id, chunk_index) pair
    best: dict[tuple[str, int], dict] = {}
    for c in raw_chunks:
        key = (c["policy_id"], c.get("chunk_index", 0))
        if key not in best or c["score"] > best[key]["score"]:
            best[key] = c

    ranked = sorted(best.values(), key=lambda x: x["score"], reverse=True)

    chunks = [
        ContextChunk(
            index=i + 1,
            policy_id=c["policy_id"],
            policy_name=c.get("policy_name", "Unknown Policy"),
            insurer=c.get("insurer", "Unknown Insurer"),
            chunk_index=c.get("chunk_index", 0),
            text=c["text"],
            score=c["score"],
        )
        for i, c in enumerate(ranked)
    ]

    # Build the numbered context string injected into the LLM prompt
    parts = [
        f"[{ch.index}] {ch.policy_name} | {ch.insurer}\n{ch.text.strip()}"
        for ch in chunks
    ]
    context_str = "\n\n---\n\n".join(parts)

    return chunks, context_str


def resolve_policy_id(policy_name: str, chunks: list[ContextChunk]) -> str:
    """Map a policy_name (as the LLM knows it) back to its UUID policy_id."""
    for ch in chunks:
        if ch.policy_name.lower() == policy_name.lower():
            return ch.policy_id
    return "unknown"
