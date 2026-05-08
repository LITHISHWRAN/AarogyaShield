from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_admin
from app.db.session import get_db
from app.modules.admin import service
from app.modules.admin.schemas import PolicyDeleteResponse, PolicyListItem, PolicyUploadResponse

router = APIRouter(dependencies=[Depends(require_admin)])


@router.post("/policies/upload", response_model=PolicyUploadResponse)
async def upload_policy(
    policy_name: str = Form(..., description="Human-readable policy name"),
    insurer: str = Form(..., description="Insurance provider / company name"),
    file: UploadFile = File(..., description="PDF, TXT, or JSON document"),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    return await service.upload_policy(
        file_bytes=content,
        filename=file.filename or "unknown",
        policy_name=policy_name,
        insurer=insurer,
        db=db,
    )


@router.get("/policies", response_model=list[PolicyListItem])
async def list_policies(db: AsyncSession = Depends(get_db)):
    return await service.list_all_policies(db=db)


@router.get("/policies/{policy_id}", response_model=PolicyListItem)
async def get_policy(policy_id: str, db: AsyncSession = Depends(get_db)):
    return await service.get_policy_detail(policy_id=policy_id, db=db)


@router.delete("/policies/{policy_id}", response_model=PolicyDeleteResponse)
async def delete_policy(policy_id: str, db: AsyncSession = Depends(get_db)):
    return await service.delete_policy(policy_id=policy_id, db=db)
