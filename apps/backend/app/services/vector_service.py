from __future__ import annotations

import uuid

import structlog
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)
from sentence_transformers import SentenceTransformer

from app.core.config import settings
from app.ingestion.chunker import Chunk

logger = structlog.get_logger()

_client: AsyncQdrantClient | None = None
_embedder: SentenceTransformer | None = None


def get_client() -> AsyncQdrantClient:
    global _client
    if _client is None:
        _client = AsyncQdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
    return _client


def get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(settings.EMBEDDING_MODEL)
    return _embedder


async def ensure_collection() -> None:
    client = get_client()
    existing = await client.get_collections()
    names = [c.name for c in existing.collections]
    if settings.QDRANT_COLLECTION_NAME not in names:
        await client.create_collection(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            vectors_config=VectorParams(
                size=settings.EMBEDDING_DIMENSION,
                distance=Distance.COSINE,
            ),
        )
        logger.info("Qdrant collection created", name=settings.QDRANT_COLLECTION_NAME)


async def store_policy_chunks(
    chunks: list[Chunk],
    *,
    policy_id: str,
    policy_name: str,
    insurer: str,
    file_type: str,
    source_document_id: str,
) -> int:
    """Embed a list of Chunk objects and upsert them into Qdrant.

    Each point carries full metadata so RAG results are self-contained —
    no secondary DB lookup is needed for citation at query time.
    """
    await ensure_collection()
    client = get_client()
    embedder = get_embedder()

    texts = [c.text for c in chunks]
    vectors = embedder.encode(texts).tolist()

    points = [
        PointStruct(
            id=str(uuid.uuid4()),   # globally unique per chunk
            vector=vec,
            payload={
                "policy_id": policy_id,
                "policy_name": policy_name,
                "insurer": insurer,
                "file_type": file_type,
                "source_document_id": source_document_id,
                "chunk_index": chunk.chunk_index,
                "char_start": chunk.char_start,
                "char_end": chunk.char_end,
                "text": chunk.text,
            },
        )
        for chunk, vec in zip(chunks, vectors)
    ]

    await client.upsert(collection_name=settings.QDRANT_COLLECTION_NAME, points=points)
    logger.info("Chunks stored in Qdrant", policy_id=policy_id, count=len(points))
    return len(points)


async def delete_policy_vectors(policy_id: str) -> int:
    """Scroll-then-delete to get an accurate removed-vector count.

    Vectors are deleted before the caller removes the DB record.
    If the DB delete later fails, orphaned metadata is recoverable;
    ghost vectors serving wrong results are not.
    """
    client = get_client()
    policy_filter = Filter(
        must=[FieldCondition(key="policy_id", match=MatchValue(value=policy_id))]
    )

    # Count first via paginated scroll (no payload/vectors needed)
    count = 0
    next_offset = None
    while True:
        records, next_offset = await client.scroll(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            scroll_filter=policy_filter,
            limit=100,
            offset=next_offset,
            with_payload=False,
            with_vectors=False,
        )
        count += len(records)
        if next_offset is None:
            break

    await client.delete(
        collection_name=settings.QDRANT_COLLECTION_NAME,
        points_selector=policy_filter,
    )
    logger.info("Vectors deleted", policy_id=policy_id, count=count)
    return count


async def search_with_query(query: str, top_k: int = 5) -> list[dict]:
    """Semantic search with a plain string query.

    Used by the multi-query retrieval step where each query targets a specific
    concern (coverage, exclusions, premium) rather than joining profile values.
    """
    client = get_client()
    embedder = get_embedder()
    vector = embedder.encode([query])[0].tolist()
    results = await client.search(
        collection_name=settings.QDRANT_COLLECTION_NAME,
        query_vector=vector,
        limit=top_k,
        with_payload=True,
    )
    return [
        {
            "text": r.payload["text"],
            "score": r.score,
            "policy_id": r.payload["policy_id"],
            "policy_name": r.payload.get("policy_name", ""),
            "insurer": r.payload.get("insurer", ""),
            "chunk_index": r.payload.get("chunk_index", 0),
            "source_document_id": r.payload.get("source_document_id", ""),
        }
        for r in results
    ]


async def search_policies(user_profile: dict, top_k: int = 5) -> list[dict]:
    """Semantic search over policy chunks.

    Returns rich payloads so the LLM can cite policy name, insurer,
    and chunk position without any secondary lookups.
    """
    client = get_client()
    embedder = get_embedder()

    query = " ".join(str(v) for v in user_profile.values())
    vector = embedder.encode([query])[0].tolist()

    results = await client.search(
        collection_name=settings.QDRANT_COLLECTION_NAME,
        query_vector=vector,
        limit=top_k,
        with_payload=True,
    )
    return [
        {
            "text": r.payload["text"],
            "score": r.score,
            "policy_id": r.payload["policy_id"],
            "policy_name": r.payload.get("policy_name", ""),
            "insurer": r.payload.get("insurer", ""),
            "chunk_index": r.payload.get("chunk_index", 0),
            "source_document_id": r.payload.get("source_document_id", ""),
        }
        for r in results
    ]


async def check_qdrant() -> bool:
    try:
        await get_client().get_collections()
        return True
    except Exception:
        return False
