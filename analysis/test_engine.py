"""The engine entry point — composition, determinism, and the run record."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta

import pytest

from app.analysis.engine import ENGINE_VERSION, analyse
from app.analysis.gates import DEFAULT_GATES, GateConfig
from app.analysis.models import InsightTier, InsightType
from app.analysis.window import AnalysisWindow
from app.domain.enums import Category
from tests.analysis.conftest import check_in, dataset, expense, life_event

JUNE = AnalysisWindow(date(2026, 6, 1), date(2026, 6, 30))
QUARTER = AnalysisWindow(date(2026, 4, 1), date(2026, 6, 30))


def rich_dataset(**kwargs):
    """A window with all three streams present."""
    expenses = []
    check_ins = []
    day = QUARTER.start
    index = 0
    while day <= QUARTER.end:
        index += 1
        expenses.append(
            expense(
                day,
                40_000 + (index % 5) * 3_000,
                Category.FOOD_DINING if index % 2 else Category.TRANSPORT,
            )
        )
        check_ins.append(
            check_in(day, exercise=(index % 3 != 0), sleep_minutes=400 + (index % 6) * 10)
        )
        day += timedelta(days=1)

    return dataset(
        window=QUARTER,
        expenses=tuple(expenses),
        check_ins=tuple(check_ins),
        events=(life_event(date(2026, 5, 10), date(2026, 5, 14), title="Goa"),),
        **kwargs,
    )


class TestComposition:
    def test_a_rich_dataset_produces_every_descriptive_family(
        self, now: datetime
    ) -> None:
        result = analyse(rich_dataset(monthly_budget_paise=5_000_000), now)
        produced = {insight.type for insight in result.insights}

        assert {
            InsightType.SPENDING_TOTAL,
            InsightType.SPENDING_BY_CATEGORY,
            InsightType.SPENDING_MONTHLY_COMPARISON,
            InsightType.SPENDING_WEEKLY_COMPARISON,
            InsightType.SPENDING_DAILY_TREND,
            InsightType.BUDGET_UTILIZATION,
            InsightType.HABIT_COMPLETION,
            InsightType.HABIT_STREAK,
            InsightType.HABIT_SLEEP_AVERAGE,
            InsightType.HABIT_EXERCISE_FREQUENCY,
            InsightType.HABIT_MISSED_DAYS,
            InsightType.EVENT_SUMMARY,
            InsightType.EVENT_IMPACT,
        } <= produced

    def test_an_empty_dataset_still_reports_the_facts_it_has(
        self, now: datetime
    ) -> None:
        """Zero spending and zero logging are facts, not errors."""
        result = analyse(dataset(window=JUNE), now)
        produced = {insight.type for insight in result.insights}

        assert produced == {
            InsightType.SPENDING_TOTAL,
            InsightType.HABIT_COMPLETION,
            InsightType.HABIT_MISSED_DAYS,
        }

    def test_functions_returning_none_are_dropped_not_emitted_empty(
        self, now: datetime
    ) -> None:
        result = analyse(dataset(window=JUNE), now)

        assert result.first(InsightType.SPENDING_BY_CATEGORY) is None
        assert result.first(InsightType.BUDGET_UTILIZATION) is None

    def test_budget_insights_appear_only_when_a_budget_is_set(
        self, now: datetime
    ) -> None:
        without = analyse(rich_dataset(), now)
        with_budget = analyse(rich_dataset(monthly_budget_paise=5_000_000), now)

        assert without.first(InsightType.BUDGET_UTILIZATION) is None
        assert with_budget.first(InsightType.BUDGET_UTILIZATION) is not None


class TestInvariants:
    def test_every_insight_carries_evidence(self, now: datetime) -> None:
        result = analyse(rich_dataset(monthly_budget_paise=5_000_000), now)

        for insight in result.insights + result.notices:
            assert insight.evidence, f"{insight.type.value} has no evidence"

    def test_only_t3_insights_carry_confidence(self, now: datetime) -> None:
        result = analyse(rich_dataset(), now)

        for insight in result.insights:
            if insight.tier is InsightTier.T3_CORRELATIONAL:
                assert insight.confidence is not None
            else:
                assert insight.confidence is None

    def test_no_insight_contains_prose(self, now: datetime) -> None:
        """``title_key`` is a renderer key. A sentence here would be a claim
        nobody downstream could validate."""
        result = analyse(rich_dataset(), now)

        for insight in result.insights:
            assert " " not in insight.title_key
            assert insight.title_key == insight.title_key.upper()

    def test_insight_ids_are_unique_within_a_run(self, now: datetime) -> None:
        result = analyse(rich_dataset(monthly_budget_paise=5_000_000), now)
        ids = [insight.id for insight in result.insights]

        assert len(ids) == len(set(ids))

    def test_the_whole_result_is_json_serialisable(self, now: datetime) -> None:
        """The API layer does no transformation, so this has to hold here."""
        result = analyse(rich_dataset(monthly_budget_paise=5_000_000), now)

        assert json.loads(json.dumps(result.as_dict()))["run"]["engine_version"]


class TestRunRecord:
    def test_records_the_engine_version_and_window(self, now: datetime) -> None:
        result = analyse(rich_dataset(), now)

        assert result.run["engine_version"] == ENGINE_VERSION
        assert result.run["window"]["start"] == "2026-04-01"
        assert result.run["window"]["days"] == 91

    def test_records_the_gate_thresholds_used(self, now: datetime) -> None:
        """So a claim can be re-derived later, or explained when it was not made."""
        loose = GateConfig(min_history_weeks=2, min_group_size=2)

        result = analyse(rich_dataset(), now, gates=loose)

        assert result.run["gates"]["min_history_weeks"] == 2
        assert result.run["gates"]["min_group_size"] == 2

    def test_records_the_input_counts(self, now: datetime) -> None:
        result = analyse(rich_dataset(), now)

        assert result.run["inputs"]["expenses"] == 91
        assert result.run["inputs"]["check_ins"] == 91
        assert result.run["inputs"]["events"] == 1

    def test_records_how_many_hypotheses_were_suppressed(self, now: datetime) -> None:
        result = analyse(rich_dataset(), now)

        assert result.run["hypotheses_tested"] >= 0
        assert result.run["relationships_suppressed"] > 0

    def test_generated_at_comes_from_the_caller_not_the_wall_clock(
        self, now: datetime
    ) -> None:
        result = analyse(dataset(window=JUNE), now)

        assert result.run["generated_at"] == now.isoformat()


class TestDeterminism:
    def test_the_same_inputs_produce_the_same_output(self, now: datetime) -> None:
        data = rich_dataset(monthly_budget_paise=5_000_000)

        first = json.dumps(analyse(data, now).as_dict(), sort_keys=True)
        second = json.dumps(analyse(data, now).as_dict(), sort_keys=True)

        assert first == second

    def test_insight_order_is_stable(self, now: datetime) -> None:
        data = rich_dataset()

        assert [i.type for i in analyse(data, now).insights] == [
            i.type for i in analyse(data, now).insights
        ]


class TestLookups:
    def test_by_type_filters(self, now: datetime) -> None:
        result = analyse(rich_dataset(), now)

        assert all(
            insight.type is InsightType.EVENT_SUMMARY
            for insight in result.by_type(InsightType.EVENT_SUMMARY)
        )

    def test_first_returns_none_when_absent(self, now: datetime) -> None:
        result = analyse(dataset(window=JUNE), now)

        assert result.first(InsightType.EVENT_IMPACT) is None


class TestNotices:
    def test_a_short_window_yields_a_sufficiency_notice(self, now: datetime) -> None:
        short = AnalysisWindow(date(2026, 6, 1), date(2026, 6, 14))
        result = analyse(dataset(window=short), now)

        assert len(result.notices) == 1
        assert result.notices[0].type is InsightType.DATA_SUFFICIENCY
        assert result.run["notice_count"] == 1

    def test_notices_are_separate_from_insights(self, now: datetime) -> None:
        """A renderer shows them differently: one is a finding, the other is
        an explanation of why there is no finding."""
        short = AnalysisWindow(date(2026, 6, 1), date(2026, 6, 14))
        result = analyse(dataset(window=short), now)

        assert InsightType.DATA_SUFFICIENCY not in {i.type for i in result.insights}
