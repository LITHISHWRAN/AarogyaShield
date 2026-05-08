from fastapi import APIRouter

from app.modules.recommendations import service
from app.modules.recommendations.schemas import RecommendationRequest, RecommendationResponse

router = APIRouter()


@router.post("/", response_model=RecommendationResponse)
async def recommend(body: RecommendationRequest):
    result = await service.get_recommendations(
        session_id=body.session_id,
        user_profile=body.user_profile.model_dump(),
    )
    return result
