from __future__ import annotations

import structlog

from app.chat.orchestrator import OrchestratorResult, orchestrate_chat
from app.core.config import settings
from app.memory.session_models import StoredMessage, StoredProfile
from app.memory.session_store import get_session_store

logger = structlog.get_logger()


async def handle_chat(
    session_id: str,
    message: str,
    user_profile: dict | None,
) -> dict:
    """Handle one chat turn through the full orchestration pipeline.

    Flow:
    1. Load session from Redis.
    2. Persist profile update if provided (supports mid-conversation profile changes).
    3. Call the orchestrator — does NOT receive the new user message in history yet.
    4. Append both user message and assistant reply to history and persist.
    5. Return the enriched response dict.

    The orchestrator is responsible for:
    - Input/output guardrails
    - Intent classification
    - Per-turn RAG retrieval
    - LLM call with grounded prompt
    - Response validation and citation extraction
    """
    store = get_session_store()
    session = await store.load_session(session_id)

    # ── Profile update ────────────────────────────────────────────────────────
    if user_profile:
        try:
            stored_profile = StoredProfile.model_validate(user_profile)
            await store.save_profile(session_id, stored_profile)
            session.profile = stored_profile
            logger.info("Profile updated in session", session_id=session_id)
        except Exception as exc:
            logger.warning(
                "Invalid profile data ignored",
                session_id=session_id,
                error=str(exc),
            )

    # ── Orchestrate (session.history does NOT contain the new message yet) ────
    result: OrchestratorResult = await orchestrate_chat(
        session_id=session_id,
        message=message,
        session=session,
    )

    # ── Persist both turns atomically ─────────────────────────────────────────
    new_messages = [
        StoredMessage(role="user", content=message),
        StoredMessage(role="assistant", content=result.reply),
    ]
    updated_history = await store.append_messages(session_id, new_messages)

    turn_count = sum(1 for m in updated_history if m.role == "user")

    logger.info(
        "Chat turn complete",
        session_id=session_id,
        intent=result.intent,
        turn=turn_count,
        guardrailed=result.was_guardrailed,
        cited=len(result.cited_chunks),
    )

    return {
        "reply": result.reply,
        "history": [{"role": m.role, "content": m.content} for m in updated_history],
        "profile_loaded": session.profile is not None,
        "turn_count": turn_count,
        "intent": result.intent,
        "cited_chunks": result.cited_chunks,
        "was_guardrailed": result.was_guardrailed,
        "grounding_warnings": result.grounding_warnings,
    }
