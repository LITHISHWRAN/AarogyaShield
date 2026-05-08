import uuid

from fastapi import APIRouter, File, UploadFile

from app.modules.admin import service
from app.modules.admin.schemas import PolicyDeleteResponse, PolicyUploadResponse

router = APIRouter()


@router.post("/policies/upload", response_model=PolicyUploadResponse)
async def upload_policy(file: UploadFile = File(...)):
    policy_id = str(uuid.uuid4())
    content = await file.read()
    result = await service.upload_policy(
        file_bytes=content,
        filename=file.filename or "unknown.pdf",
        policy_id=policy_id,
    )
    return result


@router.delete("/policies/{policy_id}", response_model=PolicyDeleteResponse)
async def delete_policy(policy_id: str):
    result = await service.delete_policy(policy_id=policy_id)
    return result
