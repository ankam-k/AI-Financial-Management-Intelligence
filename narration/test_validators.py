"""The validators — hallucination prevention, tested directly.

These are the controls. The prompt is a request; this file tests the thing
that actually decides whether a generation is used.
"""

from __future__ import annotations

import pytest

from app.analysis.models import Insight, InsightTier
from app.narration.payload import allowed_numbers, build_payload
from app.narration.validators import (
    check_advice,
    check_lexical,
    check_provenance,
    check_shape,
    validate,
)

CLEAN = {
    "observation": "Your food spending was higher in weeks without exercise.",
    "evidence": "Weeks with exercise averaged less than weeks without.",
    "interpretation": "The two are associated, though this does not prove causation.",
    "suggestion": "You may want to watch food spending in low-exercise weeks.",
}


def failures_from(result) -> set[str]:
    return {item.validator for item in result}


class TestProvenance:
    """SRS-7.3 — the mechanism that makes "must not fabricate numbers"
    enforceable rather than merely stated."""

    def test_an_invented_number_is_caught(self) -> None:
        failures = check_provenance(
            {"evidence": "You spent ₹9,999 on coffee."}, allowed={"4120"}
        )

        assert failures and failures[0].validator == "provenance"
        assert "9999" in failures[0].detail

    def test_a_licensed_number_passes(self) -> None:
        assert check_provenance({"evidence": "You spent ₹4,120."}, allowed={"4120"}) == []

    def test_formatting_variants_pass(self) -> None:
        """The model choosing commas is not a fabrication."""
        allowed = {"4120.5"}

        assert check_provenance({"a": "₹4,120.50"}, allowed) == []
        assert check_provenance({"a": "4120.50"}, allowed) == []
        assert check_provenance({"a": "4120.5"}, allowed) == []

    def test_prose_with_no_numbers_passes(self) -> None:
        assert check_provenance({"a": "Your spending rose noticeably."}, set()) == []

    def test_the_failure_names_the_section(self) -> None:
        failures = check_provenance({"interpretation": "About 73% of the time."}, {"49"})

        assert "'interpretation'" in failures[0].detail

    def test_every_offending_section_is_reported(self) -> None:
        failures = check_provenance(
            {"observation": "You spent 111.", "evidence": "Across 222 days."}, set()
        )

        assert len(failures) == 2

    def test_a_real_insight_licenses_its_own_figures(
        self, relationship_insight: Insight
    ) -> None:
        """End-to-end sanity: numbers taken straight from the insight must
        survive the check built from the same insight."""
        payload = build_payload(relationship_insight)
        metrics = relationship_insight.metrics
        text = (
            f"Weeks with exercise: ₹{metrics['group_a']['median_paise'] / 100:,.2f}. "
            f"Across {metrics['group_a']['n']} weeks."
        )

        assert check_provenance({"evidence": text}, allowed_numbers(payload)) == []


class TestLexical:
    """SRS-7.4 — tier-aware, because only T3 is an inference."""

    def test_causal_language_is_rejected_for_a_correlational_claim(self) -> None:
        failures = check_lexical(
            {
                "interpretation": "Your food spending rose because you skipped the gym. "
                "This is an association."
            },
            InsightTier.T3_CORRELATIONAL,
        )

        assert failures and any("because" in f.detail for f in failures)

    @pytest.mark.parametrize(
        "phrase",
        [
            "because",
            "caused",
            "due to",
            "led to",
            "resulted in",
            "as a result of",
            "drives",
            "therefore",
            "the reason",
        ],
    )
    def test_every_banned_connective_is_caught(self, phrase: str) -> None:
        failures = check_lexical(
            {"observation": f"Spending rose {phrase} something. It is associated."},
            InsightTier.T3_CORRELATIONAL,
        )

        assert failures

    def test_the_same_language_is_permitted_for_arithmetic(self) -> None:
        """PDR-036: "your total rose because an annual premium was debited" is
        provable by summation, so T1 is exempt."""
        assert (
            check_lexical(
                {"observation": "Your total rose because a large payment cleared."},
                InsightTier.T1_DESCRIPTIVE,
            )
            == []
        )

    def test_comparative_claims_are_not_exempt(self) -> None:
        """⭐ A period comparison establishes *that* spending moved, never *why*.

        Only T1 is exempt (PDR-036), because a T1 signal carries its largest
        contributing expenses as evidence. Running qwen2.5:7b against a real
        monthly comparison produced "this increase could be due to seasonal
        changes or unexpected expenses" — fluent, plausible, and entirely
        absent from the input.
        """
        failures = check_lexical(
            {"interpretation": "The rise could be due to seasonal changes."},
            InsightTier.T2_COMPARATIVE,
        )

        assert failures and "due to" in failures[0].detail

    def test_a_comparison_needs_no_correlational_framing(self) -> None:
        """The positive-framing requirement is T3-only — there is no
        association to frame in a two-period comparison."""
        assert (
            check_lexical(
                {"interpretation": "The most recent month totalled more than the one before."},
                InsightTier.T2_COMPARATIVE,
            )
            == []
        )

    def test_a_correlational_claim_must_be_visibly_correlational(self) -> None:
        """Absence of banned words is not enough — the framing has to be
        positively present."""
        failures = check_lexical(
            {"interpretation": "Your food spending was higher in those weeks."},
            InsightTier.T3_CORRELATIONAL,
        )

        assert failures and "association" in failures[0].detail

    @pytest.mark.parametrize(
        "phrasing",
        [
            "These are associated with one another.",
            "The two variables are correlated.",
            "Higher spending coincided with those weeks.",
            "This does not prove causation, but the pattern is consistent.",
        ],
    )
    def test_correlational_framing_passes(self, phrasing: str) -> None:
        assert check_lexical({"interpretation": phrasing}, InsightTier.T3_CORRELATIONAL) == []

    @pytest.mark.parametrize(
        "disclaimer",
        [
            "This is an association, not a cause.",
            "The pattern is correlated, rather than a cause of the change.",
            "This does not prove causation; the two are associated.",
            "There is no causal claim here — only an observed association.",
            # qwen2.5:7b's actual phrasing. A narrower verb list rejected it,
            # penalising the exact disclaimer the design tries to elicit.
            "There may be a correlation, but it does not indicate a cause.",
            "The two are associated; this does not establish a cause.",
            "Correlation is not causation — these coincided.",
        ],
    )
    def test_denying_causation_is_not_itself_causal_language(
        self, disclaimer: str
    ) -> None:
        """Scanning naively rejects the exact disclaimer the design wants,
        which pushes generations toward vaguer language than the honest
        phrasing."""
        assert check_lexical({"interpretation": disclaimer}, InsightTier.T3_CORRELATIONAL) == []

    def test_a_disclaimer_does_not_launder_a_causal_claim(self) -> None:
        """The exemption strips complete denial phrases only — it is not a
        prefix that excuses the rest of the sentence."""
        failures = check_lexical(
            {
                "interpretation": "This is not a cause, but skipping the gym caused "
                "your spending to rise. They are associated."
            },
            InsightTier.T3_CORRELATIONAL,
        )

        assert failures and "caused" in failures[0].detail


