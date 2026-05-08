from fastapi import APIRouter

from app.modules.chat import service
from app.modules.chat.schemas import ChatRequest, ChatResponse

router = APIRouter()


@router.post("/", response_model=ChatResponse)
async def chat(body: ChatRequest):
    result = await service.handle_chat(
        session_id=body.session_id,
        message=body.message,
        user_profile=body.user_profile or {},
    )
    return ChatResponse(
        session_id=body.session_id,
        reply=result["reply"],
        history=result["history"],
    )


@router.delete("/{session_id}")
async def clear_session(session_id: str):
    from app.services.session_service import clear_session as _clear
    await _clear(session_id)
    return {"cleared": session_id}
