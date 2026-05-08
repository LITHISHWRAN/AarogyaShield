from __future__ import annotations

from app.modules.recommendations.schemas import UserProfile

# Lifestyle values that warrant a dedicated query into hazard/sports sections
_NON_STANDARD_LIFESTYLES = frozenset({
    "smoker", "smoking", "athlete", "sports", "adventure",
    "high-risk", "high risk", "hazardous",
})


def build_retrieval_queries(profile: UserProfile) -> list[str]:
    """Build targeted retrieval queries from a user profile.

    Instead of one blunt query (profile fields joined), we build 3-4 queries,
    each targeting a distinct section type in insurance documents:

    1. Coverage/benefit sections  → matches sum insured, hospitalisation, OPD
    2. Exclusion/waiting sections → matches pre-existing disease limits, waiting periods
    3. Premium/affordability      → matches premium slabs, renewal, no-claim bonus
    4. Lifestyle hazard (conditional) → sports, smoking, occupation risk clauses
    """
    conditions_str = (
        ", ".join(profile.pre_existing_conditions)
        if profile.pre_existing_conditions
        else "no pre-existing conditions"
    )
    coverage_type = "family floater" if profile.family_size > 1 else "individual"

    queries = [
        # Targets benefit/coverage clauses and sum insured tables
        (
            f"health insurance coverage hospitalisation benefits "
            f"{profile.age} year old {conditions_str} {coverage_type} plan"
        ),
        # Targets pre-existing disease exclusion clauses and waiting periods
        (
            f"pre-existing disease exclusion waiting period {conditions_str} "
            f"health insurance policy terms"
        ),
        # Targets premium tables, sum insured slabs, co-payment, renewal
        (
            f"health insurance premium sum insured {profile.financial_band} "
            f"{profile.city_tier} {coverage_type} annual renewal"
        ),
    ]

    # Only add lifestyle query for profiles where it adds signal
    if profile.lifestyle.lower() in _NON_STANDARD_LIFESTYLES:
        queries.append(
            f"health insurance {profile.lifestyle} lifestyle coverage "
            f"occupation hazard sports adventure exclusion"
        )

    return queries
