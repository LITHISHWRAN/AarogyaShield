from fastapi import APIRouter

from app.modules.auth import service
from app.modules.auth.schemas import LoginRequest, RegisterRequest, TokenResponse

router = APIRouter()


@router.post("/register", response_model=TokenResponse)
async def register(body: RegisterRequest):
    await service.register_user(body.email, body.password, body.full_name)
    token = await service.authenticate_user(body.email, body.password)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    token = await service.authenticate_user(body.email, body.password)
    return TokenResponse(access_token=token)
