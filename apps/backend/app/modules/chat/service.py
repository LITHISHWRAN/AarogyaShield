import structlog

from app.services.llm_service import generate_response
from app.services.session_service import get_session, save_session

logger = structlog.get_logger()


async def handle_chat(session_id: str, message: str, user_profile: dict) -> dict:
    history = await get_session(session_id)

    history.append({"role": "user", "content": message})

    reply = await generate_response(history=history, user_profile=user_profile)

    history.append({"role": "assistant", "content": reply})
    await save_session(session_id, history)

    logger.info("Chat handled", session_id=session_id, turns=len(history))
    return {"reply": reply, "history": history}
