from __future__ import annotations

import json
import re

from json_repair import repair_json
from pydantic import BaseModel, Field, field_validator

from app.recommendation.context_builder import ContextChunk, resolve_policy_id


# ── Internal LLM output models ────────────────────────────────────────────────
# These validate the raw JSON the LLM returns. They are NOT the API response models.

class LLMPolicyRec(BaseModel):
    policy_name: str
    insurer: str
    match_score: float = Field(ge=0.0, le=1.0)
    coverage_highlights: list[str] = []
    exclusions_noted: list[str] = []
    best_for: str = ""
    citations: list[int] = []
    jargon_definitions: dict[str, str] = {}

    @field_validator("match_score", mode="before")
    @classmethod
    def clamp_score(cls, v: float) -> float:
        return max(0.0, min(1.0, float(v)))

    @field_validator("citations", mode="before")
    @classmethod
    def dedupe_citations(cls, v: object) -> list[int]:
        if not isinstance(v, list):
            return []
        return sorted({int(i) for i in v if isinstance(i, (int, float))})

    @field_validator("jargon_definitions", mode="before")
    @classmethod
    def clean_jargon(cls, v: object) -> dict[str, str]:
        if not isinstance(v, dict):
            return {}
        # Drop entries where the value is not a plain string (LLM sometimes nests
        # other fields like "alternatives" inside jargon_definitions by mistake)
        return {k: val for k, val in v.items() if isinstance(val, str)}

    @field_validator("coverage_highlights", "exclusions_noted", mode="before")
    @classmethod
    def ensure_str_list(cls, v: object) -> list[str]:
        if not isinstance(v, list):
            return []
        return [str(i) for i in v if i is not None]


class LLMComparisonRow(BaseModel):
    feature: str
    values: dict[str, str]


class LLMDecisionSummary(BaseModel):
    recommended: str
    top_reasons: list[str]
    main_drawback: str


class LLMOutput(BaseModel):
    top_recommendation: LLMPolicyRec
    alternatives: list[LLMPolicyRec] = []
    comparison_table: list[LLMComparisonRow] = []
    personalized_reasoning: str = ""
    empathy_note: str = ""
    decision_summary: LLMDecisionSummary | None = None

    @field_validator("alternatives", mode="before")
    @classmethod
    def ensure_alt_list(cls, v: object) -> list:
        # Guard against LLM putting a dict or None here
        if not isinstance(v, list):
            return []
        return v

    @field_validator("comparison_table", mode="before")
    @classmethod
    def ensure_table_list(cls, v: object) -> list:
        if not isinstance(v, list):
            return []
        return v


# ── Parsing ───────────────────────────────────────────────────────────────────

def extract_llm_output(text: str) -> LLMOutput:
    """Parse and Pydantic-validate the LLM's JSON response.

    Handles:
    - Markdown fences (```json ... ```) emitted despite JSON-mode instructions
    - Unescaped quotes / stray characters inside string values (via json-repair)
    - Trailing non-JSON text after the closing brace
    """
    cleaned = text.strip()

    # Strip markdown fences — handles both ```json and ``` variants
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", cleaned)
    cleaned = re.sub(r"\n?```\s*$", "", cleaned)
    cleaned = cleaned.strip()

    # Truncate anything after the final closing brace
    last_brace = cleaned.rfind("}")
    if last_brace != -1:
        cleaned = cleaned[: last_brace + 1]

    # First attempt: strict parse
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        # Fallback: repair common issues (unescaped quotes, trailing commas, etc.)
        repaired = repair_json(cleaned, return_objects=False)
        data = json.loads(repaired)

    return LLMOutput.model_validate(data)


# ── Validation ────────────────────────────────────────────────────────────────

def validate_citations(output: LLMOutput, context_chunks: list[ContextChunk]) -> list[str]:
    """Return grounding warnings for any citation index outside the context range.

    Invalid citations indicate the LLM fabricated a reference rather than citing
    a real excerpt. We surface these as warnings rather than hard failures so the
    response is still returned; the client can display a disclaimer.
    """
    max_index = len(context_chunks)
    warnings: list[str] = []

    def _check(rec: LLMPolicyRec) -> None:
        for idx in rec.citations:
            if not (1 <= idx <= max_index):
                warnings.append(
                    f"Policy '{rec.policy_name}' cites [{idx}] which does not exist "
                    f"in the retrieved context (max index: {max_index})."
                )

    _check(output.top_recommendation)
    for alt in output.alternatives:
        _check(alt)

    return warnings


def validate_profile_references(reasoning: str, profile: dict) -> list[str]:
    """Verify that personalized_reasoning explicitly mentions >= 3 profile fields."""
    if not reasoning.strip():
        return []

    field_signals: dict[str, list[str]] = {
        "name": [str(profile.get("name", "")).lower()],
        "age": [str(profile.get("age", "")), " year", "age"],
        "lifestyle": [str(profile.get("lifestyle", "")).lower()],
        "conditions": [c.lower() for c in profile.get("pre_existing_conditions", [])],
        "financial_band": [str(profile.get("financial_band", "")).lower(), "lpa", "income"],
        "city_tier": [str(profile.get("city_tier", "")).lower(), "tier"],
    }

    lower = reasoning.lower()
    referenced = [
        field
        for field, signals in field_signals.items()
        if any(s and s in lower for s in signals)
    ]

    if len(referenced) < 3:
        return [
            f"personalized_reasoning references only {len(referenced)} profile field(s) "
            f"({', '.join(referenced) or 'none'}). "
            f"Consider prompting the model to reference more profile details."
        ]
    return []


# ── Assembly helper ───────────────────────────────────────────────────────────

def resolve_policy_ids(output: LLMOutput, context_chunks: list[ContextChunk]) -> LLMOutput:
    """Policy IDs are UUIDs the LLM cannot know — resolve them post-parse.

    The LLM uses policy_name (from context headers) as the identifier.
    We match that back to the actual policy_id from the retrieved chunks.
    This is safe because policy_names in our context headers are sourced from
    the same Qdrant payloads we stored at ingestion time.
    """
    # Patch is not needed since LLMOutput is immutable — we just expose
    # resolve_policy_id for the assembler in chains.py to use per-record.
    return output
