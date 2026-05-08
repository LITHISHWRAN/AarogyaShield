from fastapi import APIRouter

from app.modules.policies import service

router = APIRouter()


@router.get("/")
async def list_policies():
    return await service.list_policies()


@router.get("/{policy_id}")
async def get_policy(policy_id: str):
    return await service.get_policy(policy_id)
