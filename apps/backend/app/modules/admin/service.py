import structlog

from app.services.vector_service import delete_policy_vectors, ingest_policy_pdf

logger = structlog.get_logger()


async def upload_policy(file_bytes: bytes, filename: str, policy_id: str) -> dict:
    chunks_indexed = await ingest_policy_pdf(
        file_bytes=file_bytes,
        filename=filename,
        policy_id=policy_id,
    )
    logger.info("Policy uploaded", policy_id=policy_id, chunks=chunks_indexed)
    return {
        "policy_id": policy_id,
        "chunks_indexed": chunks_indexed,
        "message": "Indexed successfully",
    }


async def delete_policy(policy_id: str) -> dict:
    vectors_removed = await delete_policy_vectors(policy_id=policy_id)
    logger.info("Policy deleted", policy_id=policy_id, vectors_removed=vectors_removed)
    return {
        "policy_id": policy_id,
        "vectors_removed": vectors_removed,
        "message": "Deleted successfully",
    }
