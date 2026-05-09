from __future__ import annotations

from app.chat.classifier import ChatIntent
from app.memory.session_models import SessionData
from app.recommendation.context_builder import ContextChunk, build_numbered_context
from app.services.vector_service import search_with_query


def build_chat_query(
    message: str,
    intent: ChatIntent,
    session: SessionData,
) -> str:
    """Build a Qdrant query string tuned for single-turn chat retrieval.

    The query blends:
    - The user's literal question (primary signal)
    - The top recommended policy name (biases toward documents the user cares about)
    - The user's conditions (ensures condition-specific clauses surface)

    For jargon queries, we also append common related terms to improve recall
    of definition sections.
    """
    parts: list[str] = [message]

    # Bias toward the user's recommended policy
    if session.recommendations:
        parts.append(session.recommendations.top_policy_name)

    # Include conditions for coverage/exclusion retrieval
    if session.profile and session.profile.pre_existing_conditions:
        parts.extend(session.profile.pre_existing_conditions[:2])

    # For jargon, add a semantic hint to surface definition sections
    if intent == ChatIntent.JARGON_DEFINITION:
        parts.append("definition meaning explanation insurance terms glossary")

    return " ".join(parts)


async def retrieve_for_chat(
    message: str,
    intent: ChatIntent,
    session: SessionData,
) -> tuple[list[ContextChunk], str]:
    """Retrieve and format policy chunks for a single chat turn.

    Returns:
        context_chunks — ContextChunk list for citation validation
        context_str    — numbered context string for the LLM prompt

    Top-k is tuned per intent:
    - JARGON_DEFINITION needs fewer chunks (one good definition is enough)
    - POLICY_QUESTION / RECOMMENDATION_FOLLOWUP need more (coverage + exclusion + premium)
    - GENERAL_INSURANCE is in between
    """
    top_k_map = {
        ChatIntent.JARGON_DEFINITION: 3,
        ChatIntent.POLICY_QUESTION: 5,
        ChatIntent.RECOMMENDATION_FOLLOWUP: 5,
        ChatIntent.GENERAL_INSURANCE: 4,
    }
    top_k = top_k_map.get(intent, 4)

    query = build_chat_query(message, intent, session)
    raw_chunks = await search_with_query(query, top_k=top_k)

    return build_numbered_context(raw_chunks)
