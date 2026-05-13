from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class GuardrailAction(str, Enum):
    ALLOW = "allow"
    BLOCK = "block"


@dataclass(frozen=True)
class GuardrailResult:
    action: GuardrailAction
    reason: str = ""
    safe_response: str = ""

    @property
    def blocked(self) -> bool:
        return self.action == GuardrailAction.BLOCK


# ── Input patterns ────────────────────────────────────────────────────────────
# These are checked BEFORE the LLM call.

_INPUT_MEDICAL_ADVICE = re.compile(
    r"\b(should\s+i\s+take|what\s+medication\s+should|which\s+drug\s+is\s+best|"
    r"is\s+it\s+safe\s+to\s+take|can\s+i\s+mix|correct\s+dosage|"
    r"diagnose\s+me|am\s+i\s+suffering|what\s+disease\s+do\s+i\s+have)\b",
    re.IGNORECASE,
)

_INPUT_SENSITIVE_DATA = re.compile(
    r"\b(\d{12}|\d{4}\s\d{4}\s\d{4})"            # Aadhar-like 12-digit
    r"|(\b[A-Z]{5}\d{4}[A-Z]\b)"                  # PAN format
    r"|(account\s+number\s*:\s*\d+)"
    r"|(credit\s+card\s+number)"
    r"|(otp\s+(is|:)\s*\d{4,6})",
    re.IGNORECASE,
)

# ── Output patterns ───────────────────────────────────────────────────────────
# These are checked AFTER the LLM responds.

_OUTPUT_MEDICAL_ADVICE = re.compile(
    r"\b(you\s+should\s+take\s+this\s+medication|i\s+recommend\s+this\s+drug|"
    r"the\s+correct\s+dosage\s+is|this\s+will\s+cure|you\s+are\s+suffering\s+from"
    r"\s+and\s+should|take\s+\w+\s+mg|consult\s+a\s+doctor\s+and\s+take)\b",
    re.IGNORECASE,
)

# ── Safe deflection messages ──────────────────────────────────────────────────

_MEDICAL_DEFLECTION = (
    "I'm here to help with health insurance coverage questions — not medical advice. "
    "For medical guidance, please consult a qualified doctor or your treating physician.\n\n"
    "That said, I can tell you what your policy covers for this type of condition "
    "(hospitalisation, OPD, medicines, specialist visits). Would you like that?"
)

_SENSITIVE_DATA_DEFLECTION = (
    "For your security, please avoid sharing Aadhar numbers, PAN, bank details, "
    "or OTPs in this chat. This conversation is not a secure channel for sensitive data.\n\n"
    "For policy-specific questions I'm happy to help — just ask!"
)

_OFF_TOPIC_DEFLECTION = (
    "I'm ShieldCare, and I specialise in health insurance guidance. "
    "I'm not able to help with that topic.\n\n"
    "I can help you with: policy coverage questions, insurance term definitions, "
    "claim procedures, or comparing plans. What would you like to know?"
)


def check_input(message: str) -> GuardrailResult:
    """Input guardrail — runs before any LLM call.

    Checks for:
    - Direct medical advice requests
    - Sensitive personal data in the message

    Returns BLOCK with a safe response if triggered.
    These are fast regex checks — no LLM involved.
    """
    if _INPUT_MEDICAL_ADVICE.search(message):
        return GuardrailResult(
            action=GuardrailAction.BLOCK,
            reason="medical_advice_request",
            safe_response=_MEDICAL_DEFLECTION,
        )

    if _INPUT_SENSITIVE_DATA.search(message):
        return GuardrailResult(
            action=GuardrailAction.BLOCK,
            reason="sensitive_data_in_input",
            safe_response=_SENSITIVE_DATA_DEFLECTION,
        )

    return GuardrailResult(action=GuardrailAction.ALLOW)


def check_output(response: str) -> GuardrailResult:
    """Output guardrail — runs after the LLM responds.

    Catches cases where the LLM drifted into medical advice despite instructions.
    The response is replaced entirely with a safe deflection.
    """
    if _OUTPUT_MEDICAL_ADVICE.search(response):
        return GuardrailResult(
            action=GuardrailAction.BLOCK,
            reason="medical_advice_in_response",
            safe_response=_MEDICAL_DEFLECTION,
        )

    return GuardrailResult(action=GuardrailAction.ALLOW)


def off_topic_response() -> str:
    return _OFF_TOPIC_DEFLECTION
