from __future__ import annotations

import structlog
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.core.config import settings

logger = structlog.get_logger()

_llm: ChatAnthropic | None = None

SYSTEM_PROMPT = """You are AarogyaAid, an empathetic health insurance advisor.
You only recommend policies based on verified document excerpts provided to you.
Never invent or assume policy details not present in the provided context.
Always explain your reasoning using the user's specific profile fields."""


def get_llm() -> ChatAnthropic:
    global _llm
    if _llm is None:
        _llm = ChatAnthropic(
            model=settings.LLM_MODEL,
            anthropic_api_key=settings.ANTHROPIC_API_KEY,
            max_tokens=settings.LLM_MAX_TOKENS,
            temperature=settings.LLM_TEMPERATURE,
        )
    return _llm


async def generate_response(history: list, user_profile: dict) -> str:
    llm = get_llm()
    messages = [SystemMessage(content=SYSTEM_PROMPT)]
    for turn in history:
        if turn["role"] == "user":
            messages.append(HumanMessage(content=turn["content"]))
        else:
            messages.append(AIMessage(content=turn["content"]))
    response = await llm.ainvoke(messages)
    return response.content


async def generate_recommendations(user_profile: dict, chunks: list[dict]) -> dict:
    llm = get_llm()
    context = "\n\n".join(c["text"] for c in chunks)
    profile_str = "\n".join(f"- {k}: {v}" for k, v in user_profile.items())

    prompt = f"""User Profile:
{profile_str}

Policy Document Excerpts:
{context}

Based strictly on the above excerpts, recommend the most suitable policies for this user.
For each recommendation, cite the specific excerpt that supports it.
Do not reference any information not present in the excerpts."""

    response = await llm.ainvoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ])

    # Structured parsing and scoring added in Phase 2
    return {
        "recommendations": [],
        "explanation": response.content,
    }
