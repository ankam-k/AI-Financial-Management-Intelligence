"""Habit analytics.

``TestUnknownIsNeverFalse`` is the reason this file matters. Every other test
here is arithmetic; those tests defend the rule that makes the arithmetic
mean anything.
"""

from __future__ import annotations

from datetime import date, datetime

import pytest

from app.analysis import habits as analytics
from app.analysis.window import AnalysisWindow
from app.domain.enums import WorkMode
from tests.analysis.conftest import check_in, dataset

WEEK = AnalysisWindow(date(2026, 6, 1), date(2026, 6, 7))
JUNE = AnalysisWindow(date(2026, 6, 1), date(2026, 6, 30))


def day(number: int) -> date:
    return date(2026, 6, number)


class TestUnknownIsNeverFalse:
    """⭐ SRS-5.5 / ADR-007."""

    def test_exercise_frequency_divides_by_recorded_days_not_window_days(
        self, now: datetime
    ) -> None:
        """The failure this prevents: a user who logs only their gym days
        would show a 43% exercise rate when what they actually said was
        "yes" every single time they answered."""
        data = dataset(
            window=WEEK,
            check_ins=(
                check_in(day(1), exercise=True),
                check_in(day(3), exercise=True),
                check_in(day(5), exercise=True),
            ),
        )

        insight = analytics.exercise_frequency(data, now)

        assert insight.metrics["recorded_days"] == 3
        assert insight.metrics["exercised_days"] == 3
        assert insight.metrics["frequency_ratio"] == 1.0, "3/3, never 3/7"
        assert insight.metrics["observations_excluded_unknown"] == 4

    def test_a_recorded_no_lowers_the_rate_but_an_unknown_does_not(
        self, now: datetime
    ) -> None:
        recorded_no = dataset(
            window=WEEK,
            check_ins=(check_in(day(1), exercise=True), check_in(day(2), exercise=False)),
        )
        unknown = dataset(
            window=WEEK,
            check_ins=(check_in(day(1), exercise=True), check_in(day(2), sleep_minutes=400)),
        )

        assert analytics.exercise_frequency(recorded_no, now).metrics["frequency_ratio"] == 0.5
        assert analytics.exercise_frequency(unknown, now).metrics["frequency_ratio"] == 1.0

    def test_coverage_is_per_habit_not_per_row(self, now: datetime) -> None:
        """A row containing only ``sleep_minutes`` gives zero coverage for
        ``exercise`` (SRS-6.2)."""
        data = dataset(
            window=WEEK,
            check_ins=tuple(check_in(day(n), sleep_minutes=420) for n in range(1, 8)),
        )

        insight = analytics.completion_rate(data, now)
        coverage = {row["habit"]: row["coverage_ratio"] for row in insight.metrics["per_habit"]}

        assert coverage["sleep_minutes"] == 1.0
        assert coverage["exercise"] == 0.0
        assert insight.metrics["completion_ratio"] == 1.0, "every day was logged"

    def test_sleep_average_ignores_days_with_no_sleep_recorded(
        self, now: datetime
    ) -> None:
        """Imputing the missing days — with the mean, or with zero — would
        change the answer. Neither is done."""
        data = dataset(
            window=WEEK,
            check_ins=(
                check_in(day(1), sleep_minutes=480),
                check_in(day(2), sleep_minutes=360),
                check_in(day(3), exercise=True),
            ),
        )

        insight = analytics.average_sleep(data, now)

        assert insight.metrics["observations_included"] == 2
        assert insight.metrics["mean_minutes"] == 420
        assert insight.metrics["observations_excluded_unknown"] == 5

    def test_an_unknown_day_breaks_an_exercise_streak(self, now: datetime) -> None:
        """The engine cannot claim a streak continued through a day it has no
        information about."""
        data = dataset(
            window=WEEK,
            check_ins=(
                check_in(day(1), exercise=True),
                check_in(day(2), sleep_minutes=400),  # exercise UNKNOWN
                check_in(day(3), exercise=True),
            ),
        )

        insight = analytics.streaks(data, now)

        assert insight.metrics["longest_exercise_streak"] == 1


