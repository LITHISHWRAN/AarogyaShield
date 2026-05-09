from __future__ import annotations

import re
from enum import Enum


class ChatIntent(str, Enum):
    POLICY_QUESTION = "policy_question"
    JARGON_DEFINITION = "jargon_definition"
    RECOMMENDATION_FOLLOWUP = "recommendation_followup"
    GENERAL_INSURANCE = "general_insurance"
    OUT_OF_SCOPE = "out_of_scope"
    GREETING = "greeting"


# ── Compiled patterns (module-level, compiled once) ───────────────────────────

_GREETING = re.compile(
    r"^\s*(hi|hello|hey|good\s+(morning|afternoon|evening)|thanks|thank\s+you|"
    r"bye|goodbye|how\s+are\s+you|nice\s+to\s+meet)\b",
    re.IGNORECASE,
)

_JARGON = re.compile(
    r"\b(what\s+is\s+a?n?|what\s+does|define|explain|meaning\s+of|what.s\s+a?n?)\b"
    r".{0,35}"
    r"\b(co.?pay(ment)?|deductible|sub.?limit|sum\s+insured|waiting\s+period|"
    r"premium|ncb|no.?claim\s+bonus|floater|cashless|tpa|exclusion|portability|"
    r"pre.?existing|rider|maternity|network\s+hospital|room\s+rent|icu|reimbursement)\b",
    re.IGNORECASE,
)

_MEDICAL_INTENT = re.compile(
    r"\b(should\s+i\s+take|what\s+medication|which\s+drug|is\s+it\s+safe\s+to|"
    r"can\s+i\s+mix|dosage\s+for|diagnose\s+me|am\s+i\s+sick|treat\s+my\s+condition|"
    r"cure\s+for|symptoms\s+of|which\s+doctor)\b",
    re.IGNORECASE,
)

_OFF_TOPIC = re.compile(
    r"\b(cricket|football|ipl|movie|film|recipe|code|programming|python|"
    r"javascript|weather|forecast|stock\s+market|crypto|bitcoin|relationship|"
    r"politics|government|election|news|sports)\b",
    re.IGNORECASE,
)

# Any of these words makes a message likely about insurance
_INSURANCE_SIGNAL = re.compile(
    r"\b(cover(ed|age|s)?|claim|reimburse|hospitaliz?ation|premium|exclusion|"
    r"benefit|waiting|cashless|network|policy|plan|insur|tpa|maternity|"
    r"ambulance|room\s+rent|icu|daycare|pre.?existing|discharge)\b",
    re.IGNORECASE,
)

# Signals that the user is asking about a previously recommended policy
_FOLLOWUP_SIGNALS = re.compile(
    r"\b(that\s+policy|the\s+recommended|the\s+plan\s+you|what\s+you\s+suggested|"
    r"the\s+one\s+you|star\s+health|hdfc|niva|care\s+health|aditya\s+birla|"
    r"manipal|religare|bajaj\s+allianz|new\s+india|max\s+bupa)\b",
    re.IGNORECASE,
)


def classify_intent(
    message: str,
    has_recommendations: bool = False,
) -> ChatIntent:
    """Classify a user message into one of six chat intents.

    Uses purely rule-based regex — no LLM call.  Fast and deterministic.
    The ordering matters: more specific patterns are checked first.

    Returns ChatIntent enum value.
    """
    # Greeting — checked first since it's a prefix match
    if _GREETING.match(message):
        return ChatIntent.GREETING

    # Jargon definition — explicit "what is X" for an insurance term
    if _JARGON.search(message):
        return ChatIntent.JARGON_DEFINITION

    # Medical advice — only block if there's no insurance signal alongside it
    if _MEDICAL_INTENT.search(message) and not _INSURANCE_SIGNAL.search(message):
        return ChatIntent.OUT_OF_SCOPE

    # Off-topic — block if clearly non-insurance AND no insurance signal
    if _OFF_TOPIC.search(message) and not _INSURANCE_SIGNAL.search(message):
        return ChatIntent.OUT_OF_SCOPE

    # Recommendation followup — references a previously suggested policy
    if has_recommendations and _FOLLOWUP_SIGNALS.search(message):
        return ChatIntent.RECOMMENDATION_FOLLOWUP

    # General insurance question with policy-specific signal
    if _INSURANCE_SIGNAL.search(message):
        return ChatIntent.POLICY_QUESTION

    # Default: treat as general insurance question (LLM + retrieval will handle it)
    return ChatIntent.GENERAL_INSURANCE
