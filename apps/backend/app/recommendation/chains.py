from __future__ import annotations

import asyncio

import structlog
from langchain_core.messages import HumanMessage, SystemMessage

from app.core.config import settings
from app.modules.recommendations.schemas import (
    ComparisonRow,
    RecommendationResponse,
    RecommendedPolicyDetail,
    SourceChunk,
    UserProfile,
)
from app.recommendation.context_builder import (
    ContextChunk,
    build_numbered_context,
    resolve_policy_id,
)
from app.recommendation.output_parser import (
    LLMOutput,
    LLMPolicyRec,
    extract_llm_output,
    validate_citations,
    validate_profile_references,
)
from app.recommendation.prompts import GROUNDED_SYSTEM_PROMPT, build_human_prompt
from app.recommendation.query_builder import build_retrieval_queries
from app.services.llm_service import get_llm
from app.services.vector_service import search_with_query

logger = structlog.get_logger()


async def run_recommendation_chain(
    profile: UserProfile,
    session_id: str,
) -> RecommendationResponse:
    """Full RAG recommendation pipeline.

    Steps:
    1. Build targeted retrieval queries from profile
    2. Run queries in parallel against Qdrant
    3. Deduplicate and format numbered context
    4. Invoke LLM with grounded prompt
    5. Parse structured JSON output
    6. Validate citations and profile references
    7. Assemble final RecommendationResponse
    """

    # ── 1. Multi-query parallel retrieval ─────────────────────────────────────
    queries = build_retrieval_queries(profile)
    logger.info("Retrieval queries built", session_id=session_id, count=len(queries))

    raw_results = await asyncio.gather(
        *[search_with_query(q, top_k=settings.RAG_TOP_K) for q in queries]
    )
    raw_chunks = [chunk for results in raw_results for chunk in results]
    logger.info("Chunks retrieved", session_id=session_id, total=len(raw_chunks))

    # ── 2. Deduplicate and build numbered context ──────────────────────────────
    context_chunks, context_str = build_numbered_context(raw_chunks)

    if not context_chunks:
        logger.warning("No relevant policy chunks found", session_id=session_id)
        return _no_context_response(session_id)

    # ── 3. Build prompt and invoke LLM ────────────────────────────────────────
    messages = [
        SystemMessage(content=GROUNDED_SYSTEM_PROMPT),
        HumanMessage(content=build_human_prompt(context_str, profile)),
    ]

    llm = get_llm()
    llm_response = await llm.ainvoke(messages)
    logger.info("LLM response received", session_id=session_id)

    # ── 4. Parse structured output ────────────────────────────────────────────
    try:
        llm_output: LLMOutput = extract_llm_output(llm_response.content)
    except Exception as exc:
        logger.error("LLM output parse failed", session_id=session_id, error=str(exc))
        raise ValueError(f"Failed to parse recommendation output: {exc}") from exc

    # ── 5. Validate grounding ─────────────────────────────────────────────────
    grounding_warnings: list[str] = []
    grounding_warnings += validate_citations(llm_output, context_chunks)
    grounding_warnings += validate_profile_references(
        llm_output.personalized_reasoning,
        profile.model_dump(),
    )

    if grounding_warnings:
        logger.warning(
            "Grounding warnings",
            session_id=session_id,
            warnings=grounding_warnings,
        )

    # ── 6. Assemble response ──────────────────────────────────────────────────
    return _assemble_response(
        session_id=session_id,
        llm_output=llm_output,
        context_chunks=context_chunks,
        grounding_warnings=grounding_warnings,
    )


# ── Assembly helpers ──────────────────────────────────────────────────────────

def _build_policy_detail(
    rec: LLMPolicyRec,
    context_chunks: list[ContextChunk],
) -> RecommendedPolicyDetail:
    return RecommendedPolicyDetail(
        policy_id=resolve_policy_id(rec.policy_name, context_chunks),
        policy_name=rec.policy_name,
        insurer=rec.insurer,
        match_score=rec.match_score,
        coverage_highlights=rec.coverage_highlights,
        exclusions_noted=rec.exclusions_noted,
        best_for=rec.best_for,
        citations=rec.citations,
        jargon_definitions=rec.jargon_definitions,
    )


def _assemble_response(
    session_id: str,
    llm_output: LLMOutput,
    context_chunks: list[ContextChunk],
    grounding_warnings: list[str],
) -> RecommendationResponse:
    top = _build_policy_detail(llm_output.top_recommendation, context_chunks)
    alternatives = [_build_policy_detail(a, context_chunks) for a in llm_output.alternatives]

    comparison_table = [
        ComparisonRow(feature=row.feature, values=row.values)
        for row in llm_output.comparison_table
    ]

    # Include ALL retrieved chunks so the client can render source transparency
    source_chunks = [
        SourceChunk(
            index=ch.index,
            policy_name=ch.policy_name,
            insurer=ch.insurer,
            chunk_index=ch.chunk_index,
            text=ch.text,
        )
        for ch in context_chunks
    ]

    return RecommendationResponse(
        session_id=session_id,
        top_recommendation=top,
        alternatives=alternatives,
        comparison_table=comparison_table,
        personalized_reasoning=llm_output.personalized_reasoning,
        empathy_note=llm_output.empathy_note,
        source_chunks=source_chunks,
        grounding_warnings=grounding_warnings,
    )


def _no_context_response(session_id: str) -> RecommendationResponse:
    """Returned when Qdrant has no indexed policies yet."""
    return RecommendationResponse(
        session_id=session_id,
        top_recommendation=None,
        alternatives=[],
        comparison_table=[],
        personalized_reasoning=(
            "No policy documents have been indexed yet. "
            "Please ask an administrator to upload insurance policy files."
        ),
        empathy_note="We want to help you find the right plan — please check back once policies are available.",
        source_chunks=[],
        grounding_warnings=["No policy documents found in the vector store."],
    )
