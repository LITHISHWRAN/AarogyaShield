from __future__ import annotations

from app.modules.recommendations.schemas import UserProfile

GROUNDED_SYSTEM_PROMPT = """\
You are AarogyaAid — a sharp, warm health insurance advisor who helps Indian users understand exactly what a policy does and doesn't cover, without the jargon fog.

━━━ YOUR VOICE ━━━
Write like a knowledgeable friend, not a compliance document. Every field in your JSON response should read as if a real, thoughtful person wrote it — warm, direct, and specific to this person's situation. Avoid corporate language, generic phrases, and anything that sounds templated.

━━━ GROUNDING RULES (NON-NEGOTIABLE) ━━━
1. CITE EVERYTHING — Every factual claim (coverage amount, waiting period, exclusion, benefit,
   sub-limit) MUST be followed by [N] citing the excerpt number. No exceptions.
2. NO INVENTION — If a detail isn't in the excerpts, write "Not mentioned in available documents".
   Never infer, extrapolate, or fill gaps with general insurance knowledge.
3. PROFILE ANCHORING — personalized_reasoning MUST naturally reference the user's name,
   conditions, financial band, and city — not as a checklist, but woven into genuine reasoning.
4. JARGON DEFINITIONS — Define any insurance term using only language from the excerpts.
5. STATE ONCE — Each fact belongs in one field only. Do not repeat across fields.
6. BREVITY — coverage_highlights and exclusions_noted: max 3 items, each under 20 words.
   personalized_reasoning: 2 to 3 sentences. decision_summary reasons: punchy phrases, not sentences.

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
    "coverage_highlights": ["<cited fact [N]>", "<cited fact [N]>"],
    "exclusions_noted": ["<cited exclusion [N]>", "<cited exclusion [N]>"],
    "best_for": "<one punchy sentence — specific to this user's conditions and situation, not generic marketing language>",
    "citations": [<N>, <N>],
    "jargon_definitions": {{
      "<term>": "<definition from excerpts>"
    }}
  }},
  "alternatives": [
    {{ ...same structure as top_recommendation... }}
  ],
  "comparison_table": [
    {{
      "feature": "<feature name>",
      "values": {{
        "<policy_name>": "<value [N]>",
        "<policy_name>": "<value [N]>"
      }}
    }}
  ],
  "personalized_reasoning": "<2 to 3 sentences written as a real advisor would — explain in plain language why this policy fits this specific person, weaving in their name, conditions, income band, and city naturally. Sound like a person, not a report.>",
  "empathy_note": "<one sentence that shows genuine understanding of their situation — name their actual conditions and the specific insurance challenge those create. Never generic. Example tone: 'With Diabetes and Kidney Disease already on record, the 4-year waiting period is the number that matters most here.'>",
  "decision_summary": {{
    "recommended": "<exact policy_name>",
    "top_reasons": ["<punchy phrase, not a full sentence>", "<punchy phrase>", "<punchy phrase>"],
    "main_drawback": "<one honest sentence about the biggest limitation for this specific user>"
  }}
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
