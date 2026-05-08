import uuid

from fastapi import APIRouter, Depends, File, UploadFile

from app.core.dependencies import require_admin
from app.modules.admin import service
from app.modules.admin.schemas import PolicyDeleteResponse, PolicyUploadResponse

# All routes on this router require a valid admin JWT.
# Adding Depends here rather than per-route guarantees no route can be accidentally left open.
router = APIRouter(dependencies=[Depends(require_admin)])


@router.post("/policies/upload", response_model=PolicyUploadResponse)
async def upload_policy(file: UploadFile = File(...)):
    policy_id = str(uuid.uuid4())
    content = await file.read()
    return await service.upload_policy(
        file_bytes=content,
        filename=file.filename or "unknown.pdf",
        policy_id=policy_id,
    )


@router.delete("/policies/{policy_id}", response_model=PolicyDeleteResponse)
async def delete_policy(policy_id: str):
    return await service.delete_policy(policy_id=policy_id)
