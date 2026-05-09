"""
Pytest configuration and shared fixtures.

Environment variables MUST be set before any app.* import so that
pydantic-settings (Settings()) can instantiate without a real .env file
or live services.
"""
import os

# ── Inject test environment BEFORE any app.* imports ──────────────────────────
os.environ.update({
    "APP_ENV": "test",
    "APP_SECRET_KEY": "test-secret-key-aarogyashield-pytest",
    "LOG_LEVEL": "WARNING",
    "POSTGRES_HOST": "localhost",
    "POSTGRES_PORT": "5432",
    "POSTGRES_DB": "aarogyashield_test",
    "POSTGRES_USER": "test",
    "POSTGRES_PASSWORD": "testpassword",
    "REDIS_HOST": "localhost",
    "REDIS_PORT": "6379",
    "REDIS_PASSWORD": "testpassword",
    "REDIS_SESSION_TTL": "86400",
    "QDRANT_HOST": "localhost",
    "QDRANT_PORT": "6333",
    "QDRANT_COLLECTION_NAME": "test_policies",
    "ADMIN_USERNAME": "admin",
    "ADMIN_PASSWORD_HASH": "$2b$12$testhashabcdefghijklmnopqrstuvwx",
    "GOOGLE_API_KEY": "test-google-api-key",
    "LLM_MODEL": "gemini-2.5-flash",
    "EMBEDDING_MODEL": "sentence-transformers/all-MiniLM-L6-v2",
    "EMBEDDING_DIMENSION": "384",
    "RAG_TOP_K": "5",
    "CHAT_MAX_HISTORY_TURNS": "20",
})

import pytest
from app.modules.recommendations.schemas import UserProfile
from app.recommendation.context_builder import ContextChunk


# ── Shared profile fixtures ────────────────────────────────────────────────────

@pytest.fixture
def standard_profile() -> UserProfile:
    """Typical user with pre-existing conditions."""
    return UserProfile(
        name="Arjun Sharma",
        age=34,
        lifestyle="sedentary",
        pre_existing_conditions=["diabetes", "hypertension"],
        financial_band="6-10 LPA",
        city_tier="Tier 2",
        family_size=3,
    )


@pytest.fixture
def smoker_profile() -> UserProfile:
    """Smoker — triggers the lifestyle-hazard retrieval query."""
    return UserProfile(
        name="Priya Nair",
        age=28,
        lifestyle="smoker",
        pre_existing_conditions=[],
        financial_band="3-6 LPA",
        city_tier="Tier 1",
        family_size=1,
    )


@pytest.fixture
def athlete_profile() -> UserProfile:
    return UserProfile(
        name="Rohan Mehta",
        age=25,
        lifestyle="athlete",
        pre_existing_conditions=[],
        financial_band="6-10 LPA",
        city_tier="Tier 1",
        family_size=1,
    )


# ── Shared chunk fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def sample_raw_chunks() -> list[dict]:
    """Three raw Qdrant results from two policies."""
    return [
        {
            "policy_id": "pol-star-001",
            "policy_name": "Star Health Optima",
            "insurer": "Star Health Insurance",
            "chunk_index": 0,
            "text": "This policy covers hospitalisation expenses up to the sum insured.",
            "score": 0.92,
        },
        {
            "policy_id": "pol-star-001",
            "policy_name": "Star Health Optima",
            "insurer": "Star Health Insurance",
            "chunk_index": 1,
            "text": "Pre-existing diseases are covered after a waiting period of 2 years.",
            "score": 0.85,
        },
        {
            "policy_id": "pol-hdfc-001",
            "policy_name": "HDFC Optima Restore",
            "insurer": "HDFC ERGO",
            "chunk_index": 0,
            "text": "OPD consultations are reimbursed up to INR 500 per visit.",
            "score": 0.78,
        },
    ]


@pytest.fixture
def sample_context_chunks() -> list[ContextChunk]:
    """Three pre-built ContextChunk objects (1-indexed)."""
    return [
        ContextChunk(index=1, policy_id="pol-star-001", policy_name="Star Health Optima",
                     insurer="Star Health Insurance", chunk_index=0,
                     text="Covers hospitalisation up to sum insured.", score=0.92),
        ContextChunk(index=2, policy_id="pol-star-001", policy_name="Star Health Optima",
                     insurer="Star Health Insurance", chunk_index=1,
                     text="Waiting period of 2 years for pre-existing diseases.", score=0.85),
        ContextChunk(index=3, policy_id="pol-hdfc-001", policy_name="HDFC Optima Restore",
                     insurer="HDFC ERGO", chunk_index=0,
                     text="OPD consultations reimbursed up to INR 500.", score=0.78),
    ]


# ── Minimal valid LLM output JSON ─────────────────────────────────────────────

@pytest.fixture
def valid_llm_json_str() -> str:
    import json
    return json.dumps({
        "top_recommendation": {
            "policy_name": "Star Health Optima",
            "insurer": "Star Health Insurance",
            "match_score": 0.87,
            "coverage_highlights": ["Covers hospitalisation up to 5 lakhs [1]"],
            "exclusions_noted": ["No cosmetic procedures [2]"],
            "best_for": "Families with pre-existing conditions needing broad coverage",
            "citations": [1, 2],
            "jargon_definitions": {
                "waiting period": "Time before pre-existing conditions are covered [2]"
            },
        },
        "alternatives": [],
        "comparison_table": [],
        "personalized_reasoning": (
            "For Arjun Sharma aged 34 with diabetes and living in Tier 2 city "
            "on a 6-10 LPA income, this plan provides suitable coverage."
        ),
        "empathy_note": "Managing diabetes can be challenging — this plan has you covered.",
    })
