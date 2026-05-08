from __future__ import annotations

import uuid

import structlog
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.policy_repository import (
    create_policy,
    delete_policy_record,
    get_policy,
    list_policies,
)
from app.modules.admin.schemas import PolicyDeleteResponse, PolicyListItem, PolicyUploadResponse
from app.services.ingestion_service import run_ingestion
from app.services.vector_service import delete_policy_vectors, store_policy_chunks

logger = structlog.get_logger()


async def upload_policy(
    *,
    file_bytes: bytes,
    filename: str,
    policy_name: str,
    insurer: str,
    db: AsyncSession,
) -> PolicyUploadResponse:
    policy_id = str(uuid.uuid4())

    try:
        ingest_result, chunks = await run_ingestion(
            file_bytes=file_bytes,
            filename=filename,
            policy_id=policy_id,
            policy_name=policy_name,
            insurer=insurer,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    # 1. Store vectors (Qdrant) — happens before DB write.
    #    If DB write fails, re-upload will overwrite via upsert; no orphaned vectors serve results.
    await store_policy_chunks(
        chunks,
        policy_id=ingest_result.policy_id,
        policy_name=ingest_result.policy_name,
        insurer=ingest_result.insurer,
        file_type=ingest_result.file_type,
        source_document_id=ingest_result.source_document_id,
    )

    # 2. Persist metadata (PostgreSQL)
    await create_policy(
        db,
        policy_id=ingest_result.policy_id,
        policy_name=ingest_result.policy_name,
        insurer=ingest_result.insurer,
        file_type=ingest_result.file_type,
        filename=ingest_result.filename,
        source_document_id=ingest_result.source_document_id,
        chunk_count=ingest_result.chunk_count,
        upload_date=ingest_result.upload_date,
    )

    logger.info(
        "Policy upload complete",
        policy_id=ingest_result.policy_id,
        chunks=ingest_result.chunk_count,
    )
    return PolicyUploadResponse(
        policy_id=ingest_result.policy_id,
        policy_name=ingest_result.policy_name,
        insurer=ingest_result.insurer,
        file_type=ingest_result.file_type,
        filename=ingest_result.filename,
        chunks_indexed=ingest_result.chunk_count,
        upload_date=ingest_result.upload_date,
        message="Policy indexed successfully.",
    )


async def delete_policy(*, policy_id: str, db: AsyncSession) -> PolicyDeleteResponse:
    # 1. Remove vectors first — ghost vectors serving wrong results are unrecoverable.
    #    Orphaned DB metadata is recoverable (can be cleaned up manually or via a sweep job).
    vectors_removed = await delete_policy_vectors(policy_id)

    # 2. Remove DB record
    found = await delete_policy_record(db, policy_id)
    if not found:
        logger.warning("Policy not found in DB during delete", policy_id=policy_id)

    logger.info("Policy deleted", policy_id=policy_id, vectors_removed=vectors_removed)
    return PolicyDeleteResponse(
        policy_id=policy_id,
        vectors_removed=vectors_removed,
        message="Policy and all associated vectors deleted.",
    )


async def get_policy_detail(*, policy_id: str, db: AsyncSession) -> PolicyListItem:
    record = await get_policy(db, policy_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found.")
    return _to_list_item(record)


async def list_all_policies(*, db: AsyncSession) -> list[PolicyListItem]:
    records = await list_policies(db)
    return [_to_list_item(r) for r in records]


def _to_list_item(record) -> PolicyListItem:
    return PolicyListItem(
        policy_id=record.id,
        policy_name=record.name,
        insurer=record.provider,
        file_type=record.file_type,
        filename=record.filename,
        chunk_count=record.chunk_count,
        source_document_id=record.source_document_id,
        upload_date=record.created_at,
    )
