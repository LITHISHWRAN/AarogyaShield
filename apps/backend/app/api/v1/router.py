from fastapi import APIRouter

from app.modules.auth.router import router as auth_router
from app.modules.chat.router import router as chat_router
from app.modules.policies.router import router as policies_router
from app.modules.recommendations.router import router as recommendations_router
from app.modules.admin.auth import router as admin_auth_router
from app.modules.admin.router import router as admin_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(chat_router, prefix="/chat", tags=["chat"])
api_router.include_router(policies_router, prefix="/policies", tags=["policies"])
api_router.include_router(recommendations_router, prefix="/recommendations", tags=["recommendations"])

# Admin: login is public, all other operations require a valid admin JWT
api_router.include_router(admin_auth_router, prefix="/admin")
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])
