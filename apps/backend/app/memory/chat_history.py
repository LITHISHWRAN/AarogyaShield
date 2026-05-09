from __future__ import annotations

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from app.memory.session_models import StoredMessage
from app.memory.session_store import get_session_store


class SessionChatHistory(BaseChatMessageHistory):
    """LangChain-compatible chat history backed by our Redis session store.

    Implements the async interface (aget_messages, aadd_messages) for use with
    LangChain's RunnableWithMessageHistory and other async chains.

    The sync interface (messages property, add_message) is intentionally no-op —
    our application is fully async. Using sync methods in an async context would
    require blocking the event loop, which we avoid.

    Usage with RunnableWithMessageHistory:

        from langchain_core.runnables.history import RunnableWithMessageHistory

        chain_with_memory = RunnableWithMessageHistory(
            chain,
            lambda session_id: SessionChatHistory(session_id),
            input_messages_key="input",
            history_messages_key="history",
        )
    """

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id

    # ── Async interface (preferred) ───────────────────────────────────────────

    async def aget_messages(self) -> list[BaseMessage]:
        store = get_session_store()
        stored = await store.get_history(self.session_id)  # type: ignore[arg-type]
        # Reconstruct history from session store
        raw = await store.load_session(self.session_id)
        return [_to_lc(m) for m in raw.history if m.role in ("user", "assistant")]

    async def aadd_messages(self, messages: list[BaseMessage]) -> None:
        store = get_session_store()
        new = [_from_lc(m) for m in messages]
        await store.append_messages(self.session_id, new)

    async def aclear(self) -> None:
        await get_session_store().clear_session(self.session_id)

    # ── Sync stubs (LangChain ABC requirement) ────────────────────────────────

    @property
    def messages(self) -> list[BaseMessage]:
        # Sync access is not supported — always use aget_messages in async code.
        return []

    def add_message(self, message: BaseMessage) -> None:
        pass

    def clear(self) -> None:
        pass


# ── Conversion helpers ────────────────────────────────────────────────────────

def _to_lc(msg: StoredMessage) -> BaseMessage:
    if msg.role == "user":
        return HumanMessage(content=msg.content)
    return AIMessage(content=msg.content)


def _from_lc(msg: BaseMessage) -> StoredMessage:
    role = "user" if isinstance(msg, HumanMessage) else "assistant"
    return StoredMessage(role=role, content=msg.content)


def get_session_history(session_id: str) -> SessionChatHistory:
    """Factory function for use with RunnableWithMessageHistory."""
    return SessionChatHistory(session_id)
