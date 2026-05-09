from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: str   # "user" | "assistant"
    content: str


class CitedChunk(BaseModel):
    """A policy excerpt the LLM cited in its reply.

    Returned on every grounded response so the frontend can display
    source attribution (e.g. "Source: Star Health Optima, excerpt 2").
    """
    index: int
    policy_name: str
    insurer: str
    text: str


class ChatRequest(BaseModel):
    session_id: str
    message: str
    # Only needed on the first turn or to update a stored profile.
    # Once saved to session, it is reused automatically.
    user_profile: Optional[dict] = None


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    history: List[ChatMessage]
    profile_loaded: bool = False
    turn_count: int = 0
    intent: str = "unknown"                 # classified intent for this turn
    cited_chunks: List[CitedChunk] = []     # source excerpts used in the reply
    was_guardrailed: bool = False           # True if a guardrail intervened
    grounding_warnings: List[str] = []     # citation or validation warnings


class SessionInfoResponse(BaseModel):
    session_id: str
    has_profile: bool
    has_recommendations: bool
    turn_count: int
    created_at: Optional[str] = None
    last_active_at: Optional[str] = None
