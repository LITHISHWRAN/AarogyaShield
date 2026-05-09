"""
Tests for recommendation engine grounding and output validation:
- app.recommendation.output_parser  (LLM JSON parsing + citation validation)
- app.recommendation.context_builder (dedup, ranking, numbered context)
- app.recommendation.query_builder  (multi-query generation)

Hallucination prevention focus:
- Invalid citation indices (LLM fabricated reference) → warning generated
- Insufficient profile references → warning generated
- match_score clamping (LLM returned out-of-range value)
- Markdown fence stripping (LLM disobeyed format instruction)
- Deduplication keeps highest-scoring chunk when same (policy_id, chunk_index)
  appears from multiple retrieval queries
"""
import json
import pytest

from app.recommendation.output_parser import (
    LLMOutput,
    extract_llm_output,
    validate_citations,
    validate_profile_references,
)
from app.recommendation.context_builder import (
    ContextChunk,
    build_numbered_context,
    resolve_policy_id,
)
from app.recommendation.query_builder import build_retrieval_queries
from app.modules.recommendations.schemas import UserProfile


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_rec(**kwargs) -> dict:
    defaults = {
        "policy_name": "Star Health Optima",
        "insurer": "Star Health Insurance",
        "match_score": 0.80,
        "coverage_highlights": ["Hospitalisation covered [1]"],
        "exclusions_noted": [],
        "best_for": "Families with pre-existing conditions",
        "citations": [1],
        "jargon_definitions": {},
    }
    return {**defaults, **kwargs}


def _make_llm_json(top_rec: dict | None = None, alternatives: list | None = None) -> str:
    return json.dumps({
        "top_recommendation": top_rec or _make_rec(),
        "alternatives": alternatives or [],
        "comparison_table": [],
        "personalized_reasoning": (
            "For Arjun Sharma aged 34 with diabetes in Tier 2 on 6-10 LPA income."
        ),
        "empathy_note": "We understand living with diabetes is challenging.",
    })


def _make_chunk(index: int, policy_id: str = "p1", policy_name: str = "Star Optima",
                insurer: str = "Star Health", chunk_index: int = 0,
                score: float = 0.9) -> ContextChunk:
    return ContextChunk(
        index=index, policy_id=policy_id, policy_name=policy_name,
        insurer=insurer, chunk_index=chunk_index,
        text=f"Policy text for chunk {chunk_index}.", score=score,
    )


# ─────────────────────────────────────────────────────────────────────────────
# TestExtractLLMOutput — parsing and structural validation
# ─────────────────────────────────────────────────────────────────────────────

