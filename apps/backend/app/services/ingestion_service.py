from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import structlog

from app.ingestion.chunker import Chunk, chunk_text
from app.ingestion.cleaner import clean_text
from app.ingestion.parsers import get_parser, SUPPORTED_EXTENSIONS

logger = structlog.get_logger()


@dataclass
class IngestionResult:
    policy_id: str
    source_document_id: str
    policy_name: str
    insurer: str
    file_type: str
    filename: str
    chunk_count: int
    upload_date: datetime


async def run_ingestion(
    file_bytes: bytes,
    filename: str,
    policy_id: str,
    policy_name: str,
    insurer: str,
) -> tuple[IngestionResult, list[Chunk]]:
    """Orchestrates parse → clean → chunk.

    Returns an IngestionResult (metadata) and the list of Chunks.
    Vector storage and DB persistence are handled by the caller so this
    function remains pure and independently testable.

    Raises ValueError for unsupported file types.
    """
    file_type = _extension(filename)
    if file_type not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '{file_type}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    parser = get_parser(file_type)
    raw_text = parser.extract(file_bytes)
    cleaned = clean_text(raw_text)
    chunks = chunk_text(cleaned)

    logger.info(
        "Document ingested",
        policy_id=policy_id,
        file_type=file_type,
        raw_chars=len(raw_text),
        clean_chars=len(cleaned),
        chunks=len(chunks),
    )

    result = IngestionResult(
        policy_id=policy_id,
        source_document_id=policy_id,   # same UUID links vectors ↔ DB row
        policy_name=policy_name,
        insurer=insurer,
        file_type=file_type,
        filename=filename,
        chunk_count=len(chunks),
        upload_date=datetime.now(timezone.utc),
    )
    return result, chunks


def _extension(filename: str) -> str:
    if "." not in filename:
        return ""
    return filename.rsplit(".", 1)[-1].lower()
