from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


class StoredMessage(BaseModel):
    """A single chat turn stored in Redis."""
    role: str                                        # "user" | "assistant"
    content: str
    timestamp: datetime = Field(default_factory=_now)


class StoredProfile(BaseModel):
    """User profile persisted to session on first collection.

    Mirrors UserProfile from recommendations/schemas.py.
    Kept separate so the memory layer has no dependency on the modules layer.
    """
    name: str
    age: int
    lifestyle: str
    pre_existing_conditions: list[str] = []
    financial_band: str
    city_tier: str
    family_size: int = 1


class StoredAlternative(BaseModel):
    policy_name: str
    insurer: str
    policy_id: str


class StoredRecommendations(BaseModel):
    """Lightweight summary of the last recommendation run, stored in session.

    Injected into the chat system message so the LLM can reference specific
    policies in follow-up questions without the user repeating them.
    """
    top_policy_name: str
    top_insurer: str
    top_policy_id: str
    alternatives: list[StoredAlternative] = []
    recommended_at: datetime = Field(default_factory=_now)


class SessionData(BaseModel):
    """Full in-memory representation of a user session, loaded from Redis."""
    session_id: str
    profile: Optional[StoredProfile] = None
    recommendations: Optional[StoredRecommendations] = None
    history: list[StoredMessage] = []
    created_at: datetime = Field(default_factory=_now)
    last_active_at: datetime = Field(default_factory=_now)
