from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Policy


async def create_policy(
    session: AsyncSession,
    *,
    policy_id: str,
    policy_name: str,
    insurer: str,
    file_type: str,
    filename: str,
    source_document_id: str,
    chunk_count: int,
    upload_date: datetime,
) -> Policy:
    policy = Policy(
        id=policy_id,
        name=policy_name,
        provider=insurer,
        file_type=file_type,
        filename=filename,
        source_document_id=source_document_id,
        chunk_count=chunk_count,
        created_at=upload_date,
    )
    session.add(policy)
    await session.commit()
    await session.refresh(policy)
    return policy


async def get_policy(session: AsyncSession, policy_id: str) -> Policy | None:
    result = await session.execute(select(Policy).where(Policy.id == policy_id))
    return result.scalar_one_or_none()


async def list_policies(session: AsyncSession) -> list[Policy]:
    result = await session.execute(select(Policy).order_by(Policy.created_at.desc()))
    return list(result.scalars().all())


async def delete_policy_record(session: AsyncSession, policy_id: str) -> bool:
    result = await session.execute(delete(Policy).where(Policy.id == policy_id))
    await session.commit()
    return result.rowcount > 0
