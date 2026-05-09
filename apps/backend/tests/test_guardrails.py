"""
Tests for chat safety and intent routing:
- app.chat.guardrails  (input + output safety checks)
- app.chat.classifier  (intent classification)

Guardrail focus:
- Medical advice requests blocked at input
- Sensitive data (Aadhar, PAN) blocked at input
- Medical advice in LLM response blocked at output
- Insurance questions that mention medical context are NOT blocked
- Off-topic messages classified correctly

Classifier focus:
- Greeting detection (prefix match)
- Jargon definition pattern
- Medical intent without insurance signal → OUT_OF_SCOPE
- Medical intent with insurance signal → POLICY_QUESTION (allowed through)
- Off-topic without insurance signal → OUT_OF_SCOPE
- Off-topic with insurance signal → POLICY_QUESTION
- Recommendation followup signals
- Default fallback to GENERAL_INSURANCE
"""
import pytest

from app.chat.guardrails import (
    GuardrailAction,
    check_input,
    check_output,
)
from app.chat.classifier import ChatIntent, classify_intent


# ─────────────────────────────────────────────────────────────────────────────
# TestInputGuardrail — messages that must be blocked before the LLM
# ─────────────────────────────────────────────────────────────────────────────

class TestInputGuardrail:

    # ── Medical advice blocked ────────────────────────────────────────────────

    def test_should_i_take_blocked(self):
        result = check_input("should I take metformin for my diabetes?")
        assert result.blocked is True
        assert result.reason == "medical_advice_request"

    def test_what_medication_should_blocked(self):
        result = check_input("What medication should I take for hypertension?")
        assert result.blocked is True

    def test_which_drug_blocked(self):
        result = check_input("Which drug is best for my condition?")
        assert result.blocked is True

    def test_diagnose_me_blocked(self):
        result = check_input("Can you diagnose me based on my symptoms?")
        assert result.blocked is True

    def test_am_i_suffering_blocked(self):
        result = check_input("Am I suffering from diabetes?")
        assert result.blocked is True

    def test_correct_dosage_blocked(self):
        result = check_input("What is the correct dosage for insulin?")
        assert result.blocked is True

    def test_case_insensitive_medical_block(self):
        result = check_input("SHOULD I TAKE aspirin daily?")
        assert result.blocked is True

    # ── Sensitive data blocked ────────────────────────────────────────────────

    def test_12_digit_aadhar_blocked(self):
        result = check_input("My Aadhar number is 123456789012")
        assert result.blocked is True
        assert result.reason == "sensitive_data_in_input"

    def test_spaced_aadhar_blocked(self):
        result = check_input("Aadhar: 1234 5678 9012")
        assert result.blocked is True

    def test_pan_format_blocked(self):
        result = check_input("PAN: ABCDE1234F")
        assert result.blocked is True

    def test_otp_blocked(self):
        result = check_input("otp is: 123456")
        assert result.blocked is True

    def test_credit_card_number_blocked(self):
        result = check_input("my credit card number is here")
        assert result.blocked is True

    # ── Legitimate messages allowed ───────────────────────────────────────────

    def test_policy_question_allowed(self):
        result = check_input("Does my policy cover diabetes medication costs?")
        assert result.blocked is False

    def test_jargon_question_allowed(self):
        result = check_input("What is a waiting period?")
        assert result.blocked is False

    def test_general_insurance_allowed(self):
        result = check_input("How do I file a cashless claim?")
        assert result.blocked is False

    def test_greeting_allowed(self):
        result = check_input("Hello, I need help with my insurance.")
        assert result.blocked is False

    def test_condition_mention_in_coverage_context_allowed(self):
        """Asking what the POLICY covers for a condition is NOT medical advice."""
        result = check_input("What does my policy cover for hypertension hospitalisation?")
        assert result.blocked is False

    def test_empty_message_allowed(self):
        result = check_input("")
        assert result.blocked is False

    def test_safe_response_present_when_blocked(self):
        result = check_input("should I take aspirin?")
        assert result.safe_response != ""
        assert len(result.safe_response) > 20

    def test_action_enum_on_allow(self):
        result = check_input("What is my premium?")
        assert result.action == GuardrailAction.ALLOW

    def test_action_enum_on_block(self):
        result = check_input("should I take metformin?")
        assert result.action == GuardrailAction.BLOCK


# ─────────────────────────────────────────────────────────────────────────────
# TestOutputGuardrail — LLM responses that must be replaced
# ─────────────────────────────────────────────────────────────────────────────

