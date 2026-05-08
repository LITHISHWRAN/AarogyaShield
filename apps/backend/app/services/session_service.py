from __future__ import annotations

import json

import redis.asyncio as aioredis
import structlog

from app.core.config import settings

logger = structlog.get_logger()

_redis: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            decode_responses=True,
        )
    return _redis


def _key(session_id: str) -> str:
    return f"session:{session_id}"


async def get_session(session_id: str) -> list:
    raw = await get_redis().get(_key(session_id))
    return json.loads(raw) if raw else []


async def save_session(session_id: str, history: list) -> None:
    await get_redis().setex(_key(session_id), settings.REDIS_SESSION_TTL, json.dumps(history))


async def clear_session(session_id: str) -> None:
    await get_redis().delete(_key(session_id))
    logger.info("Session cleared", session_id=session_id)


async def check_redis() -> bool:
    try:
        await get_redis().ping()
        return True
    except Exception:
        return False
