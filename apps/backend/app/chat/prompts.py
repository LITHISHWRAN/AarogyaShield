from __future__ import annotations

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from app.chat.classifier import ChatIntent
from app.memory.session_models import SessionData

# ── Grounded system prompt (all retrieval-backed intents) ─────────────────────

_GROUNDED_SYSTEM = """\
You are AarogyaAid, a compassionate and knowledgeable health insurance advisor for Indian users.

━━━ GROUNDING RULES (MANDATORY) ━━━
1. CITE EVERY FACT — Any claim about a policy (coverage, waiting period, exclusion,
   premium, benefit, limit) MUST be followed by [N] citing the excerpt number.
2. NO INVENTION — If information is not in the provided excerpts, say exactly:
   "This detail is not mentioned in the available policy documents."
   Never infer, extrapolate, or use general insurance knowledge as a substitute.
3. NO MEDICAL ADVICE — Never recommend medications, treatments, or diagnoses.
   If asked, say: "Please consult a qualified doctor for medical questions."
   You may explain what the policy COVERS for a condition — that is not medical advice.
4. STAY SCOPED — Only discuss health insurance. If the user asks about anything else,
   politely redirect to insurance topics.
5. PERSONALISE — Use the user's profile (name, conditions, financial band, city tier)
   to make every answer specific to their situation.
"""

# ── Intent-specific task instructions ────────────────────────────────────────

_INTENT_INSTRUCTIONS: dict[ChatIntent, str] = {
    ChatIntent.POLICY_QUESTION: (
        "Answer the question using ONLY the provided policy excerpts.\n"
        "Structure your answer:\n"
        "1. Direct answer with [N] citations.\n"
        "2. What this means specifically for {name} given their profile.\n"
        "3. Any relevant caveats or conditions found in the documents [N]."
    ),
    ChatIntent.JARGON_DEFINITION: (
        "Define the insurance term the user asked about.\n"
        "Structure your answer:\n"
        "1. Clear definition using language from the excerpts [N].\n"
        "2. A concrete example personalised to {name}'s situation "
        "(use their age, conditions, and financial band in the example).\n"
        "3. Any variations or nuances found in the documents [N].\n"
        "Keep the definition accessible — avoid unexplained jargon within the definition."
    ),
    ChatIntent.RECOMMENDATION_FOLLOWUP: (
        "Answer the follow-up question about the previously recommended policies.\n"
        "Structure your answer:\n"
        "1. Identify which policy the user is asking about.\n"
        "2. Answer using the document excerpts [N].\n"
        "3. Relate the answer to {name}'s specific situation."
    ),
    ChatIntent.GENERAL_INSURANCE: (
        "Answer the general insurance question using the excerpts as reference.\n"
        "1. Answer the question with [N] citations where applicable.\n"
        "2. Relate to {name}'s situation where relevant.\n"
        "3. If the excerpts don't address this, say so and offer to help with related coverage questions."
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