class TestExtractLLMOutput:

    def test_valid_json_parses_to_llm_output(self, valid_llm_json_str):
        result = extract_llm_output(valid_llm_json_str)
        assert isinstance(result, LLMOutput)
        assert result.top_recommendation.policy_name == "Star Health Optima"

    def test_match_score_returned_correctly(self, valid_llm_json_str):
        result = extract_llm_output(valid_llm_json_str)
        assert result.top_recommendation.match_score == pytest.approx(0.87)

    def test_citations_returned_as_sorted_list(self, valid_llm_json_str):
        result = extract_llm_output(valid_llm_json_str)
        assert result.top_recommendation.citations == [1, 2]

    def test_markdown_json_fence_stripped(self):
        """LLM sometimes wraps JSON in ```json ... ``` despite instructions."""
        raw = "```json\n" + _make_llm_json() + "\n```"
        result = extract_llm_output(raw)
        assert result.top_recommendation.policy_name == "Star Health Optima"

    def test_plain_code_fence_stripped(self):
        raw = "```\n" + _make_llm_json() + "\n```"
        result = extract_llm_output(raw)
        assert isinstance(result, LLMOutput)

    def test_trailing_text_after_json_truncated(self):
        """LLM sometimes appends text after the closing brace."""
        raw = _make_llm_json() + "\n\nSome trailing commentary."
        result = extract_llm_output(raw)
        assert isinstance(result, LLMOutput)

    def test_match_score_above_1_clamped_to_1(self):
        """LLM returned 1.5 — must be clamped to 1.0."""
        raw = _make_llm_json(top_rec=_make_rec(match_score=1.5))
        result = extract_llm_output(raw)
        assert result.top_recommendation.match_score == pytest.approx(1.0)

    def test_match_score_below_0_clamped_to_0(self):
        raw = _make_llm_json(top_rec=_make_rec(match_score=-0.3))
        result = extract_llm_output(raw)
        assert result.top_recommendation.match_score == pytest.approx(0.0)

    def test_match_score_at_boundary_1_allowed(self):
        raw = _make_llm_json(top_rec=_make_rec(match_score=1.0))
        result = extract_llm_output(raw)
        assert result.top_recommendation.match_score == pytest.approx(1.0)

    def test_match_score_at_boundary_0_allowed(self):
        raw = _make_llm_json(top_rec=_make_rec(match_score=0.0))
        result = extract_llm_output(raw)
        assert result.top_recommendation.match_score == pytest.approx(0.0)

    def test_duplicate_citations_deduplicated_and_sorted(self):
        """LLM returned [3, 1, 3, 2, 1] — must deduplicate to [1, 2, 3]."""
        raw = _make_llm_json(top_rec=_make_rec(citations=[3, 1, 3, 2, 1]))
        result = extract_llm_output(raw)
        assert result.top_recommendation.citations == [1, 2, 3]

    def test_invalid_json_raises_exception(self):
        with pytest.raises(Exception):
            extract_llm_output("this is not json at all {")

    def test_missing_required_field_raises(self):
        """top_recommendation is required — missing it must raise validation error."""
        raw = json.dumps({
            "alternatives": [],
            "comparison_table": [],
            "personalized_reasoning": "Some reasoning.",
            "empathy_note": "Some empathy.",
        })
        with pytest.raises(Exception):
            extract_llm_output(raw)

    def test_empty_alternatives_is_valid(self):
        raw = _make_llm_json(alternatives=[])
        result = extract_llm_output(raw)
        assert result.alternatives == []

    def test_multiple_alternatives_parsed(self):
        alts = [_make_rec(policy_name=f"Plan {i}", citations=[1]) for i in range(3)]
        raw = _make_llm_json(alternatives=alts)
        result = extract_llm_output(raw)
        assert len(result.alternatives) == 3

    def test_jargon_definitions_parsed_correctly(self):
        rec = _make_rec(jargon_definitions={"waiting period": "Time before coverage starts [1]"})
        result = extract_llm_output(_make_llm_json(top_rec=rec))
        assert "waiting period" in result.top_recommendation.jargon_definitions


# ─────────────────────────────────────────────────────────────────────────────
# TestValidateCitations — hallucination prevention: citation index checks
# ─────────────────────────────────────────────────────────────────────────────