class TestOutputGuardrail:

    # ── Medical advice in output blocked ─────────────────────────────────────

    def test_you_should_take_this_medication_blocked(self):
        response = "You should take this medication twice daily for best results."
        result = check_output(response)
        assert result.blocked is True
        assert result.reason == "medical_advice_in_response"

    def test_correct_dosage_is_blocked(self):
        response = "The correct dosage is 500mg twice a day."
        result = check_output(response)
        assert result.blocked is True

    def test_i_recommend_this_drug_blocked(self):
        response = "I recommend this drug for controlling your blood sugar."
        result = check_output(response)
        assert result.blocked is True

    def test_take_N_mg_of_blocked(self):
        response = "Take 50mg of this supplement to manage your condition."
        result = check_output(response)
        assert result.blocked is True

    def test_case_insensitive_output_block(self):
        response = "YOU SHOULD TAKE THIS MEDICATION every morning."
        result = check_output(response)
        assert result.blocked is True

    # ── Legitimate LLM responses allowed ─────────────────────────────────────

    def test_policy_explanation_allowed(self):
        response = (
            "Your Star Health Optima plan covers hospitalisation for diabetes "
            "after the 2-year waiting period [1]. The room rent sub-limit is "
            "INR 4,000 per day [2]."
        )
        result = check_output(response)
        assert result.blocked is False

    def test_jargon_definition_allowed(self):
        response = (
            "A waiting period is the time after policy purchase before "
            "pre-existing conditions are covered [1]. For your plan, this is 2 years."
        )
        result = check_output(response)
        assert result.blocked is False

    def test_coverage_query_response_allowed(self):
        response = "Your policy does not cover cosmetic procedures [3]."
        result = check_output(response)
        assert result.blocked is False

    def test_consult_doctor_phrase_without_advice_allowed(self):
        """'Consult a doctor' alone is fine — it's a redirect, not advice."""
        response = "For medical questions, please consult a qualified doctor."
        result = check_output(response)
        assert result.blocked is False

    def test_safe_response_provided_when_blocked(self):
        response = "I recommend this drug for your condition."
        result = check_output(response)
        assert result.safe_response != ""

    def test_empty_response_allowed(self):
        result = check_output("")
        assert result.blocked is False


# ─────────────────────────────────────────────────────────────────────────────
# TestChatClassifier — intent classification accuracy
# ─────────────────────────────────────────────────────────────────────────────

