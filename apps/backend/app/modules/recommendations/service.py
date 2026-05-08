import structlog

from app.services.llm_service import generate_recommendations
from app.services.vector_service import search_policies

logger = structlog.get_logger()


async def get_recommendations(session_id: str, user_profile: dict) -> dict:
    chunks = await search_policies(user_profile)
    result = await generate_recommendations(user_profile=user_profile, chunks=chunks)
    logger.info(
        "Recommendations generated",
        session_id=session_id,
        count=len(result.get("recommendations", [])),
    )
    return result
