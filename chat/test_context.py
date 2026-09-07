"""The context builder — what the model is allowed to see."""

from __future__ import annotations

import json

from app.analysis.engine import AnalysisResult
from app.analysis.models import InsightType
from app.chat.context import MAX_INSIGHTS, MAX_NOTICES, build_context
from app.chat.intents import Intent, capability_for
from app.narration.models import Narration


class TestSelection:
    def test_it_selects_only_what_the_intent_can_be_answered_from(
        self, analysis: AnalysisResult, narrations: dict[str, Narration]
    ) -> None:
        context = build_context(Intent.BUDGET_STATUS, analysis, narrations)
        allowed = set(capability_for(Intent.BUDGET_STATUS))

        assert context.insights
        assert all(insight.type in allowed for insight in context.insights)

    def test_it_leaves_out_the_rest_of_the_run(
        self, analysis: AnalysisResult, narrations: dict[str, Narration]
    ) -> None:
        """⭐ Minimum necessary is a correctness property, not a token saving:
        every number in the context becomes a number the answer is allowed to
        contain."""
        context = build_context(Intent.HABIT_SUMMARY, analysis, narrations)
        types = {insight.type for insight in context.insights}

        assert InsightType.SPENDING_BY_CATEGORY not in types
        assert InsightType.BEHAVIOR_RELATIONSHIP not in types

    def test_it_is_capped(
        self, analysis: AnalysisResult, narrations: dict[str, Narration]
    ) -> None:
        context = build_context(Intent.OVERVIEW, analysis, narrations)

        assert len(context.insights) <= MAX_INSIGHTS

    def test_sufficiency_notices_are_capped_harder(
        self, empty_analysis: AnalysisResult
    ) -> None:
        """One notice per habit all read the same — "X was recorded in 33% of
        weeks". Six of them is the same sentence six times, which buries the
        point rather than making it."""
        context = build_context(Intent.HABIT_RELATIONSHIP, empty_analysis, {})
        notices = [i for i in context.insights if i.type is InsightType.DATA_SUFFICIENCY]

        assert len(notices) <= MAX_NOTICES

    def test_it_attaches_existing_narrations(
        self, analysis: AnalysisResult, narrations: dict[str, Narration]
    ) -> None:
        """Sprint 3 already wrote and validated this prose. Regenerating it
        would be paying twice for the same sentences."""
        context = build_context(Intent.SPENDING_SUMMARY, analysis, narrations)

        assert context.narrations
        assert all(key in narrations for key in context.narrations)

    def test_a_relationship_question_reaches_the_association(
        self, analysis: AnalysisResult, narrations: dict[str, Narration]
    ) -> None:
        context = build_context(Intent.HABIT_RELATIONSHIP, analysis, narrations)

        assert InsightType.BEHAVIOR_RELATIONSHIP in {i.type for i in context.insights}
        assert context.has_correlational_finding is True

    def test_a_spending_question_carries_no_correlational_finding(
        self, analysis: AnalysisResult, narrations: dict[str, Narration]
    ) -> None:
        context = build_context(Intent.SPENDING_SUMMARY, analysis, narrations)

        assert context.has_correlational_finding is False


class TestEmptyContext:
    def test_an_intent_with_nothing_behind_it_yields_an_empty_context(
        self, empty_analysis: AnalysisResult
    ) -> None:
        context = build_context(Intent.EVENT_CONTEXT, empty_analysis, {})

        assert context.is_empty
        assert context.insights == ()

    def test_a_spending_question_is_still_answerable_over_an_empty_window(
        self, empty_analysis: AnalysisResult
    ) -> None:
        """The engine emits SPENDING_TOTAL even for a window with nothing in
        it — zero spending is a fact. "You have no recorded spending" is a
        better answer than a refusal, and the context builder gets there
        without a special case."""
        context = build_context(Intent.SPENDING_SUMMARY, empty_analysis, {})

        assert not context.is_empty
        assert InsightType.SPENDING_TOTAL in {i.type for i in context.insights}

    def test_an_empty_context_still_reports_its_window(
        self, empty_analysis: AnalysisResult
    ) -> None:
        context = build_context(Intent.EVENT_CONTEXT, empty_analysis, {})

        assert context.window["start"] == "2026-06-01"


class TestModelInput:
    def test_it_is_json_serialisable(
        self, analysis: AnalysisResult, narrations: dict[str, Narration]
    ) -> None:
        context = build_context(Intent.CATEGORY_BREAKDOWN, analysis, narrations)

        assert json.loads(json.dumps(context.as_model_input()))

    def test_it_carries_no_database_identifiers(
        self, analysis: AnalysisResult, narrations: dict[str, Narration]
    ) -> None:
        """The model receives finished findings, never the ledger."""
        payload = json.dumps(context_of(analysis, narrations).as_model_input())

        assert "user_id" not in payload
        assert "raw_record" not in payload

    def test_each_finding_carries_its_tier(
        self, analysis: AnalysisResult, narrations: dict[str, Narration]
    ) -> None:
        """The prompt's language rules are tier-dependent, so the tier has to
        travel with the finding."""
        context = build_context(Intent.HABIT_RELATIONSHIP, analysis, narrations)

        for finding in context.as_model_input()["findings"]:
            assert finding["tier"] in {"T1", "T2", "T3"}

    def test_it_includes_the_existing_explanation(
        self, analysis: AnalysisResult, narrations: dict[str, Narration]
    ) -> None:
        context = build_context(Intent.SPENDING_SUMMARY, analysis, narrations)
        findings = context.as_model_input()["findings"]

        assert any(finding["existing_explanation"] for finding in findings)


class TestAllowedNumbers:
    def test_it_licenses_the_selected_insights_figures(
        self, analysis: AnalysisResult, narrations: dict[str, Narration]
    ) -> None:
        context = build_context(Intent.SPENDING_SUMMARY, analysis, narrations)
        total = next(
            i for i in context.insights if i.type is InsightType.SPENDING_TOTAL
        )

        assert str(total.metrics["total_paise"]) in context.allowed_numbers()

    def test_it_does_not_license_an_excluded_insights_figures(
        self, analysis: AnalysisResult, narrations: dict[str, Narration]
    ) -> None:
        """⭐ The selection is a control. A figure from an insight the question
        did not need is a figure the answer may not quote — a plausible
        mix-up would otherwise pass every check."""
        habits = build_context(Intent.HABIT_SUMMARY, analysis, narrations)
        breakdown = next(
            i for i in analysis.insights if i.type is InsightType.SPENDING_BY_CATEGORY
        )

        assert str(breakdown.metrics["top_category_paise"]) not in habits.allowed_numbers()


class TestSummary:
    def test_it_records_what_was_sent(
        self, analysis: AnalysisResult, narrations: dict[str, Narration]
    ) -> None:
        summary = build_context(Intent.BUDGET_STATUS, analysis, narrations).summary()

        assert summary["intent"] == "BUDGET_STATUS"
        assert summary["insight_count"] > 0
        assert summary["allowed_number_count"] > 0
        assert "BUDGET_UTILIZATION" in summary["insight_types"]


def context_of(analysis: AnalysisResult, narrations: dict[str, Narration]):
    return build_context(Intent.CATEGORY_BREAKDOWN, analysis, narrations)