class TestChatClassifier:

    # ── Greetings ─────────────────────────────────────────────────────────────

    def test_hi_is_greeting(self):
        assert classify_intent("hi") == ChatIntent.GREETING

    def test_hello_is_greeting(self):
        assert classify_intent("Hello! Can you help me?") == ChatIntent.GREETING

    def test_good_morning_is_greeting(self):
        assert classify_intent("Good morning") == ChatIntent.GREETING

    def test_thanks_is_greeting(self):
        assert classify_intent("Thanks for the help") == ChatIntent.GREETING

    def test_bye_is_greeting(self):
        assert classify_intent("bye") == ChatIntent.GREETING

    def test_greeting_case_insensitive(self):
        assert classify_intent("HELLO") == ChatIntent.GREETING

    # ── Jargon definitions ────────────────────────────────────────────────────

    def test_what_is_waiting_period(self):
        assert classify_intent("What is a waiting period?") == ChatIntent.JARGON_DEFINITION

    def test_what_is_copayment(self):
        assert classify_intent("What is co-payment in insurance?") == ChatIntent.JARGON_DEFINITION

    def test_define_sublimit(self):
        assert classify_intent("Can you define sub-limit?") == ChatIntent.JARGON_DEFINITION

    def test_explain_ncb(self):
        assert classify_intent("Explain NCB") == ChatIntent.JARGON_DEFINITION

    def test_meaning_of_sum_insured(self):
        assert classify_intent("What's the meaning of sum insured?") == ChatIntent.JARGON_DEFINITION

    def test_what_is_cashless(self):
        assert classify_intent("What is cashless hospitalisation?") == ChatIntent.JARGON_DEFINITION

    def test_what_is_tpa(self):
        assert classify_intent("What does TPA mean?") == ChatIntent.JARGON_DEFINITION

    def test_what_is_premium(self):
        assert classify_intent("What is a premium in health insurance?") == ChatIntent.JARGON_DEFINITION

    # ── Out of scope: medical intent without insurance signal ─────────────────

    def test_medication_query_without_policy_context_is_out_of_scope(self):
        assert classify_intent("What medication should I take for fever?") == ChatIntent.OUT_OF_SCOPE

    def test_diagnose_me_is_out_of_scope(self):
        assert classify_intent("diagnose me based on my symptoms") == ChatIntent.OUT_OF_SCOPE

    def test_cure_for_is_out_of_scope(self):
        assert classify_intent("What is the cure for hypertension?") == ChatIntent.OUT_OF_SCOPE

    # ── Medical intent WITH insurance signal — must NOT be blocked ────────────

    def test_coverage_for_medication_is_policy_question(self):
        """User asking what INSURANCE covers for medication = valid insurance question."""
        intent = classify_intent("Does my policy cover diabetes medication costs?")
        assert intent == ChatIntent.POLICY_QUESTION

    def test_which_doctor_with_cashless_is_policy_question(self):
        intent = classify_intent("Which doctor can I visit for cashless treatment?")
        assert intent == ChatIntent.POLICY_QUESTION

    # ── Out of scope: off-topic ───────────────────────────────────────────────

    def test_cricket_is_out_of_scope(self):
        assert classify_intent("Who won the IPL?") == ChatIntent.OUT_OF_SCOPE

    def test_movie_without_insurance_is_out_of_scope(self):
        assert classify_intent("Tell me about the latest movie releases") == ChatIntent.OUT_OF_SCOPE

    def test_crypto_is_out_of_scope(self):
        assert classify_intent("What is bitcoin worth?") == ChatIntent.OUT_OF_SCOPE

    def test_programming_is_out_of_scope(self):
        assert classify_intent("How do I write a Python function?") == ChatIntent.OUT_OF_SCOPE

    # ── Off-topic WITH insurance signal — route to policy question ────────────

    def test_sports_with_insurance_is_policy_question(self):
        """'Sports' is off-topic but 'policy' is an insurance signal."""
        intent = classify_intent("Does my policy cover sports injuries?")
        assert intent == ChatIntent.POLICY_QUESTION

    # ── Recommendation followup ───────────────────────────────────────────────

    def test_that_policy_is_followup_with_recommendations(self):
        intent = classify_intent("Tell me more about that policy", has_recommendations=True)
        assert intent == ChatIntent.RECOMMENDATION_FOLLOWUP

    def test_star_health_reference_is_followup_with_recommendations(self):
        intent = classify_intent(
            "What does Star Health plan cover for room rent?",
            has_recommendations=True,
        )
        assert intent == ChatIntent.RECOMMENDATION_FOLLOWUP

    def test_hdfc_reference_is_followup_with_recommendations(self):
        intent = classify_intent(
            "What is the waiting period for HDFC plan?",
            has_recommendations=True,
        )
        assert intent == ChatIntent.RECOMMENDATION_FOLLOWUP

    def test_recommendation_followup_requires_has_recommendations_flag(self):
        """Without has_recommendations=True, 'that policy' is not classified as followup."""
        intent = classify_intent("Tell me more about that policy", has_recommendations=False)
        assert intent != ChatIntent.RECOMMENDATION_FOLLOWUP

    # ── Policy questions ──────────────────────────────────────────────────────

    def test_coverage_question_is_policy_question(self):
        assert classify_intent("What does hospitalisation coverage include?") == ChatIntent.POLICY_QUESTION

    def test_claim_question_is_policy_question(self):
        assert classify_intent("How do I file a claim?") == ChatIntent.POLICY_QUESTION

    def test_exclusion_question_is_policy_question(self):
        assert classify_intent("What are the exclusions in my plan?") == ChatIntent.POLICY_QUESTION

    def test_premium_question_is_policy_question(self):
        assert classify_intent("How is my premium calculated?") == ChatIntent.POLICY_QUESTION

    # ── General insurance (default) ───────────────────────────────────────────

    def test_vague_question_defaults_to_general_insurance(self):
        intent = classify_intent("How does health insurance work in India?")
        # May be POLICY_QUESTION (if 'insur' signal is found) or GENERAL_INSURANCE
        assert intent in (ChatIntent.POLICY_QUESTION, ChatIntent.GENERAL_INSURANCE)

    def test_truly_ambiguous_defaults_to_general_insurance(self):
        intent = classify_intent("I need some help please")
        assert intent == ChatIntent.GENERAL_INSURANCE

    def test_empty_message_defaults_to_general_insurance(self):
        intent = classify_intent("")
        assert intent == ChatIntent.GENERAL_INSURANCE

    # ── Ordering: more-specific patterns take precedence ─────────────────────

    def test_greeting_prefix_wins_over_insurance_content(self):
        """'Hello, what does my policy cover?' — greeting detected first (prefix match)."""
        intent = classify_intent("Hello, what does my policy cover?")
        assert intent == ChatIntent.GREETING

    def test_jargon_wins_over_policy_question_for_definition_request(self):
        """'What is a waiting period?' is JARGON, not POLICY_QUESTION."""
        intent = classify_intent("What is a waiting period and how does it affect my claim?")
        assert intent == ChatIntent.JARGON_DEFINITION
