from __future__ import annotations

import structlog
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import settings
from app.memory.session_models import SessionData

logger = structlog.get_logger()

_llm: ChatGoogleGenerativeAI | None = None
_json_llm: ChatGoogleGenerativeAI | None = None


def get_llm() -> ChatGoogleGenerativeAI:
    global _llm
    if _llm is None:
        _llm = ChatGoogleGenerativeAI(
            model=settings.LLM_MODEL,
            google_api_key=settings.GOOGLE_API_KEY,
            max_output_tokens=settings.LLM_MAX_TOKENS,
            temperature=settings.LLM_TEMPERATURE,
        )
    return _llm


def get_json_llm() -> ChatGoogleGenerativeAI:
    """LLM instance with Gemini's native JSON mode enabled.

    Uses model_kwargs to pass response_mime_type — the correct form for
    langchain-google-genai 2.x. Forces valid JSON output at the model layer.
    """
    global _json_llm
    if _json_llm is None:
        _json_llm = ChatGoogleGenerativeAI(
            model=settings.LLM_MODEL,
            google_api_key=settings.GOOGLE_API_KEY,
            max_output_tokens=settings.LLM_MAX_TOKENS,
            temperature=settings.LLM_TEMPERATURE,
            model_kwargs={"response_mime_type": "application/json"},
        )
    return _json_llm


# ── Chat response ─────────────────────────────────────────────────────────────

async def generate_chat_response(
    session: SessionData,
    max_history_turns: int = 20,
) -> str:
    """Generate the next assistant reply using session-aware context.

    The system message is built dynamically from session state:
    - If a profile is stored, the LLM is told what it already knows and
      instructed NOT to ask for that information again.
    - If recommendations exist, the LLM is told which policies were suggested
      so follow-up questions reference specific policies by name.

    History is trimmed to the last `max_history_turns` turns before sending
    to the LLM. The full history is retained in Redis for display purposes.
    The new user message must already be appended to session.history before
    calling this function.
    """
    llm = get_llm()

    system_content = _build_chat_system(session)

    # Each "turn" = one user message + one assistant message = 2 items.
    # We trim from the left to stay within the context window.
    history_window = session.history[-(max_history_turns * 2):]

    messages = [SystemMessage(content=system_content)]
    for msg in history_window:
        if msg.role == "user":
            messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            messages.append(AIMessage(content=msg.content))

    response = await llm.ainvoke(messages)
    return response.content


def _build_chat_system(session: SessionData) -> str:
    """Compose a context-rich system message from the current session state."""
    lines: list[str] = [
        "You are ShieldCare, a compassionate health insurance advisor for Indian users.",
        "You discuss policy details based only on information already established in this conversation.",
        "Never invent policy facts. If you are unsure, say so and suggest the user consult the insurer.",
        "",
    ]

    if session.profile:
        p = session.profile
        conditions = (
            ", ".join(p.pre_existing_conditions)
            if p.pre_existing_conditions
            else "none declared"
        )
        lines += [
            "━━━ KNOWN USER PROFILE ━━━",
            f"Name:                {p.name}",
            f"Age:                 {p.age} years",
            f"Lifestyle:           {p.lifestyle}",
            f"Pre-existing:        {conditions}",
            f"Financial band:      {p.financial_band}",
            f"City tier:           {p.city_tier}",
            f"Family size:         {p.family_size}",
            "",
            "You already know the above. Do NOT ask the user to repeat this information.",
            "Use these details to personalise every answer.",
            "",
        ]
    else:
        lines += [
            "You do not yet know the user's profile.",
            "If they ask for a recommendation, gently ask for: name, age, any pre-existing "
            "conditions, annual income band, and city tier.",
            "",
        ]

    if session.recommendations:
        r = session.recommendations
        alt_names = (
            ", ".join(a.policy_name for a in r.alternatives[:3])
            if r.alternatives
            else "none"
        )
        lines += [
            "━━━ PREVIOUSLY RECOMMENDED POLICIES ━━━",
            f"Top recommendation:  {r.top_policy_name} by {r.top_insurer}",
            f"Alternatives:        {alt_names}",
            "",
            "When the user asks follow-up questions about policies, refer to these by name.",
            "Do not re-run the recommendation engine — use the above results.",
            "",
        ]

    return "\n".join(lines)


# ── Kept for backward compatibility with generate_recommendations ─────────────

async def generate_recommendations(user_profile: dict, chunks: list[dict]) -> dict:
    """Legacy function retained for any callers not yet migrated to chains.py."""
    llm = get_llm()
    context = "\n\n".join(c["text"] for c in chunks)
    profile_str = "\n".join(f"- {k}: {v}" for k, v in user_profile.items())

    prompt = (
        f"User Profile:\n{profile_str}\n\n"
        f"Policy Excerpts:\n{context}\n\n"
        "Based strictly on the above excerpts, recommend the most suitable policies. "
        "Cite each excerpt that supports your recommendation. "
        "Do not reference information not present in the excerpts."
    )

    response = await llm.ainvoke([
        SystemMessage(content="You are ShieldCare, a grounded health insurance advisor."),
        HumanMessage(content=prompt),
    ])
    return {"recommendations": [], "explanation": response.content}
