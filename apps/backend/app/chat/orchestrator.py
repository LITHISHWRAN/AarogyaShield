from __future__ import annotations

from dataclasses import dataclass, field

import structlog

from app.chat.classifier import ChatIntent, classify_intent
from app.chat.guardrails import GuardrailAction, check_input, check_output, off_topic_response
from app.chat.prompts import build_greeting_response, build_grounded_messages
from app.chat.response_validator import ValidationResult, extract_cited_chunks, validate_chat_response
from app.chat.retriever import retrieve_for_chat
from app.core.config import settings
from app.memory.session_models import SessionData
from app.services.llm_service import get_llm

logger = structlog.get_logger()


@dataclass
class OrchestratorResult:
    reply: str
    intent: str
    cited_chunks: list[dict] = field(default_factory=list)
    was_guardrailed: bool = False
    grounding_warnings: list[str] = field(default_factory=list)


async def orchestrate_chat(
    session_id: str,
    message: str,
    session: SessionData,
) -> OrchestratorResult:
    """Full chat orchestration pipeline for a single turn.

    Pipeline:
    1. Input guardrail  — block medical advice / sensitive data before any LLM call
    2. Intent classify  — route to correct handler (fast, regex-only)
    3. Fast paths       — greetings and out-of-scope return without LLM call
    4. RAG retrieval    — Qdrant search, deduplicate, build numbered context
    5. LLM generation   — intent-tuned prompt with injected context + profile
    6. Output guardrail — catch medical advice that slipped through the prompt
    7. Response validation — citation index check, length check
    8. Assemble result  — cited_chunks + warnings for the API response

    The session.history at entry must NOT include the current user message yet —
    the caller (handle_chat) appends it after this function returns.
    """

    # ── 1. Input guardrail ────────────────────────────────────────────────────
    input_guard = check_input(message)
    if input_guard.blocked:
        logger.info(
            "Input guardrail triggered",
            session_id=session_id,
            reason=input_guard.reason,
        )
        return OrchestratorResult(
            reply=input_guard.safe_response,
            intent="guardrailed",
            was_guardrailed=True,
            grounding_warnings=[f"input_guardrail:{input_guard.reason}"],
        )

    # ── 2. Intent classification ──────────────────────────────────────────────
    intent = classify_intent(
        message,
        has_recommendations=session.recommendations is not None,
    )
    logger.info("Intent classified", session_id=session_id, intent=intent.value)

    # ── 3. Fast paths (no retrieval, no LLM) ─────────────────────────────────
    if intent == ChatIntent.GREETING:
        return OrchestratorResult(
            reply=build_greeting_response(session),
            intent=intent.value,
        )

    if intent == ChatIntent.OUT_OF_SCOPE:
        return OrchestratorResult(
            reply=off_topic_response(),
            intent=intent.value,
            was_guardrailed=True,
            grounding_warnings=["out_of_scope_deflection"],
        )

    # ── 4. RAG retrieval ──────────────────────────────────────────────────────
    context_chunks, context_str = await retrieve_for_chat(message, intent, session)
    logger.info(
        "Chunks retrieved",
        session_id=session_id,
        intent=intent.value,
        chunks=len(context_chunks),
    )

    # ── 5. Build prompt and call LLM ──────────────────────────────────────────
    messages = build_grounded_messages(
        intent=intent,
        message=message,
        context_str=context_str,
        session=session,
        max_history_turns=settings.CHAT_MAX_HISTORY_TURNS,
    )

    llm = get_llm()
    llm_response = await llm.ainvoke(messages)
    raw_reply: str = llm_response.content

    # ── 6. Output guardrail ───────────────────────────────────────────────────
    output_guard = check_output(raw_reply)
    if output_guard.blocked:
        logger.warning(
            "Output guardrail triggered",
            session_id=session_id,
            reason=output_guard.reason,
        )
        return OrchestratorResult(
            reply=output_guard.safe_response,
            intent=intent.value,
            was_guardrailed=True,
            grounding_warnings=[f"output_guardrail:{output_guard.reason}"],
        )

    # ── 7. Response validation ────────────────────────────────────────────────
    validation: ValidationResult = validate_chat_response(raw_reply, context_chunks, intent)

    if not validation.valid:
        logger.warning(
            "Response validation failed",
            session_id=session_id,
            warnings=validation.warnings,
        )

    final_reply = validation.sanitised_response

    # ── 8. Extract cited chunks for the API response ──────────────────────────
    cited = extract_cited_chunks(final_reply, context_chunks)

    logger.info(
        "Chat turn orchestrated",
        session_id=session_id,
        intent=intent.value,
        cited_count=len(cited),
        warnings=len(validation.warnings),
    )

    return OrchestratorResult(
        reply=final_reply,
        intent=intent.value,
        cited_chunks=cited,
        was_guardrailed=not validation.valid,
        grounding_warnings=validation.warnings,
    )