class TestValidateCitations:
    """
    validate_citations prevents the LLM from referencing excerpts that do not
    exist in the retrieved context.  A citation of [0] or [N+1] means the LLM
    invented a source reference — this is the primary hallucination vector.
    """

    def test_valid_citations_produce_no_warnings(self, sample_context_chunks):
        """Citations [1], [2], [3] all exist in a 3-chunk context."""
        output = extract_llm_output(_make_llm_json(top_rec=_make_rec(citations=[1, 2, 3])))
        warnings = validate_citations(output, sample_context_chunks)
        assert warnings == []

    def test_citation_zero_is_out_of_range(self, sample_context_chunks):
        """[0] is below the 1-based minimum — LLM invented this reference."""
        output = extract_llm_output(_make_llm_json(top_rec=_make_rec(citations=[0])))
        warnings = validate_citations(output, sample_context_chunks)
        assert len(warnings) == 1
        assert "[0]" in warnings[0]

    def test_citation_above_max_index_is_out_of_range(self, sample_context_chunks):
        """Context has 3 chunks; [4] does not exist."""
        output = extract_llm_output(_make_llm_json(top_rec=_make_rec(citations=[4])))
        warnings = validate_citations(output, sample_context_chunks)
        assert len(warnings) == 1
        assert "[4]" in warnings[0]

    def test_citation_exactly_at_max_index_is_valid(self, sample_context_chunks):
        """Context has 3 chunks; [3] is the last valid index."""
        output = extract_llm_output(_make_llm_json(top_rec=_make_rec(citations=[3])))
        warnings = validate_citations(output, sample_context_chunks)
        assert warnings == []

    def test_empty_citations_produce_no_warnings(self, sample_context_chunks):
        """No citations is not a hallucination — it's a lack of grounding (different issue)."""
        output = extract_llm_output(_make_llm_json(top_rec=_make_rec(citations=[])))
        warnings = validate_citations(output, sample_context_chunks)
        assert warnings == []

    def test_alternative_with_invalid_citation_warns(self, sample_context_chunks):
        """Invalid citation in an alternative also triggers a warning."""
        alt = _make_rec(policy_name="HDFC Plan", citations=[99])
        output = extract_llm_output(_make_llm_json(alternatives=[alt]))
        warnings = validate_citations(output, sample_context_chunks)
        assert any("[99]" in w for w in warnings)

    def test_multiple_invalid_citations_each_warn(self, sample_context_chunks):
        output = extract_llm_output(_make_llm_json(top_rec=_make_rec(citations=[0, 4, 99])))
        warnings = validate_citations(output, sample_context_chunks)
        assert len(warnings) == 3

    def test_empty_context_any_positive_citation_warns(self):
        """If no chunks were retrieved, citation [1] is also invalid."""
        output = extract_llm_output(_make_llm_json(top_rec=_make_rec(citations=[1])))
        warnings = validate_citations(output, context_chunks=[])
        assert len(warnings) == 1

    def test_both_top_and_alternative_invalid_both_warn(self, sample_context_chunks):
        """Warnings are generated independently for top_recommendation and alternatives."""
        top = _make_rec(citations=[99])
        alt = _make_rec(policy_name="Other Plan", citations=[0])
        output = extract_llm_output(_make_llm_json(top_rec=top, alternatives=[alt]))
        warnings = validate_citations(output, sample_context_chunks)
        assert len(warnings) == 2


# ─────────────────────────────────────────────────────────────────────────────
# TestValidateProfileReferences — personalisation enforcement
# ─────────────────────────────────────────────────────────────────────────────

