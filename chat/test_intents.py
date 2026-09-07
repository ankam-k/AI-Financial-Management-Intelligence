"""Intent routing and the capability map."""

from __future__ import annotations

import pytest

from app.analysis.models import InsightType
from app.chat.intents import (
    CAPABILITIES,
    SUPPORTED_EXAMPLES,
    Intent,
    capability_for,
    detect_intent,
)


class TestRouting:
    @pytest.mark.parametrize(
        ("question", "expected"),
        [
            ("How much did I spend this month?", Intent.SPENDING_SUMMARY),
            ("What were my biggest expenses?", Intent.BIGGEST_EXPENSES),
            ("Which category did I spend the most on?", Intent.CATEGORY_BREAKDOWN),
            ("Compare this month with last month.", Intent.PERIOD_COMPARISON),
            ("Which category increased the most?", Intent.PERIOD_COMPARISON),
            ("Why did I overspend this month?", Intent.BUDGET_STATUS),
            ("Am I over budget?", Intent.BUDGET_STATUS),
            ("How is my sleep looking?", Intent.HABIT_SUMMARY),
            ("What's my check-in streak?", Intent.HABIT_SUMMARY),
            ("How has my gym routine affected spending?", Intent.HABIT_RELATIONSHIP),
            ("Which habit has the strongest financial impact?", Intent.HABIT_RELATIONSHIP),
            ("What happened during exam week?", Intent.EVENT_CONTEXT),
            ("Show me my life events.", Intent.EVENT_CONTEXT),
            ("What should I improve?", Intent.IMPROVEMENT),
            ("How can I cut back?", Intent.IMPROVEMENT),
            ("Give me an overview.", Intent.OVERVIEW),
        ],
    )
    def test_every_supported_question_routes(
        self, question: str, expected: Intent
    ) -> None:
        assert detect_intent(question).intent is expected

    def test_every_advertised_example_routes(self) -> None:
        """The starter questions in the UI come from this list. One that did
        not route would be an invitation to a refusal."""
        for example in SUPPORTED_EXAMPLES:
            assert detect_intent(example).is_supported, example

    def test_a_relationship_question_beats_a_habit_question(self) -> None:
        """Rule order matters: "how has the gym affected spending" names a
        habit but asks about an association."""
        assert detect_intent("Has the gym affected my food spending?").intent is (
            Intent.HABIT_RELATIONSHIP
        )

    def test_routing_is_case_insensitive(self) -> None:
        assert detect_intent("HOW MUCH DID I SPEND?").intent is Intent.SPENDING_SUMMARY

    def test_the_matched_rule_is_recorded(self) -> None:
        assert detect_intent("Am I over budget?").matched == "budget"


class TestUnsupportedQuestions:
    @pytest.mark.parametrize(
        "question",
        [
            "What's the weather tomorrow?",
            "Who won the cricket match?",
            "Write me a poem.",
            "What is the capital of France?",
            "asdfghjkl",
        ],
    )
    def test_off_topic_questions_route_nowhere(self, question: str) -> None:
        """Returning nothing is the point. An embedding matcher would always
        find a nearest neighbour, and "I have no finding for this" would stop
        being expressible."""
        match = detect_intent(question)

        assert match.intent is None
        assert match.is_supported is False

    def test_a_too_short_question_routes_nowhere(self) -> None:
        assert detect_intent("hi").intent is None
        assert detect_intent("").intent is None


class TestCapabilityMap:
    def test_every_intent_has_a_capability(self) -> None:
        """An intent with no insight types is a question the system claimed to
        support and cannot ground."""
        for intent in Intent:
            assert CAPABILITIES[intent], intent.value

    def test_capabilities_name_real_insight_types(self) -> None:
        for intent, types in CAPABILITIES.items():
            for insight_type in types:
                assert isinstance(insight_type, InsightType), intent.value

    def test_a_relationship_question_can_reach_a_sufficiency_notice(self) -> None:
        """With no association found, the notice explaining why *is* the
        answer — leaving it out would turn an explanation into silence."""
        assert InsightType.DATA_SUFFICIENCY in capability_for(Intent.HABIT_RELATIONSHIP)

    def test_a_budget_question_can_reach_the_budget_insight(self) -> None:
        assert InsightType.BUDGET_UTILIZATION in capability_for(Intent.BUDGET_STATUS)
