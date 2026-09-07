"""Event analytics."""

from __future__ import annotations

from datetime import date, datetime

import pytest

from app.analysis import events as analytics
from app.analysis.models import InsightTier
from app.analysis.window import AnalysisWindow
from app.domain.enums import Category, EventType
from tests.analysis.conftest import dataset, expense, life_event

JUNE = AnalysisWindow(date(2026, 6, 1), date(2026, 6, 30))


def day(number: int) -> date:
    return date(2026, 6, number)


class TestEventSummaries:
    def test_one_insight_per_event(self, now: datetime) -> None:
        data = dataset(
            window=JUNE,
            events=(
                life_event(day(5), day(7), title="Goa"),
                life_event(day(20), title="Diwali", event_type=EventType.FESTIVAL),
            ),
        )

        summaries = analytics.event_summaries(data, now)

        assert [s.metrics["title"] for s in summaries] == ["Diwali", "Goa"]

    def test_counts_only_spending_inside_the_event(self, now: datetime) -> None:
        data = dataset(
            window=JUNE,
            expenses=(
                expense(day(4), 10000),   # day before
                expense(day(5), 30000),   # first day
                expense(day(7), 20000),   # last day
                expense(day(8), 90000),   # day after
            ),
            events=(life_event(day(5), day(7)),)
        )

        summary = analytics.event_summaries(data, now)[0]

        assert summary.metrics["total_paise"] == 50000
        assert summary.metrics["expense_count"] == 2
        assert summary.metrics["event_days_in_window"] == 3

    def test_a_point_event_covers_one_day(self, now: datetime) -> None:
        data = dataset(
            window=JUNE,
            expenses=(expense(day(10), 40000),),
            events=(life_event(day(10)),),
        )

        summary = analytics.event_summaries(data, now)[0]

        assert summary.metrics["is_point_event"] is True
        assert summary.metrics["event_days_in_window"] == 1
        assert summary.metrics["average_per_day_paise"] == 40000

    def test_an_event_beginning_before_the_window_counts_only_the_overlap(
        self, now: datetime
    ) -> None:
        data = dataset(
            window=JUNE,
            expenses=(expense(day(2), 10000),),
            events=(life_event(date(2026, 5, 28), day(3)),),
        )

        summary = analytics.event_summaries(data, now)[0]

        assert summary.metrics["event_days_total"] == 7
        assert summary.metrics["event_days_in_window"] == 3

    def test_an_event_entirely_outside_the_window_is_skipped(
        self, now: datetime
    ) -> None:
        data = dataset(
            window=JUNE,
            events=(life_event(date(2026, 3, 1), date(2026, 3, 5)),),
        )

        assert analytics.event_summaries(data, now) == []

    def test_the_event_itself_is_evidence(self, now: datetime) -> None:
        data = dataset(window=JUNE, events=(life_event(day(5), day(7), record_id="ev-9"),))

        summary = analytics.event_summaries(data, now)[0]

        assert summary.evidence[0].ref_id == "ev-9"
        assert summary.subject == "ev-9"

    def test_categories_are_broken_out(self, now: datetime) -> None:
        data = dataset(
            window=JUNE,
            expenses=(
                expense(day(5), 30000, Category.TRAVEL),
                expense(day(6), 70000, Category.FOOD_DINING),
            ),
            events=(life_event(day(5), day(7)),),
        )

        summary = analytics.event_summaries(data, now)[0]

        assert summary.metrics["top_category"] == "FOOD_DINING"


class TestEventImpact:
    def test_compares_per_day_not_per_total(self, now: datetime) -> None:
        """A four-day trip will always total less than the other 26 days.
        Comparing totals would report that as spending less on holiday."""
        window = AnalysisWindow(day(1), day(10))
        data = dataset(
            window=window,
            expenses=(
                expense(day(2), 100000),  # event day
                expense(day(3), 100000),  # event day
                expense(day(6), 20000),
                expense(day(7), 20000),
                expense(day(8), 20000),
            ),
            events=(life_event(day(2), day(3)),),
        )

        insight = analytics.event_impact(data, now)

        assert insight.tier is InsightTier.T2_COMPARATIVE
        assert insight.metrics["event_days"] == 2
        assert insight.metrics["ordinary_days"] == 8
        assert insight.metrics["during_daily_paise"] == 100000
        assert insight.metrics["outside_daily_paise"] == 7500
        assert insight.metrics["direction"] == "HIGHER"

    def test_no_events_means_no_comparison(self, now: datetime) -> None:
        data = dataset(window=JUNE, expenses=(expense(day(1), 10000),))

        assert analytics.event_impact(data, now) is None

    def test_an_event_covering_the_whole_window_leaves_nothing_to_compare(
        self, now: datetime
    ) -> None:
        window = AnalysisWindow(day(1), day(5))
        data = dataset(
            window=window,
            expenses=(expense(day(1), 10000),),
            events=(life_event(day(1), day(5)),),
        )

        assert analytics.event_impact(data, now) is None

    def test_overlapping_events_count_a_day_once(self, now: datetime) -> None:
        window = AnalysisWindow(day(1), day(10))
        data = dataset(
            window=window,
            expenses=(expense(day(3), 60000),),
            events=(life_event(day(2), day(4)), life_event(day(3), day(5))),
        )

        insight = analytics.event_impact(data, now)

        assert insight.metrics["event_days"] == 4  # days 2,3,4,5

    def test_it_does_not_pretend_to_be_a_hypothesis_test(self, now: datetime) -> None:
        """No p-value is reported because none was computed. Inventing one to
        make a descriptive split look rigorous is the failure mode this
        project exists to avoid."""
        window = AnalysisWindow(day(1), day(10))
        data = dataset(
            window=window,
            expenses=(expense(day(2), 50000),),
            events=(life_event(day(2), day(3)),),
        )

        insight = analytics.event_impact(data, now)

        assert insight.metrics["is_statistical_test"] is False
        assert "p_value" not in insight.metrics
        assert insight.confidence is None

    def test_a_zero_baseline_yields_no_relative_difference(
        self, now: datetime
    ) -> None:
        window = AnalysisWindow(day(1), day(10))
        data = dataset(
            window=window,
            expenses=(expense(day(2), 50000),),
            events=(life_event(day(2), day(3)),),
        )

        insight = analytics.event_impact(data, now)

        assert insight.metrics["outside_daily_paise"] == 0
        assert insight.metrics["relative_difference"] is None

    def test_every_event_is_carried_as_evidence(self, now: datetime) -> None:
        window = AnalysisWindow(day(1), day(20))
        data = dataset(
            window=window,
            expenses=(expense(day(2), 50000),),
            events=(life_event(day(2), day(3)), life_event(day(10))),
        )

        insight = analytics.event_impact(data, now)
        event_refs = [e for e in insight.evidence if e.kind.value == "LIFE_EVENT"]

        assert len(event_refs) == 2