class TestValidateProfileReferences:
    """
    validate_profile_references ensures the LLM actually referenced the user's
    specific details, not just generated generic advice.  Generic advice that
    ignores the user profile is a soft form of hallucination (the reasoning is
    not grounded in the user's actual situation).
    """

    PROFILE = {
        "name": "Arjun Sharma",
        "age": 34,
        "lifestyle": "sedentary",
        "pre_existing_conditions": ["diabetes", "hypertension"],
        "financial_band": "6-10 LPA",
        "city_tier": "Tier 2",
    }

    def test_three_or_more_fields_produces_no_warning(self):
        reasoning = (
            "For Arjun Sharma aged 34 with diabetes living in Tier 2 "
            "on 6-10 LPA income, this plan is recommended."
        )
        warnings = validate_profile_references(reasoning, self.PROFILE)
        assert warnings == []

    def test_exactly_two_fields_produces_warning(self):
        """Only age (34) and condition (diabetes) referenced — not enough."""
        reasoning = "For a 34-year-old with diabetes, this plan covers pre-existing diseases."
        warnings = validate_profile_references(reasoning, self.PROFILE)
        assert len(warnings) == 1
        assert "2 profile field" in warnings[0]

    def test_zero_fields_produces_warning(self):
        reasoning = "This plan offers excellent coverage and is very affordable."
        warnings = validate_profile_references(reasoning, self.PROFILE)
        assert len(warnings) == 1
        assert "0 profile field" in warnings[0]

    def test_name_detected_via_full_name_match(self):
        """Signal is the full name 'arjun sharma'."""
        reasoning = "For Arjun Sharma with diabetes in a Tier 2 city."
        warnings = validate_profile_references(reasoning, self.PROFILE)
        # name + conditions + city_tier = 3 fields → no warning
        assert warnings == []

    def test_age_detected_via_numeric_string(self):
        """Age signal is '34' — the string representation."""
        reasoning = "At 34, with diabetes and living in Tier 2, this plan suits."
        warnings = validate_profile_references(reasoning, self.PROFILE)
        assert warnings == []

    def test_age_detected_via_year_keyword(self):
        """' year' is also an age signal."""
        reasoning = "A 34 year old with diabetes in Tier 2 should choose this."
        warnings = validate_profile_references(reasoning, self.PROFILE)
        assert warnings == []

    def test_condition_detected_via_substring(self):
        """'diabetes' is a signal for pre_existing_conditions."""
        reasoning = "Given diabetes management needs and Tier 2 location on 6-10 LPA."
        warnings = validate_profile_references(reasoning, self.PROFILE)
        # conditions + city_tier + financial_band = 3 fields → no warning
        assert warnings == []

    def test_lpa_abbreviation_detected(self):
        """'lpa' is a signal for financial_band."""
        reasoning = "For someone earning in the 6-10 LPA range with diabetes in Tier 2."
        warnings = validate_profile_references(reasoning, self.PROFILE)
        assert warnings == []

    def test_tier_keyword_detected(self):
        """'tier' is a signal for city_tier."""
        reasoning = "For a 34-year-old with diabetes in a Tier 2 city on 6-10 LPA."
        warnings = validate_profile_references(reasoning, self.PROFILE)
        assert warnings == []

    def test_lifestyle_signal_detected(self):
        """The lifestyle value 'sedentary' must appear verbatim."""
        reasoning = "Given sedentary lifestyle and diabetes, this plan is appropriate."
        profile = {**self.PROFILE, "age": 99, "city_tier": "Unknown", "financial_band": "Unknown"}
        # sedentary + conditions only = 2 fields — not enough alone
        warnings = validate_profile_references(reasoning, profile)
        # sedentary (lifestyle) + diabetes (conditions) = 2 fields → warning
        assert len(warnings) == 1

    def test_empty_conditions_list_does_not_crash(self):
        profile = {**self.PROFILE, "pre_existing_conditions": []}
        reasoning = "For Arjun Sharma aged 34 in Tier 2."
        warnings = validate_profile_references(reasoning, profile)
        # name + age + city_tier = 3 fields → no warning
        assert warnings == []

    def test_profile_without_name_still_works(self):
        profile = {**self.PROFILE, "name": ""}
        reasoning = "Aged 34 with diabetes in Tier 2 on 6-10 LPA income."
        warnings = validate_profile_references(reasoning, profile)
        # age + conditions + city_tier = 3 fields → no warning
        assert warnings == []


# ─────────────────────────────────────────────────────────────────────────────
# TestBuildNumberedContext — retrieval deduplication and ranking
# ─────────────────────────────────────────────────────────────────────────────

