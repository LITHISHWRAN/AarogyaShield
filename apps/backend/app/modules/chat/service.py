from __future__ import annotations

import structlog

from app.core.config import settings
from app.memory.session_models import StoredMessage, StoredProfile
from app.memory.session_store import get_session_store
from app.services.llm_service import generate_chat_response

logger = structlog.get_logger()


async def handle_chat(
    session_id: str,
    message: str,
    user_profile: dict | None,
) -> dict:
    """Handle one chat turn with full session-aware memory.

    Flow:
    1. Load full session from Redis (profile, recommendations, history).
    2. If a profile is passed in the request, persist it to the session
       (supports profile updates mid-conversation).
    3. Append the new user message to history.
    4. Call the LLM with the enriched system message (profile + recs injected).
    5. Append the assistant reply to history and persist.
    6. Return reply + full history + session metadata.

    The LLM receives:
    - A system message that lists the known profile (so it never re-asks).
    - A system message that lists previously recommended policies.
    - The last N turns of conversation history.
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
            logger.warning("Invalid profile data ignored", session_id=session_id, error=str(exc))

    # ── Append user message ───────────────────────────────────────────────────
    user_msg = StoredMessage(role="user", content=message)
    session.history.append(user_msg)

    # ── Generate reply (profile + recommendations injected into system msg) ───
    reply = await generate_chat_response(
        session=session,
        max_history_turns=settings.CHAT_MAX_HISTORY_TURNS,
    )

    # ── Append assistant reply and persist ────────────────────────────────────
    assistant_msg = StoredMessage(role="assistant", content=reply)
    session.history.append(assistant_msg)
    await store.save_history(session_id, session.history)

    turn_count = sum(1 for m in session.history if m.role == "user")
    logger.info(
        "Chat turn complete",
        session_id=session_id,
        turn=turn_count,
        profile_loaded=session.profile is not None,
    )

    return {
        "reply": reply,
        "history": [{"role": m.role, "content": m.content} for m in session.history],
        "profile_loaded": session.profile is not None,
        "turn_count": turn_count,
    }
