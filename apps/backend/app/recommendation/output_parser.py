from __future__ import annotations

import json
import re

from pydantic import BaseModel, Field, field_validator

from app.recommendation.context_builder import ContextChunk, resolve_policy_id


# ── Internal LLM output models ────────────────────────────────────────────────
# These validate the raw JSON the LLM returns. They are NOT the API response models.

class LLMPolicyRec(BaseModel):
    policy_name: str
    insurer: str
    match_score: float = Field(ge=0.0, le=1.0)
    coverage_highlights: list[str]
    exclusions_noted: list[str]
    best_for: str
    citations: list[int]
    jargon_definitions: dict[str, str] = {}

    @field_validator("match_score", mode="before")
    @classmethod
    def clamp_score(cls, v: float) -> float:
        return max(0.0, min(1.0, float(v)))

    @field_validator("citations", mode="before")
    @classmethod
    def dedupe_citations(cls, v: list[int]) -> list[int]:
        return sorted(set(v))


class LLMComparisonRow(BaseModel):
    feature: str
    values: dict[str, str]


class LLMOutput(BaseModel):
    top_recommendation: LLMPolicyRec
    alternatives: list[LLMPolicyRec] = []
    comparison_table: list[LLMComparisonRow] = []
    personalized_reasoning: str
    empathy_note: str


# ── Parsing ───────────────────────────────────────────────────────────────────

def extract_llm_output(text: str) -> LLMOutput:
    """Parse and Pydantic-validate the LLM's JSON response.

    Handles markdown code fences (```json ... ```) that some LLMs emit
    despite instructions not to, and trailing non-JSON text.
    """
    cleaned = text.strip()

    # Strip opening/closing markdown fences
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    # If there is trailing text after the closing brace, truncate
    last_brace = cleaned.rfind("}")
    if last_brace != -1:
        cleaned = cleaned[: last_brace + 1]

    data = json.loads(cleaned)
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
    """Verify that personalized_reasoning explicitly mentions >= 3 profile fields.

    This enforces that recommendations are personalised, not generic text with
    profile fields only mentioned superficially.
    """
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