class TestBuildNumberedContext:

    def test_empty_input_returns_empty_results(self):
        chunks, context_str = build_numbered_context([])
        assert chunks == []
        assert context_str == ""

    def test_single_chunk_indexed_at_1(self):
        raw = [{"policy_id": "p1", "policy_name": "Plan A", "insurer": "Insurer X",
                "chunk_index": 0, "text": "Some coverage text.", "score": 0.9}]
        chunks, _ = build_numbered_context(raw)
        assert len(chunks) == 1
        assert chunks[0].index == 1

    def test_multiple_chunks_indexed_consecutively(self, sample_raw_chunks):
        chunks, _ = build_numbered_context(sample_raw_chunks)
        assert [c.index for c in chunks] == list(range(1, len(chunks) + 1))

    def test_deduplication_keeps_highest_score_for_same_key(self):
        """Same (policy_id, chunk_index) retrieved by two queries with different scores."""
        raw = [
            {"policy_id": "p1", "policy_name": "Plan A", "insurer": "X",
             "chunk_index": 0, "text": "Low-score version.", "score": 0.5},
            {"policy_id": "p1", "policy_name": "Plan A", "insurer": "X",
             "chunk_index": 0, "text": "High-score version.", "score": 0.9},
        ]
        chunks, _ = build_numbered_context(raw)
        assert len(chunks) == 1
        assert chunks[0].score == pytest.approx(0.9)
        assert "High-score" in chunks[0].text

    def test_deduplication_different_chunk_index_kept_separately(self):
        """Same policy_id but different chunk_index → two chunks retained."""
        raw = [
            {"policy_id": "p1", "policy_name": "Plan A", "insurer": "X",
             "chunk_index": 0, "text": "Chunk zero.", "score": 0.9},
            {"policy_id": "p1", "policy_name": "Plan A", "insurer": "X",
             "chunk_index": 1, "text": "Chunk one.", "score": 0.8},
        ]
        chunks, _ = build_numbered_context(raw)
        assert len(chunks) == 2

    def test_deduplication_different_policy_id_kept_separately(self):
        """Different policy_id even with same chunk_index → two chunks retained."""
        raw = [
            {"policy_id": "p1", "policy_name": "Plan A", "insurer": "X",
             "chunk_index": 0, "text": "Plan A text.", "score": 0.9},
            {"policy_id": "p2", "policy_name": "Plan B", "insurer": "Y",
             "chunk_index": 0, "text": "Plan B text.", "score": 0.8},
        ]
        chunks, _ = build_numbered_context(raw)
        assert len(chunks) == 2

    def test_chunks_ranked_by_score_descending(self):
        raw = [
            {"policy_id": "p1", "chunk_index": 0, "text": "Low",  "score": 0.5,
             "policy_name": "A", "insurer": "X"},
            {"policy_id": "p2", "chunk_index": 0, "text": "High", "score": 0.9,
             "policy_name": "B", "insurer": "Y"},
            {"policy_id": "p3", "chunk_index": 0, "text": "Mid",  "score": 0.7,
             "policy_name": "C", "insurer": "Z"},
        ]
        chunks, _ = build_numbered_context(raw)
        assert chunks[0].score == pytest.approx(0.9)
        assert chunks[1].score == pytest.approx(0.7)
        assert chunks[2].score == pytest.approx(0.5)

    def test_context_string_contains_index_markers(self, sample_raw_chunks):
        _, context_str = build_numbered_context(sample_raw_chunks)
        assert "[1]" in context_str
        assert "[2]" in context_str
        assert "[3]" in context_str

    def test_context_string_contains_policy_and_insurer(self, sample_raw_chunks):
        _, context_str = build_numbered_context(sample_raw_chunks)
        assert "Star Health Optima" in context_str
        assert "Star Health Insurance" in context_str

    def test_context_string_contains_chunk_text(self, sample_raw_chunks):
        _, context_str = build_numbered_context(sample_raw_chunks)
        assert "hospitalisation expenses" in context_str

    def test_context_string_separates_chunks_with_delimiter(self, sample_raw_chunks):
        _, context_str = build_numbered_context(sample_raw_chunks)
        assert "---" in context_str

    def test_missing_optional_fields_use_defaults(self):
        """policy_name and insurer are optional in raw Qdrant results."""
        raw = [{"policy_id": "p1", "chunk_index": 0,
                "text": "Some text.", "score": 0.8}]
        chunks, _ = build_numbered_context(raw)
        assert chunks[0].policy_name == "Unknown Policy"
        assert chunks[0].insurer == "Unknown Insurer"


# ─────────────────────────────────────────────────────────────────────────────
# TestResolvePolicyId
# ─────────────────────────────────────────────────────────────────────────────

class TestResolvePolicyId:

    def test_exact_name_match_returns_id(self, sample_context_chunks):
        pid = resolve_policy_id("Star Health Optima", sample_context_chunks)
        assert pid == "pol-star-001"

    def test_case_insensitive_match(self, sample_context_chunks):
        pid = resolve_policy_id("STAR HEALTH OPTIMA", sample_context_chunks)
        assert pid == "pol-star-001"

    def test_no_match_returns_unknown(self, sample_context_chunks):
        pid = resolve_policy_id("Non-existent Policy Name XYZ", sample_context_chunks)
        assert pid == "unknown"

    def test_second_policy_resolved_correctly(self, sample_context_chunks):
        pid = resolve_policy_id("HDFC Optima Restore", sample_context_chunks)
        assert pid == "pol-hdfc-001"

    def test_empty_chunk_list_returns_unknown(self):
        pid = resolve_policy_id("Any Policy", [])
        assert pid == "unknown"