class TestAdviceGuard:
    """ADR-010 — independent of tier and of the other validators.

    The boundary is PDR-027's: describing recorded history is always
    permitted; directing future capital allocation is always refused.
    """

    @pytest.mark.parametrize(
        "text",
        [
            "You could invest the difference.",
            "Consider a mutual fund for the surplus.",
            "Starting a SIP may help.",
            "You might buy stocks with the savings.",
            "A fixed deposit could work here.",
            "Consider an insurance policy for this.",
            "Refinancing may reduce this cost.",
            "A tax-saving option might suit you.",
            "Your portfolio could absorb this.",
            "Crypto may be worth a look.",
        ],
    )
    def test_prohibited_topics_are_refused(self, text: str) -> None:
        failures = check_advice({"suggestion": text})

        assert failures and failures[0].validator == "advice_guard"

    def test_describing_a_recorded_loan_payment_is_permitted(self) -> None:
        """PDR-027's distinction: this describes history, it does not direct
        capital."""
        assert check_advice(
            {"evidence": "Your largest expense was a loan repayment of ₹20,000."}
        ) == []

    def test_an_insurance_premium_as_an_expense_is_permitted(self) -> None:
        """A bare word ban on "premium" would reject a legitimate expense
        description, so the patterns target the product, not the payment."""
        assert check_advice({"evidence": "An annual premium was debited in June."}) == []

    def test_a_behavioural_suggestion_is_permitted(self) -> None:
        assert check_advice(
            {"suggestion": "Cooking at home more often may reduce food spending."}
        ) == []

    def test_an_unhedged_instruction_is_refused(self) -> None:
        failures = check_advice({"suggestion": "Cook at home. Stop ordering out."})

        assert failures and "instruction" in failures[0].detail

    def test_it_runs_on_every_section_not_just_the_suggestion(self) -> None:
        assert check_advice({"interpretation": "You should invest this surplus."})

    def test_it_is_independent_of_the_other_validators(self) -> None:
        """A generation that already failed provenance is still checked, so
        the recorded reason is complete."""
        sections = {
            "observation": "You saved ₹9,999,999.",
            "evidence": "Put it in a mutual fund.",
            "interpretation": "They are associated.",
        }

        result = validate(sections, tier=InsightTier.T3_CORRELATIONAL, allowed_numbers=set())

        assert {"provenance", "advice_guard"} <= failures_from(result)


class TestShape:
    def test_a_missing_section_is_caught(self) -> None:
        failures = check_shape({"observation": "Fine and long enough."})

        assert len(failures) == 2

    def test_a_stub_section_is_caught(self) -> None:
        assert check_shape({"observation": "ok", "evidence": "x", "interpretation": "y"})

    def test_complete_sections_pass(self) -> None:
        assert check_shape(CLEAN) == []


class TestValidateTogether:
    def test_clean_output_passes_everything(self) -> None:
        assert validate(CLEAN, tier=InsightTier.T3_CORRELATIONAL, allowed_numbers=set()) == []

    def test_all_failures_are_collected_not_just_the_first(self) -> None:
        """Order carries no meaning — any single failure discards — so every
        check runs and the fallback reason is the whole reason."""
        sections = {
            "observation": "Spending rose 42% because of the gym.",
            "evidence": "Consider a SIP.",
            "interpretation": "Yes.",
        }

        result = validate(
            sections, tier=InsightTier.T3_CORRELATIONAL, allowed_numbers=set()
        )

        assert {"provenance", "lexical", "advice_guard", "shape"} <= failures_from(result)

    def test_suggestion_is_optional(self) -> None:
        sections = {key: value for key, value in CLEAN.items() if key != "suggestion"}

        assert validate(sections, tier=InsightTier.T3_CORRELATIONAL, allowed_numbers=set()) == []
