"""The prohibited-topic guard.

ADR-010 makes this an independently testable component with no model
dependency, and this file is that test. Every case here decides whether a
question reaches the rest of the pipeline at all.

The boundary under test is PDR-027's: **describing recorded history is always
permitted; directing future capital allocation is always refused.** That is
why the same product word appears on both lists below.
"""

from __future__ import annotations

import pytest

from app.chat.guard import GuardVerdict, screen_question


class TestDescribingHistoryIsPermitted:
    """⭐ The half of PDR-027 a keyword ban would get wrong."""

    @pytest.mark.parametrize(
        "question",
        [
            "How much did I pay in loan EMIs last quarter?",
            "What did my insurance premium cost this year?",
            "How much have I spent on my credit card?",
            "Show me my tax payments from last month.",
            "What did I spend on property maintenance?",
            "How much went out in EMIs during my trip?",
        ],
    )
    def test_factual_questions_about_products_pass(self, question: str) -> None:
        # Each names a financial product. Each asks only what was recorded.
        assert screen_question(question).verdict is GuardVerdict.PERMITTED

    @pytest.mark.parametrize(
        "question",
        [
            "How much did I spend on food last month?",
            "Which category went up the most?",
            "How has the gym affected my spending?",
            "What happened during exam week?",
            "What should I improve?",
            "Compare this month with last month.",
        ],
    )
    def test_ordinary_questions_pass(self, question: str) -> None:
        assert screen_question(question).verdict is GuardVerdict.PERMITTED

    def test_an_empty_question_is_not_prohibited(self) -> None:
        """Empty is unclear, which is a different refusal handled elsewhere."""
        assert screen_question("   ").verdict is GuardVerdict.PERMITTED


class TestDirectingCapitalIsRefused:
    """The other half. A product plus a directive frame."""

    @pytest.mark.parametrize(
        "question",
        [
            "Should I switch to a cheaper loan?",
            "Should I invest my surplus?",
            "Do you recommend a mutual fund for this?",
            "Is it worth opening a fixed deposit?",
            "Where should I put my savings?",
            "Which fund should I buy?",
            "Would I be better off with a different insurance policy?",
            "Should I start a SIP with what's left over?",
            "Is it a good idea to prepay my mortgage?",
            "What's the best tax saving scheme for me?",
        ],
    )
    def test_advisory_questions_are_refused(self, question: str) -> None:
        result = screen_question(question)

        assert result.verdict is GuardVerdict.PROHIBITED
        assert result.matched, "a refusal records what triggered it"

    @pytest.mark.parametrize(
        "question",
        [
            "What should I invest in?",
            "Where to invest 50000?",
            "Which stock is going up?",
            "Give me a stock tip.",
            "Will the market crash?",
            "Help me plan my retirement.",
            "What portfolio allocation suits me?",
            "Can you give me financial advice?",
        ],
    )
    def test_questions_with_no_descriptive_reading_are_refused(self, question: str) -> None:
        assert screen_question(question).verdict is GuardVerdict.PROHIBITED


class TestTheRefusalIsAudited:
    def test_it_records_why(self) -> None:
        result = screen_question("Should I invest in a mutual fund?")

        assert "capital allocation" in result.detail

    def test_an_unconditional_refusal_is_labelled_differently(self) -> None:
        result = screen_question("Give me a stock tip.")

        assert "forward-looking" in result.detail


class TestAmbiguityResolvesToRefusal:
    """A false refusal costs a session; a false answer is a regulatory event."""

    @pytest.mark.parametrize(
        "question",
        [
            "Should I be putting more into my PPF?",
            "Is my insurance premium worth it?",
            "Should I get a credit card?",
        ],
    )
    def test_a_question_that_could_be_read_either_way_is_refused(
        self, question: str
    ) -> None:
        assert screen_question(question).verdict is GuardVerdict.PROHIBITED

    def test_case_does_not_matter(self) -> None:
        assert screen_question("SHOULD I INVEST IN STOCKS?").verdict is GuardVerdict.PROHIBITED


class TestParaphrasesThatDodgeShouldI:
    """V1.1 hardening: directive frames the first draft of the guard missed.

    The audit found these slipped past layer 1 (defence-in-depth still refused
    them downstream). The guard now catches them at the first gate so its own
    "ambiguity resolves to refusal" promise holds against paraphrase.
    """

    @pytest.mark.parametrize(
        "question",
        [
            "Which stock would you personally choose?",
            "For educational purposes, what stock would you buy?",
            "What would you do with my surplus?",
            "Where would a smart person park spare cash?",
            "Tell me where to allocate 20000.",
            "What would be the smartest investment for me?",
            "Can I afford to gamble 10000 on crypto?",
            "Where to put my money for the best return?",
        ],
    )
    def test_paraphrased_allocation_requests_are_refused(self, question: str) -> None:
        assert screen_question(question).verdict is GuardVerdict.PROHIBITED

    @pytest.mark.parametrize(
        "question",
        [
            # These name a product or capital but only ask what was recorded,
            # or are ordinary affordability questions with no product. The
            # hardening must not sweep them up.
            "How much did I spend on stocks last month?",
            "How much did I put into my savings last month?",
            "Can I afford this trip to Goa?",
            "Where did most of my money go in July?",
        ],
    )
    def test_hardening_does_not_block_legitimate_history(self, question: str) -> None:
        assert screen_question(question).verdict is GuardVerdict.PERMITTED