# ─────────────────────────────────────────────────────────────────────────────
# TestBuildRetrievalQueries — retrieval query generation
# ─────────────────────────────────────────────────────────────────────────────

class TestBuildRetrievalQueries:
    """
    Correct query generation ensures the right sections of policy documents
    are retrieved.  Wrong queries → wrong chunks → hallucinated recommendations.
    """

    def test_standard_profile_returns_exactly_3_queries(self, standard_profile):
        queries = build_retrieval_queries(standard_profile)
        assert len(queries) == 3

    def test_smoker_profile_returns_4_queries(self, smoker_profile):
        """Smoker is a non-standard lifestyle → adds lifestyle-hazard query."""
        queries = build_retrieval_queries(smoker_profile)
        assert len(queries) == 4

    def test_athlete_profile_returns_4_queries(self, athlete_profile):
        queries = build_retrieval_queries(athlete_profile)
        assert len(queries) == 4

    def test_sedentary_profile_returns_3_queries(self, standard_profile):
        """Sedentary is a standard lifestyle → no extra query."""
        assert standard_profile.lifestyle == "sedentary"
        queries = build_retrieval_queries(standard_profile)
        assert len(queries) == 3

    def test_active_lifestyle_returns_3_queries(self, standard_profile):
        from app.modules.recommendations.schemas import UserProfile
        profile = UserProfile(
            name="Test", age=30, lifestyle="active",
            pre_existing_conditions=[], financial_band="6-10 LPA",
            city_tier="Tier 1", family_size=1,
        )
        queries = build_retrieval_queries(profile)
        assert len(queries) == 3

    def test_family_floater_in_queries_for_family_size_gt_1(self, standard_profile):
        """family_size=3 → 'family floater' must appear in coverage and premium queries."""
        assert standard_profile.family_size > 1
        queries = build_retrieval_queries(standard_profile)
        floater_queries = [q for q in queries if "family floater" in q]
        assert len(floater_queries) >= 2

    def test_individual_in_queries_for_family_size_1(self, smoker_profile):
        assert smoker_profile.family_size == 1
        queries = build_retrieval_queries(smoker_profile)
        individual_queries = [q for q in queries if "individual" in q]
        assert len(individual_queries) >= 1

    def test_conditions_present_in_coverage_query(self, standard_profile):
        queries = build_retrieval_queries(standard_profile)
        coverage_query = queries[0]
        assert "diabetes" in coverage_query or "hypertension" in coverage_query

    def test_conditions_present_in_exclusion_query(self, standard_profile):
        queries = build_retrieval_queries(standard_profile)
        exclusion_query = queries[1]
        assert "diabetes" in exclusion_query or "hypertension" in exclusion_query

    def test_no_conditions_uses_placeholder_text(self, smoker_profile):
        """Profile with no conditions uses 'no pre-existing conditions' as the placeholder."""
        assert smoker_profile.pre_existing_conditions == []
        queries = build_retrieval_queries(smoker_profile)
        assert any("no pre-existing conditions" in q for q in queries)

    def test_financial_band_in_premium_query(self, standard_profile):
        queries = build_retrieval_queries(standard_profile)
        premium_query = queries[2]
        assert standard_profile.financial_band in premium_query

    def test_city_tier_in_premium_query(self, standard_profile):
        queries = build_retrieval_queries(standard_profile)
        premium_query = queries[2]
        assert standard_profile.city_tier in premium_query

    def test_age_in_coverage_query(self, standard_profile):
        queries = build_retrieval_queries(standard_profile)
        coverage_query = queries[0]
        assert str(standard_profile.age) in coverage_query

    def test_lifestyle_in_4th_query_for_smoker(self, smoker_profile):
        queries = build_retrieval_queries(smoker_profile)
        assert len(queries) == 4
        lifestyle_query = queries[3]
        assert smoker_profile.lifestyle in lifestyle_query

    def test_all_queries_are_non_empty_strings(self, standard_profile):
        queries = build_retrieval_queries(standard_profile)
        for q in queries:
            assert isinstance(q, str)
            assert len(q.strip()) > 0
