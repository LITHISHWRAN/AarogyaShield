from typing import List, Optional

from pydantic import BaseModel


class PolicyBase(BaseModel):
    name: str
    provider: str
    description: Optional[str] = None


class PolicyResponse(PolicyBase):
    id: str
    vector_ids: List[str] = []
