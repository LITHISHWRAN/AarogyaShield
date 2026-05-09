from __future__ import annotations

import structlog

from app.memory.session_models import StoredAlternative, StoredProfile, StoredRecommendations
from app.memory.session_store import get_session_store
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

    store = get_session_store()

    # Persist user profile so subsequent chat turns know the user's details
    stored_profile = StoredProfile(
        name=user_profile.name,
        age=user_profile.age,
        lifestyle=user_profile.lifestyle,
        pre_existing_conditions=user_profile.pre_existing_conditions,
        financial_band=user_profile.financial_band,
        city_tier=user_profile.city_tier,
        family_size=user_profile.family_size,
    )
    await store.save_profile(session_id, stored_profile)

    # Persist recommendation summary so chat can reference policies by name
    if result.top_recommendation:
        stored_recs = StoredRecommendations(
            top_policy_name=result.top_recommendation.policy_name,
            top_insurer=result.top_recommendation.insurer,
            top_policy_id=result.top_recommendation.policy_id,
            alternatives=[
                StoredAlternative(
                    policy_name=a.policy_name,
                    insurer=a.insurer,
                    policy_id=a.policy_id,
                )
                for a in result.alternatives
            ],
        )
        await store.save_recommendations(session_id, stored_recs)

    logger.info(
        "Recommendations served and persisted",
        session_id=session_id,
        top_policy=result.top_recommendation.policy_name if result.top_recommendation else "none",
        alternatives=len(result.alternatives),
        warnings=len(result.grounding_warnings),
    )
    return result
