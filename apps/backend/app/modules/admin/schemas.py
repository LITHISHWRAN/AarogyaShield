from datetime import datetime

from pydantic import BaseModel


class PolicyUploadResponse(BaseModel):
    policy_id: str
    policy_name: str
    insurer: str
    file_type: str
    filename: str
    chunks_indexed: int
    upload_date: datetime
    message: str


class PolicyDeleteResponse(BaseModel):
    policy_id: str
    vectors_removed: int
    message: str


class PolicyListItem(BaseModel):
    policy_id: str
    policy_name: str
    insurer: str
    file_type: str
    filename: str
    chunk_count: int
    source_document_id: str
    upload_date: datetime
