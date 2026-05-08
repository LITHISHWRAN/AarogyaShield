from __future__ import annotations

from app.modules.recommendations.schemas import UserProfile

GROUNDED_SYSTEM_PROMPT = """\
You are AarogyaAid, a compassionate and knowledgeable health insurance advisor for Indian users.

━━━ GROUNDING RULES (NON-NEGOTIABLE) ━━━
1. CITE EVERYTHING — Every factual claim about a policy (coverage amount, waiting period,
   exclusion, premium, benefit, sub-limit) MUST be followed by [N] citing the excerpt number.
2. NO INVENTION — If a detail is not present in the provided excerpts, write
   "Not mentioned in available documents" — never infer, extrapolate, or invent.
3. PROFILE ANCHORING — Your personalized_reasoning MUST reference at least 3 of these fields
   by name: name, age, lifestyle, pre-existing conditions, financial band, city tier.
4. JARGON DEFINITIONS — For any insurance term you use (e.g., co-payment, sub-limit,
   waiting period, sum insured, floater, NCB), define it using only language from the excerpts.
5. EMPATHY — Acknowledge the user's specific health situation with warmth and without judgment.

━━━ OUTPUT FORMAT ━━━
Return a single valid JSON object. No markdown, no extra text outside the JSON.
"""


# JSON schema description embedded in the human prompt — uses {{}} escaping for .format()
_JSON_SCHEMA = """\
{{
  "top_recommendation": {{
    "policy_name": "<exact name from excerpts>",
    "insurer": "<exact insurer from excerpts>",
    "match_score": <float 0.0-1.0>,
    "coverage_highlights": ["<fact [N]>", "<fact [N]>", ...],
    "exclusions_noted": ["<exclusion [N]>", ...],
    "best_for": "<one sentence why this suits this specific user>",
    "citations": [<N>, <N>, ...],
    "jargon_definitions": {{
      "<term>": "<definition derived from excerpts>"
    }}
  }},
  "alternatives": [
    {{ ...same structure as top_recommendation... }}
  ],
  "comparison_table": [
    {{
      "feature": "<e.g., Sum Insured, Waiting Period, Co-payment>",
      "values": {{
        "<policy_name>": "<value [N]>",
        "<policy_name>": "<value [N]>"
      }}
    }}
  ],
  "personalized_reasoning": "<paragraph that explicitly references the user's name, age,
    conditions, financial band, and city tier to explain WHY this recommendation fits>",
  "empathy_note": "<one warm sentence acknowledging the user's specific health situation>"
}}"""


_HUMAN_TEMPLATE = """\
POLICY DOCUMENT EXCERPTS
(These are your ONLY source of truth. Cite each as [N] in your response.)

{context}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

USER PROFILE:
  Name:                  {name}
  Age:                   {age} years
  Lifestyle:             {lifestyle}
  Pre-existing conditions: {conditions}
  Financial band (annual): {financial_band}
  City tier:             {city_tier}
  Family size:           {family_size}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TASK:
Based STRICTLY on the excerpts above, recommend the most suitable health insurance
policies for this user. Explain why each policy fits or doesn't fit their profile.

Return this exact JSON structure (no other text):
{schema}
"""


def build_human_prompt(context_str: str, profile: UserProfile) -> str:
    conditions = (
        ", ".join(profile.pre_existing_conditions)
        if profile.pre_existing_conditions
        else "none"
    )
    return _HUMAN_TEMPLATE.format(
        context=context_str,
        name=profile.name,
        age=profile.age,
        lifestyle=profile.lifestyle,
        conditions=conditions,
        financial_band=profile.financial_band,
        city_tier=profile.city_tier,
        family_size=profile.family_size,
        schema=_JSON_SCHEMA,
    )
