from typing import List, Optional

from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    session_id: str
    message: str
    user_profile: Optional[dict] = None


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    history: List[ChatMessage]
