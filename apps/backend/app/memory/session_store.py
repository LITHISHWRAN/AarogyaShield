from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

import redis.asyncio as aioredis
import structlog

from app.core.config import settings
from app.memory.session_models import (
    SessionData,
    StoredMessage,
    StoredProfile,
    StoredRecommendations,
)

logger = structlog.get_logger()

# ── Redis key helpers ─────────────────────────────────────────────────────────

_PREFIX = "aarogya:session"

# Hash field names — kept as constants to catch typos at import time
_F_HISTORY = "history"
_F_PROFILE = "profile"
_F_RECOMMENDATIONS = "recommendations"
_F_CREATED_AT = "created_at"
_F_LAST_ACTIVE = "last_active_at"


def _hkey(session_id: str) -> str:
    """Namespaced Redis Hash key for a session."""
    return f"{_PREFIX}:{session_id}"


# ── Redis client singleton ────────────────────────────────────────────────────

_redis_client: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
        )
    return _redis_client


# ── Session Store ─────────────────────────────────────────────────────────────

class SessionStore:
    """Redis Hash-backed session store.

    Each session is one Redis Hash key containing individual fields for history,
    profile, recommendations, and timestamps.  A single EXPIRE covers all fields
    atomically.  TTL is refreshed on every write so active sessions never expire.

    Session isolation: each session_id maps to a distinct key — no shared state
    is possible between users.
    """

    async def load_session(self, session_id: str) -> SessionData:
        """Load all session fields in one HGETALL call."""
        raw: dict[str, str] = await get_redis().hgetall(_hkey(session_id))

        if not raw:
            return SessionData(session_id=session_id)

        profile: Optional[StoredProfile] = None
        if raw.get(_F_PROFILE):
            try:
                profile = StoredProfile.model_validate_json(raw[_F_PROFILE])
            except Exception:
                logger.warning("Corrupt profile field", session_id=session_id)

        recommendations: Optional[StoredRecommendations] = None
        if raw.get(_F_RECOMMENDATIONS):
            try:
                recommendations = StoredRecommendations.model_validate_json(
                    raw[_F_RECOMMENDATIONS]
                )
            except Exception:
                logger.warning("Corrupt recommendations field", session_id=session_id)

        history: list[StoredMessage] = []
        if raw.get(_F_HISTORY):
            try:
                history = [
                    StoredMessage.model_validate(m)
                    for m in json.loads(raw[_F_HISTORY])
                ]
            except Exception:
                logger.warning("Corrupt history field", session_id=session_id)

        created_at = _parse_dt(raw.get(_F_CREATED_AT))
        last_active_at = _parse_dt(raw.get(_F_LAST_ACTIVE))

        return SessionData(
            session_id=session_id,
            profile=profile,
            recommendations=recommendations,
            history=history,
            created_at=created_at,
            last_active_at=last_active_at,
        )

    async def save_history(
        self, session_id: str, history: list[StoredMessage]
    ) -> None:
        r = get_redis()
        key = _hkey(session_id)
        serialised = json.dumps(
            [m.model_dump(mode="json") for m in history],
            default=str,
        )
        async with r.pipeline(transaction=False) as pipe:
            pipe.hset(key, _F_HISTORY, serialised)
            await _touch_pipe(pipe, key)
            await pipe.execute()

    async def save_profile(
        self, session_id: str, profile: StoredProfile
    ) -> None:
        r = get_redis()
        key = _hkey(session_id)
        async with r.pipeline(transaction=False) as pipe:
            pipe.hset(key, _F_PROFILE, profile.model_dump_json())
            await _touch_pipe(pipe, key)
            await pipe.execute()
        logger.info("Profile saved to session", session_id=session_id)

    async def save_recommendations(
        self, session_id: str, recs: StoredRecommendations
    ) -> None:
        r = get_redis()
        key = _hkey(session_id)
        async with r.pipeline(transaction=False) as pipe:
            pipe.hset(key, _F_RECOMMENDATIONS, recs.model_dump_json())
            await _touch_pipe(pipe, key)
            await pipe.execute()
        logger.info("Recommendations saved to session", session_id=session_id)

    async def get_profile(self, session_id: str) -> Optional[StoredProfile]:
        raw = await get_redis().hget(_hkey(session_id), _F_PROFILE)
        return StoredProfile.model_validate_json(raw) if raw else None

    async def append_messages(
        self, session_id: str, new_messages: list[StoredMessage]
    ) -> list[StoredMessage]:
        """Append messages and return the full updated history."""
        r = get_redis()
        key = _hkey(session_id)

        raw = await r.hget(key, _F_HISTORY)
        current: list[StoredMessage] = (
            [StoredMessage.model_validate(m) for m in json.loads(raw)]
            if raw
            else []
        )
        current.extend(new_messages)

        serialised = json.dumps(
            [m.model_dump(mode="json") for m in current], default=str
        )
        async with r.pipeline(transaction=False) as pipe:
            pipe.hset(key, _F_HISTORY, serialised)
            await _touch_pipe(pipe, key)
            await pipe.execute()

        return current

    async def clear_session(self, session_id: str) -> None:
        await get_redis().delete(_hkey(session_id))
        logger.info("Session cleared", session_id=session_id)

    async def session_info(self, session_id: str) -> dict:
        """Return lightweight session metadata without loading full history."""
        r = get_redis()
        key = _hkey(session_id)
        fields = await r.hmget(
            key, _F_PROFILE, _F_RECOMMENDATIONS, _F_CREATED_AT, _F_LAST_ACTIVE, _F_HISTORY
        )
        profile_raw, recs_raw, created_raw, active_raw, hist_raw = fields

        turn_count = 0
        if hist_raw:
            try:
                msgs = json.loads(hist_raw)
                turn_count = sum(1 for m in msgs if m.get("role") == "user")
            except Exception:
                pass

        return {
            "session_id": session_id,
            "has_profile": bool(profile_raw),
            "has_recommendations": bool(recs_raw),
            "turn_count": turn_count,
            "created_at": created_raw,
            "last_active_at": active_raw,
        }


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _touch_pipe(pipe, key: str) -> None:
    """Queue last_active_at update + TTL refresh onto an open pipeline."""
    now = datetime.now(timezone.utc).isoformat()
    pipe.hsetnx(key, _F_CREATED_AT, now)       # set created_at only if not exists
    pipe.hset(key, _F_LAST_ACTIVE, now)
    pipe.expire(key, settings.REDIS_SESSION_TTL)


def _parse_dt(value: Optional[str]) -> datetime:
    if value:
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            pass
    return datetime.now(timezone.utc)


# ── Module-level singleton ────────────────────────────────────────────────────

_store: SessionStore | None = None


def get_session_store() -> SessionStore:
    global _store
    if _store is None:
        _store = SessionStore()
    return _store
