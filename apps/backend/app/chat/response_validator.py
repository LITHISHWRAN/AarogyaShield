from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.chat.classifier import ChatIntent
from app.recommendation.context_builder import ContextChunk

# ── Patterns ──────────────────────────────────────────────────────────────────

_CITATION_RE = re.compile(r"\[(\d+)\]")

# Medical advice in LLM output — more specific than input patterns to reduce false positives
_OUTPUT_MEDICAL = re.compile(
    r"\b(you\s+should\s+take\s+(this\s+)?medication|i\s+recommend\s+(this\s+)?drug|"
    r"the\s+correct\s+dosage\s+is|this\s+(drug|medicine)\s+will\s+cure|"
    r"take\s+\d+\s*mg\s+of|diagnosed\s+with\s+\w+\s+and\s+should\s+take)\b",
    re.IGNORECASE,
)

# Minimum reply length below which we warn (but still return the response)
_MIN_REASONABLE_LENGTH = 40

_MEDICAL_DEFLECTION = (
    "I understand you have questions about your health condition. "
    "For medical guidance, please consult a qualified doctor.\n\n"
    "I can tell you what your health insurance policy covers for this type of treatment "
    "— hospitalisation, specialist visits, medicines under OPD, etc. "
    "Would you like me to check what's covered?"
)

# ── Result dataclass ──────────────────────────────────────────────────────────


@dataclass
class ValidationResult:
    valid: bool
    sanitised_response: str
    warnings: list[str] = field(default_factory=list)


# ── Citation extraction ───────────────────────────────────────────────────────


def extract_cited_chunks(response: str, context_chunks: list[ContextChunk]) -> list[dict]:
    """Return the context chunks actually cited in the response.

    Used to populate `cited_chunks` on the API response, giving the frontend
    source references it can display to the user.
    """
    cited_indices = {int(m) for m in _CITATION_RE.findall(response)}
    return [
        {
            "index": ch.index,
            "policy_name": ch.policy_name,
            "insurer": ch.insurer,
            "text": ch.text[:300] + "…" if len(ch.text) > 300 else ch.text,
        }
        for ch in context_chunks
        if ch.index in cited_indices
    ]


# ── Main validator ────────────────────────────────────────────────────────────


def validate_chat_response(
    response: str,
    context_chunks: list[ContextChunk],
    intent: ChatIntent,
) -> ValidationResult:
    """Post-generation response validation.

    Checks (in order):
    1. Medical advice in the LLM response → replace entirely with deflection.
    2. Citation index validity → warn (don't block; the response may still be useful).
    3. Suspiciously short response → warn.

    Returns a ValidationResult with a (possibly sanitised) response and any warnings.
    """
    # ── Check 1: medical advice in output ─────────────────────────────────────
    if _OUTPUT_MEDICAL.search(response):
        return ValidationResult(
            valid=False,
            sanitised_response=_MEDICAL_DEFLECTION,
            warnings=["Medical advice detected in LLM response — replaced with safe deflection."],
        )

    warnings: list[str] = []

    # ── Check 2: citation index validity ──────────────────────────────────────
    grounded_intents = {
        ChatIntent.POLICY_QUESTION,
        ChatIntent.JARGON_DEFINITION,
        ChatIntent.RECOMMENDATION_FOLLOWUP,
        ChatIntent.GENERAL_INSURANCE,
    }
    if intent in grounded_intents and context_chunks:
        max_index = len(context_chunks)
        cited = {int(m) for m in _CITATION_RE.findall(response)}
        invalid = {i for i in cited if not (1 <= i <= max_index)}
        if invalid:
            warnings.append(
                f"Response cites {sorted(invalid)} which {'does' if len(invalid) == 1 else 'do'} "
                f"not exist in the retrieved context (valid: 1–{max_index})."
            )

    # ── Check 3: suspiciously short ───────────────────────────────────────────
    if (
        len(response.strip()) < _MIN_REASONABLE_LENGTH
        and intent not in {ChatIntent.GREETING, ChatIntent.OUT_OF_SCOPE}
    ):
        warnings.append(
            f"Response is very short ({len(response.strip())} chars). "
            "May indicate an LLM generation failure."
        )

    return ValidationResult(valid=True, sanitised_response=response, warnings=warnings)
