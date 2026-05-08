from fastapi import APIRouter, HTTPException, status

from app.modules.recommendations import service
from app.modules.recommendations.schemas import RecommendationRequest, RecommendationResponse

router = APIRouter()


@router.post("/", response_model=RecommendationResponse)
async def recommend(body: RecommendationRequest):
    try:
        return await service.get_recommendations(
            session_id=body.session_id,
            user_profile=body.user_profile,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Recommendation engine error: {exc}",
        )
