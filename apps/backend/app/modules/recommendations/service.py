from __future__ import annotations

import structlog

from app.modules.recommendations.schemas import RecommendationResponse, UserProfile
from app.recommendation.chains import run_recommendation_chain

logger = structlog.get_logger()


async def get_recommendations(
    session_id: str,
    user_profile: UserProfile,
) -> RecommendationResponse:
    result = await run_recommendation_chain(
        profile=user_profile,
        session_id=session_id,
    )
    logger.info(
        "Recommendations served",
        session_id=session_id,
        top_policy=result.top_recommendation.policy_name if result.top_recommendation else "none",
        alternatives=len(result.alternatives),
        warnings=len(result.grounding_warnings),
    )
    return result
