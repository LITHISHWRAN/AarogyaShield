from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    name: str
    age: int = Field(ge=1, le=120)
    lifestyle: str = Field(
        description="e.g. sedentary, active, smoker, athlete, high-risk"
    )
    pre_existing_conditions: list[str] = []
    financial_band: str = Field(
        description="Annual income band, e.g. '3-6 LPA', '6-10 LPA', '10-15 LPA'"
    )
    city_tier: str = Field(
        description="City classification, e.g. 'Tier 1', 'Tier 2', 'Tier 3'"
    )
    family_size: int = Field(default=1, ge=1)


class RecommendationRequest(BaseModel):
    session_id: str
    user_profile: UserProfile


# ── Response models ───────────────────────────────────────────────────────────

class RecommendedPolicyDetail(BaseModel):
    policy_id: str
    policy_name: str
    insurer: str
    match_score: float = Field(ge=0.0, le=1.0)
    coverage_highlights: list[str]
    exclusions_noted: list[str]
    best_for: str
    citations: list[int]
    jargon_definitions: dict[str, str] = {}


class ComparisonRow(BaseModel):
    feature: str
    values: dict[str, str]   # policy_name → value (with [N] citation)


class SourceChunk(BaseModel):
    """A retrieved policy excerpt included for source transparency."""
    index: int
    policy_name: str
    insurer: str
    chunk_index: int
    text: str


class DecisionSummary(BaseModel):
    recommended: str
    top_reasons: list[str]
    main_drawback: str


class RecommendationResponse(BaseModel):
    session_id: str
    top_recommendation: Optional[RecommendedPolicyDetail] = None
    alternatives: list[RecommendedPolicyDetail] = []
    comparison_table: list[ComparisonRow] = []
    personalized_reasoning: str
    empathy_note: str
    decision_summary: Optional[DecisionSummary] = None
    source_chunks: list[SourceChunk] = []
    grounding_warnings: list[str] = []