class TestCompletionRate:
    def test_counts_days_with_any_check_in(self, now: datetime) -> None:
        data = dataset(
            window=WEEK,
            check_ins=(check_in(day(1), exercise=True), check_in(day(2), alcohol=False)),
        )

        insight = analytics.completion_rate(data, now)

        assert insight.metrics["logged_days"] == 2
        assert insight.metrics["unlogged_days"] == 5
        assert insight.metrics["completion_ratio"] == pytest.approx(0.2857, abs=1e-4)

    def test_an_empty_window_still_reports(self, now: datetime) -> None:
        """The user with no data needs this number more than anyone, and it
        feeds gate G3."""
        insight = analytics.completion_rate(dataset(window=WEEK), now)

        assert insight.metrics["completion_ratio"] == 0.0
        assert insight.metrics["logged_days"] == 0

    def test_all_six_habits_are_reported(self, now: datetime) -> None:
        insight = analytics.completion_rate(dataset(window=WEEK), now)

        assert len(insight.metrics["per_habit"]) == 6


class TestStreaks:
    def test_current_streak_must_reach_the_window_end(self, now: datetime) -> None:
        data = dataset(
            window=WEEK,
            check_ins=tuple(check_in(day(n), exercise=True) for n in (1, 2, 3)),
        )

        insight = analytics.streaks(data, now)

        assert insight.metrics["longest_logging_streak"] == 3
        assert insight.metrics["current_logging_streak"] == 0
        assert insight.metrics["streak_is_live"] is False

    def test_a_streak_running_to_the_last_day_is_live(self, now: datetime) -> None:
        data = dataset(
            window=WEEK,
            check_ins=tuple(check_in(day(n), exercise=True) for n in range(1, 8)),
        )

        insight = analytics.streaks(data, now)

        assert insight.metrics["current_logging_streak"] == 7
        assert insight.metrics["current_exercise_streak"] == 7
        assert insight.metrics["streak_is_live"] is True

    def test_the_longest_run_is_found_not_the_first(self, now: datetime) -> None:
        data = dataset(
            window=WEEK,
            check_ins=tuple(check_in(day(n), exercise=True) for n in (1, 2, 4, 5, 6)),
        )

        insight = analytics.streaks(data, now)

        assert insight.metrics["longest_logging_streak"] == 3
        assert insight.metrics["longest_logging_streak_start"] == "2026-06-04"
        assert insight.metrics["longest_logging_streak_end"] == "2026-06-06"

    def test_a_recorded_no_breaks_the_exercise_streak(self, now: datetime) -> None:
        data = dataset(
            window=WEEK,
            check_ins=(
                check_in(day(1), exercise=True),
                check_in(day(2), exercise=False),
                check_in(day(3), exercise=True),
            ),
        )

        assert analytics.streaks(data, now).metrics["longest_exercise_streak"] == 1

    def test_no_check_ins_means_no_streak_insight(self, now: datetime) -> None:
        assert analytics.streaks(dataset(window=WEEK), now) is None


class TestAverageSleep:
    def test_reports_minutes_and_hours(self, now: datetime) -> None:
        data = dataset(
            window=WEEK,
            check_ins=(
                check_in(day(1), sleep_minutes=450),
                check_in(day(2), sleep_minutes=390),
            ),
        )

        insight = analytics.average_sleep(data, now)

        assert insight.metrics["mean_minutes"] == 420
        assert insight.metrics["mean_hours"] == 7.0
        assert insight.metrics["min_minutes"] == 390
        assert insight.metrics["max_minutes"] == 450

    def test_stored_averages_stay_integers(self, now: datetime) -> None:
        data = dataset(
            window=WEEK,
            check_ins=(
                check_in(day(1), sleep_minutes=400),
                check_in(day(2), sleep_minutes=401),
                check_in(day(3), sleep_minutes=403),
            ),
        )

        insight = analytics.average_sleep(data, now)

        assert isinstance(insight.metrics["mean_minutes"], int)
        assert insight.metrics["mean_minutes"] == 401

    def test_extreme_nights_are_carried_as_evidence(self, now: datetime) -> None:
        data = dataset(
            window=WEEK,
            check_ins=(
                check_in(day(1), sleep_minutes=450, record_id="long"),
                check_in(day(2), sleep_minutes=300, record_id="short"),
            ),
        )

        insight = analytics.average_sleep(data, now)
        refs = {e.label: e.ref_id for e in insight.evidence}

        assert refs["shortest_night"] == "short"
        assert refs["longest_night"] == "long"

    def test_no_sleep_recorded_means_no_insight(self, now: datetime) -> None:
        data = dataset(window=WEEK, check_ins=(check_in(day(1), exercise=True),))

        assert analytics.average_sleep(data, now) is None


