from fastapi import APIRouter, HTTPException, status

from app.memory.session_store import get_session_store
from app.modules.chat import service
from app.modules.chat.schemas import (
    ChatRequest,
    ChatResponse,
    ChatMessage,
    SessionInfoResponse,
)

router = APIRouter()


@router.post("/", response_model=ChatResponse)
async def chat(body: ChatRequest):
    result = await service.handle_chat(
        session_id=body.session_id,
        message=body.message,
        user_profile=body.user_profile,
    )
    return ChatResponse(
        session_id=body.session_id,
        reply=result["reply"],
        history=[ChatMessage(**m) for m in result["history"]],
        profile_loaded=result["profile_loaded"],
        turn_count=result["turn_count"],
    )


@router.get("/{session_id}/session", response_model=SessionInfoResponse)
async def get_session_info(session_id: str):
    """Return session metadata without loading full history.

    The frontend calls this on page load to decide whether to show the
    onboarding form (no profile) or jump straight to the chat interface.
    """
    info = await get_session_store().session_info(session_id)
    return SessionInfoResponse(**info)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def clear_session(session_id: str):
    await get_session_store().clear_session(session_id)
