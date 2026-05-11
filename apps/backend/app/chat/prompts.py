from __future__ import annotations

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from app.chat.classifier import ChatIntent
from app.memory.session_models import SessionData

# ── Grounded system prompt (all retrieval-backed intents) ─────────────────────

_GROUNDED_SYSTEM = """\
You are AarogyaAid — a sharp, warm health insurance advisor who helps Indian users cut through confusing policy documents and understand exactly what they're getting.

━━━ YOUR VOICE ━━━
Write like a knowledgeable friend who understands insurance deeply and genuinely cares about getting it right for this person.
- Conversational and warm — never stiff, clinical, or corporate
- Lead with the answer, then the context — never bury the point
- Write in flowing prose; no numbered steps, no bullet points, no headers
- Use plain language; when you must use an insurance term, define it in the same breath
- Be concise — 3 to 5 sentences is almost always enough, then stop

━━━ GROUNDING RULES ━━━
- Back every policy fact with a citation [N] — never invent or assume anything
- If something isn't in the documents, say it plainly: "I don't see that in what I have"
- Never give medical advice — you can explain what a policy covers, not what to treat
- Stay on health insurance — redirect anything else kindly but firmly

━━━ PERSONALISATION ━━━
You already know this person's name, conditions, income band, and city. Every answer should feel written specifically for them — not a template with their name swapped in. Mention their actual conditions when they're relevant. Skip the generic empathy phrases.
"""

# ── Intent-specific task instructions ────────────────────────────────────────

_INTENT_INSTRUCTIONS: dict[ChatIntent, str] = {
    ChatIntent.POLICY_QUESTION: (
        "Answer {name}'s question in natural prose — no lists, no steps. "
        "Open with the direct answer and cite it [N]. Then in a sentence or two, explain what that "
        "actually means for someone with {name}'s specific conditions. If there's a catch, weave it "
        "in naturally rather than saving it for the end. Keep the whole response under 100 words."
    ),
    ChatIntent.JARGON_DEFINITION: (
        "Explain this term to {name} the way you'd explain it to a smart friend who's new to insurance. "
        "One clear sentence for the meaning [N], then a concrete example that uses {name}'s actual "
        "situation — their conditions, income band, or city. No jargon inside the definition. "
        "Under 80 words total."
    ),
    ChatIntent.RECOMMENDATION_FOLLOWUP: (
        "Continue the conversation naturally — {name} is asking a follow-up, so pick up from context. "
        "Name the specific policy, give the cited answer [N], and connect it to their situation in "
        "one sentence. Write as if you're already mid-conversation, not starting fresh. Under 100 words."
    ),
    ChatIntent.GENERAL_INSURANCE: (
        "Answer directly in plain prose [N]. Connect to {name}'s situation only where it's genuinely "
        "useful — don't force it. If the documents don't cover this, say so honestly and offer what "
        "you can help with. Under 100 words."
    ),
}

# ── Human message templates ───────────────────────────────────────────────────

_GROUNDED_HUMAN = """\
POLICY DOCUMENT EXCERPTS
(Your ONLY source of factual information. Cite each as [N].)

{context}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

USER QUESTION: {question}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TASK:
{task_instruction}
"""

_NO_CONTEXT_HUMAN = """\
USER QUESTION: {question}

No relevant policy documents were found for this question.
Respond helpfully by:
1. Acknowledging that you don't have specific policy documents to cite for this.
2. Explaining what general type of policy information would address this question.
3. Suggesting the user consult their insurer or policy document directly.
Do NOT invent any policy details.
"""

_GREETING_TEMPLATES = {
    "with_profile_and_recs": (
        "Hello {name}! Great to see you again. Last time I recommended "
        "{top_policy} for you. Do you have questions about it, or would you "
        "like to explore coverage for something specific?"
    ),
    "with_profile_no_recs": (
        "Hello {name}! How can I help with your health insurance today? "
        "I can explain policy terms, answer coverage questions, or help you "
        "understand what plans are available."
    ),
    "no_profile": (
        "Hello! I'm AarogyaAid, your health insurance guide. I can help you "
        "understand policy coverage, define insurance terms, or answer questions "
        "about claims and benefits. What would you like to know?"
    ),
}


# ── Public builders ───────────────────────────────────────────────────────────

def build_grounded_messages(
    intent: ChatIntent,
    message: str,
    context_str: str,
    session: SessionData,
    max_history_turns: int,
) -> list[BaseMessage]:
    """Build the full message list for a grounded (RAG) chat turn.

    Structure:
    [SystemMessage: rules + profile + recommendations]
    [HumanMessage, AIMessage, ...] — recent history
    [HumanMessage: context + question + task instruction]
    """
    system_content = _build_system(session, intent)
    name = session.profile.name if session.profile else "the user"

    task_instruction = _INTENT_INSTRUCTIONS.get(intent, _INTENT_INSTRUCTIONS[ChatIntent.GENERAL_INSURANCE])
    task_instruction = task_instruction.format(name=name)

    # Trim history — session.history does NOT include the current message yet
    history_window = session.history[-(max_history_turns * 2):]

    messages: list[BaseMessage] = [SystemMessage(content=system_content)]
    for msg in history_window:
        if msg.role == "user":
            messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            messages.append(AIMessage(content=msg.content))

    if context_str:
        human_content = _GROUNDED_HUMAN.format(
            context=context_str,
            question=message,
            task_instruction=task_instruction,
        )
    else:
        human_content = _NO_CONTEXT_HUMAN.format(question=message)

    messages.append(HumanMessage(content=human_content))
    return messages


def build_greeting_response(session: SessionData) -> str:
    """Return a personalised greeting without calling the LLM."""
    if session.profile:
        name = session.profile.name
        if session.recommendations:
            return _GREETING_TEMPLATES["with_profile_and_recs"].format(
                name=name,
                top_policy=session.recommendations.top_policy_name,
            )
        return _GREETING_TEMPLATES["with_profile_no_recs"].format(name=name)
    return _GREETING_TEMPLATES["no_profile"]


def _build_system(session: SessionData, intent: ChatIntent) -> str:
    lines = [_GROUNDED_SYSTEM]

    if session.profile:
        p = session.profile
        conditions = (
            ", ".join(p.pre_existing_conditions)
            if p.pre_existing_conditions
            else "none declared"
        )
        lines.append(
            f"━━━ KNOWN USER PROFILE ━━━\n"
            f"Name: {p.name}  |  Age: {p.age}  |  Lifestyle: {p.lifestyle}\n"
            f"Conditions: {conditions}  |  Band: {p.financial_band}  |  Tier: {p.city_tier}\n"
            f"Do NOT ask for the above — you already have it. Use it to personalise answers.\n"
        )
    else:
        lines.append(
            "You do not yet know the user's profile. If they ask for a personalised "
            "answer, gently ask for their age, conditions, and income band.\n"
        )

    if session.recommendations and intent in (
        ChatIntent.RECOMMENDATION_FOLLOWUP,
        ChatIntent.POLICY_QUESTION,
    ):
        r = session.recommendations
        alts = (
            ", ".join(a.policy_name for a in r.alternatives[:3])
            if r.alternatives
            else "none"
        )
        lines.append(
            f"━━━ PREVIOUSLY RECOMMENDED POLICIES ━━━\n"
            f"Top: {r.top_policy_name} by {r.top_insurer}\n"
            f"Alternatives: {alts}\n"
            f"Reference these by name when answering follow-up questions.\n"
        )

    return "\n".join(lines)