class TestExerciseFrequency:
    def test_reports_sessions_per_week(self, now: datetime) -> None:
        data = dataset(
            window=WEEK,
            check_ins=tuple(
                check_in(day(n), exercise=(n <= 3)) for n in range(1, 8)
            ),
        )

        insight = analytics.exercise_frequency(data, now)

        assert insight.metrics["exercised_days"] == 3
        assert insight.metrics["rest_days"] == 4
        assert insight.metrics["sessions_per_week"] == pytest.approx(3.0)

    def test_no_exercise_recorded_means_no_insight(self, now: datetime) -> None:
        data = dataset(window=WEEK, check_ins=(check_in(day(1), sleep_minutes=400),))

        assert analytics.exercise_frequency(data, now) is None

    def test_all_rest_days_is_a_real_zero(self, now: datetime) -> None:
        """Every day answered "no" is a fact, distinct from every day unlogged."""
        data = dataset(
            window=WEEK,
            check_ins=tuple(check_in(day(n), exercise=False) for n in range(1, 8)),
        )

        insight = analytics.exercise_frequency(data, now)

        assert insight.metrics["frequency_ratio"] == 0.0
        assert insight.metrics["recorded_days"] == 7


class TestMissedDays:
    def test_lists_days_with_no_check_in(self, now: datetime) -> None:
        data = dataset(
            window=WEEK,
            check_ins=(check_in(day(1), exercise=True), check_in(day(7), exercise=True)),
        )

        insight = analytics.missed_days(data, now)

        assert insight.metrics["missed_days"] == 5
        assert insight.metrics["missed_dates"] == [f"2026-06-0{n}" for n in range(2, 7)]
        assert insight.metrics["longest_gap_days"] == 5

    def test_a_fully_logged_window_has_no_gaps(self, now: datetime) -> None:
        data = dataset(
            window=WEEK,
            check_ins=tuple(check_in(day(n), exercise=True) for n in range(1, 8)),
        )

        insight = analytics.missed_days(data, now)

        assert insight.metrics["missed_days"] == 0
        assert insight.metrics["longest_gap_days"] == 0
        assert insight.metrics["days_since_last_check_in"] == 0

    def test_an_empty_window_is_entirely_missed(self, now: datetime) -> None:
        insight = analytics.missed_days(dataset(window=WEEK), now)

        assert insight.metrics["missed_days"] == 7
        assert insight.metrics["missed_ratio"] == 1.0
        assert insight.metrics["days_since_last_check_in"] is None

    def test_reports_days_since_the_last_check_in(self, now: datetime) -> None:
        data = dataset(window=WEEK, check_ins=(check_in(day(4), exercise=True),))

        assert analytics.missed_days(data, now).metrics["days_since_last_check_in"] == 3


class TestWorkModeIsCarried:
    def test_work_mode_counts_toward_coverage(self, now: datetime) -> None:
        data = dataset(
            window=WEEK,
            check_ins=(check_in(day(1), work_mode=WorkMode.REMOTE),),
        )

        insight = analytics.completion_rate(data, now)
        coverage = {row["habit"]: row["recorded_days"] for row in insight.metrics["per_habit"]}

        assert coverage["work_mode"] == 1
