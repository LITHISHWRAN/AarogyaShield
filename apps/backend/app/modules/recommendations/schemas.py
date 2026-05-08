from typing import List, Optional

from pydantic import BaseModel


class UserProfile(BaseModel):
    age: int
    income_bracket: str
    pre_existing_conditions: List[str] = []
    family_size: int = 1
    preferred_coverage: Optional[str] = None


class RecommendationRequest(BaseModel):
    session_id: str
    user_profile: UserProfile


class RecommendedPolicy(BaseModel):
    policy_id: str
    policy_name: str
    score: float
    rationale: str
    source_chunks: List[str]


class RecommendationResponse(BaseModel):
    recommendations: List[RecommendedPolicy]
    explanation: str
