from __future__ import annotations

import io

import pdfplumber
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


def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    words = text.split()
    chunks, start = [], 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append(" ".join(words[start:end]))
        start += chunk_size - overlap
    return chunks


async def ingest_policy_pdf(file_bytes: bytes, filename: str, policy_id: str) -> int:
    await ensure_collection()
    client = get_client()
    embedder = get_embedder()

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        full_text = "\n".join(page.extract_text() or "" for page in pdf.pages)

    chunks = _chunk_text(full_text)
    vectors = embedder.encode(chunks).tolist()

    points = [
        PointStruct(
            id=f"{policy_id}_{i}",
            vector=vec,
            payload={"policy_id": policy_id, "text": chunk, "filename": filename},
        )
        for i, (chunk, vec) in enumerate(zip(chunks, vectors))
    ]

    await client.upsert(collection_name=settings.QDRANT_COLLECTION_NAME, points=points)
    logger.info("Policy ingested", policy_id=policy_id, chunks=len(points))
    return len(points)


async def delete_policy_vectors(policy_id: str) -> int:
    client = get_client()
    await client.delete(
        collection_name=settings.QDRANT_COLLECTION_NAME,
        points_selector=Filter(
            must=[FieldCondition(key="policy_id", match=MatchValue(value=policy_id))]
        ),
    )
    logger.info("Vectors deleted", policy_id=policy_id)
    # Exact deleted count returned in Phase 2 via scroll-before-delete pattern
    return 0


async def search_policies(user_profile: dict, top_k: int = 5) -> list[dict]:
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
        {"text": r.payload["text"], "score": r.score, "policy_id": r.payload["policy_id"]}
        for r in results
    ]


async def check_qdrant() -> bool:
    try:
        await get_client().get_collections()
        return True
    except Exception:
        return False
