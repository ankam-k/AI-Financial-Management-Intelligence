"""Window arithmetic and calendar bucketing."""

from __future__ import annotations

from datetime import date

import pytest

from app.analysis.window import (
    AnalysisWindow,
    month_end,
    month_key,
    month_start,
    week_key,
    week_start,
)


class TestCalendarHelpers:
    def test_week_starts_on_monday(self) -> None:
        # 2026-06-03 is a Wednesday.
        assert week_start(date(2026, 6, 3)) == date(2026, 6, 1)

    def test_a_monday_is_its_own_week_start(self) -> None:
        assert week_start(date(2026, 6, 1)) == date(2026, 6, 1)

    def test_week_keys_sort_chronologically(self) -> None:
        assert week_key(date(2026, 1, 5)) < week_key(date(2026, 11, 2))

    def test_week_keys_zero_pad(self) -> None:
        assert week_key(date(2026, 1, 5)) == "2026-W02"

    def test_month_bounds(self) -> None:
        assert month_start(date(2026, 6, 15)) == date(2026, 6, 1)
        assert month_end(date(2026, 6, 15)) == date(2026, 6, 30)

    def test_december_month_end_does_not_overflow_the_year(self) -> None:
        assert month_end(date(2026, 12, 5)) == date(2026, 12, 31)

    def test_february_in_a_leap_year(self) -> None:
        assert month_end(date(2028, 2, 1)) == date(2028, 2, 29)

    def test_month_keys_zero_pad(self) -> None:
        assert month_key(date(2026, 6, 1)) == "2026-06"


class TestConstruction:
    def test_a_single_day_window_spans_one_day(self) -> None:
        window = AnalysisWindow(date(2026, 6, 1), date(2026, 6, 1))

        assert window.days == 1

    def test_an_inverted_window_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            AnalysisWindow(date(2026, 6, 30), date(2026, 6, 1))

    def test_trailing_windows_include_the_end_date(self) -> None:
        window = AnalysisWindow.trailing(end=date(2026, 6, 30), days=30)

        assert window.start == date(2026, 6, 1)
        assert window.end == date(2026, 6, 30)
        assert window.days == 30

    def test_a_zero_day_window_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            AnalysisWindow.trailing(end=date(2026, 6, 30), days=0)


class TestMembership:
    def test_both_ends_are_inclusive(self) -> None:
        window = AnalysisWindow(date(2026, 6, 1), date(2026, 6, 30))

        assert window.contains(date(2026, 6, 1))
        assert window.contains(date(2026, 6, 30))
        assert not window.contains(date(2026, 5, 31))
        assert not window.contains(date(2026, 7, 1))

    def test_iter_days_is_contiguous_and_ascending(self) -> None:
        window = AnalysisWindow(date(2026, 6, 1), date(2026, 6, 5))

        assert list(window.iter_days()) == [date(2026, 6, d) for d in range(1, 6)]


class TestCompleteWeeks:
    def test_partial_weeks_at_the_edges_are_excluded(self) -> None:
        """A three-day fragment would contribute a spending total that is an
        artefact of where the window happens to start."""
        # 2026-06-03 is a Wednesday; 2026-06-23 is a Tuesday. The part-weeks
        # at both ends are dropped, leaving the two whole weeks between them.
        window = AnalysisWindow(date(2026, 6, 3), date(2026, 6, 23))
        weeks = window.complete_weeks()

        assert [key for key, _, _ in weeks] == ["2026-W24", "2026-W25"]
        assert weeks[0][1] == date(2026, 6, 8)
        assert weeks[-1][2] == date(2026, 6, 21)

    def test_a_window_of_exact_weeks_keeps_all_of_them(self) -> None:
        window = AnalysisWindow(date(2026, 6, 1), date(2026, 6, 28))

        assert len(window.complete_weeks()) == 4

    def test_a_window_shorter_than_a_week_has_none(self) -> None:
        window = AnalysisWindow(date(2026, 6, 1), date(2026, 6, 5))

        assert window.complete_weeks() == []

    def test_weeks_are_contiguous_and_seven_days_each(self) -> None:
        window = AnalysisWindow(date(2026, 4, 1), date(2026, 6, 30))
        weeks = window.complete_weeks()

        for _, monday, sunday in weeks:
            assert (sunday - monday).days == 6
        for earlier, later in zip(weeks, weeks[1:]):
            assert (later[1] - earlier[1]).days == 7


class TestCompleteMonths:
    def test_partial_months_at_the_edges_are_excluded(self) -> None:
        window = AnalysisWindow(date(2026, 4, 15), date(2026, 7, 10))

        assert [key for key, _, _ in window.complete_months()] == ["2026-05", "2026-06"]

    def test_an_exact_month_is_complete(self) -> None:
        window = AnalysisWindow(date(2026, 6, 1), date(2026, 6, 30))

        assert [key for key, _, _ in window.complete_months()] == ["2026-06"]

    def test_one_day_short_of_a_month_is_not_complete(self) -> None:
        window = AnalysisWindow(date(2026, 6, 1), date(2026, 6, 29))

        assert window.complete_months() == []

    def test_months_spanning_a_year_boundary(self) -> None:
        window = AnalysisWindow(date(2026, 11, 20), date(2027, 2, 5))

        assert [key for key, _, _ in window.complete_months()] == ["2026-12", "2027-01"]

    def test_the_default_ninety_day_window_yields_enough_for_analysis(self) -> None:
        """The engine's default must satisfy gate G1 (≥ 8 complete weeks) and
        give the monthly comparison two months to compare."""
        window = AnalysisWindow.trailing(end=date(2026, 6, 30), days=90)

        assert len(window.complete_weeks()) >= 8
        assert len(window.complete_months()) >= 2
