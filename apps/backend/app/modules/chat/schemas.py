from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: str   # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    session_id: str
    message: str
    # user_profile is only required on the first turn or to update a stored profile.
    # If the session already has a profile, omitting this field reuses the stored one.
    user_profile: Optional[dict] = None


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    history: List[ChatMessage]
    profile_loaded: bool = False    # True if session has a persisted profile
    turn_count: int = 0             # total user turns in this session


class SessionInfoResponse(BaseModel):
    session_id: str
    has_profile: bool
    has_recommendations: bool
    turn_count: int
    created_at: Optional[str] = None
    last_active_at: Optional[str] = None
