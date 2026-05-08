from pydantic import BaseModel


class PolicyUploadResponse(BaseModel):
    policy_id: str
    chunks_indexed: int
    message: str


class PolicyDeleteResponse(BaseModel):
    policy_id: str
    vectors_removed: int
    message: str
