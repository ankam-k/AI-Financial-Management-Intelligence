r"""Habit analytics.

⭐ **The rule that governs every function here** (SRS-5.5, ADR-007):

```
For each habit:
    observations ← days with a NON-NULL value for THAT habit
    if none  → UNKNOWN → EXCLUDED
    else     → aggregate the recorded values

NEVER:  coalesce NULL → false / 0
NEVER:  impute (mean, mode, or otherwise)
NEVER:  treat a missing check-in as a recorded negative
```

The consequence shows up in every denominator below. Exercise frequency is
``exercised_days / days_where_exercise_WAS_RECORDED`` — never
``/ days_in_window``. Dividing by the window would silently count every
unlogged day as a day without exercise, which is exactly how a user who logs
only their gym days ends up with a fabricated 20% exercise rate.

**Coverage is per-habit, not per-row** (SRS-6.2). A check-in containing only
``sleep_hours`` provides zero coverage for ``exercise``. So each habit gets
its own denominator, and every insight reports how many observations it
excluded as unknown (SRS-6.4).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Callable

from app.analysis.dataset import HABIT_FIELDS, AnalysisDataset, CheckInRecord
from app.analysis.models import Evidence, EvidenceKind, Insight, InsightTier, InsightType
from app.analysis.stats import mean_paise, median_paise

MINUTES_PER_HOUR = 60


def _by_date(dataset: AnalysisDataset) -> dict[date, CheckInRecord]:
    return {record.date: record for record in dataset.check_ins}


def _minutes_to_hours(minutes: float) -> float:
    return round(minutes / MINUTES_PER_HOUR, 2)


def _longest_run(
    days: list[date], holds: Callable[[date], bool]
) -> tuple[int, date | None, date | None]:
    """Longest consecutive run of days satisfying ``holds``.

    Returns ``(length, first_day, last_day)``. Days are assumed contiguous and
    ascending, which :meth:`AnalysisWindow.iter_days` guarantees.
    """
    best = 0
    best_span: tuple[date | None, date | None] = (None, None)
    current = 0
    start: date | None = None

    for day in days:
        if holds(day):
            current += 1
            if start is None:
                start = day
            if current > best:
                best = current
                best_span = (start, day)
        else:
            current = 0
            start = None
    return best, best_span[0], best_span[1]


def _trailing_run(days: list[date], holds: Callable[[date], bool]) -> int:
    """Length of the run ending on the last day. Zero if the last day fails."""
    count = 0
    for day in reversed(days):
        if not holds(day):
            break
        count += 1
    return count


def completion_rate(dataset: AnalysisDataset, now: datetime) -> Insight:
    """How much of the window the user actually logged, per habit and overall.

    Always returns. A user who has logged nothing needs this number more than
    anyone, and it is the input to gate G3.
    """
    days = list(dataset.window.iter_days())
    by_date = _by_date(dataset)
    window_days = len(days)

    logged_days = sum(1 for day in days if day in by_date)

    per_habit: list[dict[str, Any]] = []
    for habit in HABIT_FIELDS:
        recorded = sum(
            1 for day in days if (r := by_date.get(day)) and r.habit(habit) is not None
        )
        per_habit.append(
            {
                "habit": habit,
                "recorded_days": recorded,
                "unknown_days": window_days - recorded,
                "coverage_ratio": round(recorded / window_days, 4),
            }
        )

    metrics: dict[str, Any] = {
        "window_days": window_days,
        "logged_days": logged_days,
        "unlogged_days": window_days - logged_days,
        "completion_ratio": round(logged_days / window_days, 4),
        "per_habit": per_habit,
        # The overall figure counts a row as logged even if it records one
        # habit out of six, so it always reads higher than per-habit coverage.
        "average_habit_coverage_ratio": round(
            sum(row["coverage_ratio"] for row in per_habit) / len(per_habit), 4
        ),
    }

    evidence: list[Evidence] = [
        Evidence(
            kind=EvidenceKind.AGGREGATE,
            label="window_coverage",
            payload={"logged_days": logged_days, "window_days": window_days},
        )
    ]
    evidence.extend(
        Evidence(kind=EvidenceKind.AGGREGATE, label=f"habit:{row['habit']}", payload=row)
        for row in per_habit
    )

    return Insight(
        type=InsightType.HABIT_COMPLETION,
        tier=InsightTier.T1_DESCRIPTIVE,
        title_key="HABIT_COMPLETION",
        window=dataset.window,
        metrics=metrics,
        evidence=tuple(evidence),
        created_at=now,
    )


def streaks(dataset: AnalysisDataset, now: datetime) -> Insight | None:
    """Logging streaks and exercise streaks, current and longest.

    An UNKNOWN day **breaks** an exercise streak rather than extending it. The
    engine cannot claim a streak continued through a day it has no information
    about; the conservative reading is the only honest one.
    """
    if not dataset.check_ins:
        return None

    days = list(dataset.window.iter_days())
    by_date = _by_date(dataset)

    def logged(day: date) -> bool:
        return day in by_date

    def exercised(day: date) -> bool:
        record = by_date.get(day)
        return record is not None and record.exercise is True

    longest_log, log_from, log_to = _longest_run(days, logged)
    longest_exercise, ex_from, ex_to = _longest_run(days, exercised)

    logged_dates = sorted(by_date)
    metrics: dict[str, Any] = {
        "current_logging_streak": _trailing_run(days, logged),
        "longest_logging_streak": longest_log,
        "longest_logging_streak_start": log_from.isoformat() if log_from else None,
        "longest_logging_streak_end": log_to.isoformat() if log_to else None,
        "current_exercise_streak": _trailing_run(days, exercised),
        "longest_exercise_streak": longest_exercise,
        "longest_exercise_streak_start": ex_from.isoformat() if ex_from else None,
        "longest_exercise_streak_end": ex_to.isoformat() if ex_to else None,
        "last_logged_date": logged_dates[-1].isoformat() if logged_dates else None,
        "window_end": dataset.window.end.isoformat(),
        # A streak is "current" only if it reaches the last day of the window.
        "streak_is_live": bool(logged_dates) and logged_dates[-1] == dataset.window.end,
        "unknown_exercise_days": sum(
            1 for day in days if (r := by_date.get(day)) is None or r.exercise is None
        ),
    }

    evidence = (
        Evidence(
            kind=EvidenceKind.AGGREGATE,
            label="logging_streak",
            payload={
                "current": metrics["current_logging_streak"],
                "longest": longest_log,
            },
        ),
        Evidence(
            kind=EvidenceKind.AGGREGATE,
            label="exercise_streak",
            payload={
                "current": metrics["current_exercise_streak"],
                "longest": longest_exercise,
            },
        ),
    )

    return Insight(
        type=InsightType.HABIT_STREAK,
        tier=InsightTier.T1_DESCRIPTIVE,
        title_key="HABIT_STREAK",
        window=dataset.window,
        metrics=metrics,
        evidence=tuple(evidence),
        created_at=now,
    )


def average_sleep(dataset: AnalysisDataset, now: datetime) -> Insight | None:
    """Mean and median sleep across days where sleep was actually recorded."""
    observations = [
        (record.date, record.sleep_minutes)
        for record in sorted(dataset.check_ins, key=lambda r: r.date)
        if record.sleep_minutes is not None
    ]
    if not observations:
        return None

    minutes = [value for _, value in observations]
    window_days = dataset.window.days
    shortest = min(observations, key=lambda row: (row[1], row[0]))
    longest = max(observations, key=lambda row: (row[1], row[0]))

    # `mean_paise`/`median_paise` are integer-exact averages. Sleep is not
    # money, but the same helpers keep the stored value an integer, matching
    # the `sleep_minutes` column and avoiding a float round trip.
    mean_minutes = mean_paise(minutes)
    median_minutes = median_paise(minutes)

    metrics: dict[str, Any] = {
        "observations_included": len(minutes),
        "observations_excluded_unknown": window_days - len(minutes),
        "coverage_ratio": round(len(minutes) / window_days, 4),
        "mean_minutes": mean_minutes,
        "mean_hours": _minutes_to_hours(mean_minutes),
        "median_minutes": median_minutes,
        "median_hours": _minutes_to_hours(median_minutes),
        "min_minutes": shortest[1],
        "min_hours": _minutes_to_hours(shortest[1]),
        "max_minutes": longest[1],
        "max_hours": _minutes_to_hours(longest[1]),
    }

    evidence = (
        Evidence(
            kind=EvidenceKind.AGGREGATE,
            label="sleep_observations",
            payload={
                "included": len(minutes),
                "excluded_unknown": metrics["observations_excluded_unknown"],
            },
        ),
        Evidence(
            kind=EvidenceKind.CHECK_IN,
            label="shortest_night",
            ref_id=next(r.id for r in dataset.check_ins if r.date == shortest[0]),
            payload={"date": shortest[0].isoformat(), "sleep_minutes": shortest[1]},
        ),
        Evidence(
            kind=EvidenceKind.CHECK_IN,
            label="longest_night",
            ref_id=next(r.id for r in dataset.check_ins if r.date == longest[0]),
            payload={"date": longest[0].isoformat(), "sleep_minutes": longest[1]},
        ),
    )

    return Insight(
        type=InsightType.HABIT_SLEEP_AVERAGE,
        tier=InsightTier.T1_DESCRIPTIVE,
        title_key="HABIT_SLEEP_AVERAGE",
        window=dataset.window,
        metrics=metrics,
        evidence=evidence,
        created_at=now,
        subject="sleep_minutes",
    )


def exercise_frequency(dataset: AnalysisDataset, now: datetime) -> Insight | None:
    """How often the user exercised, **among days where they said**.

    The denominator is recorded days, not window days. That is the whole
    point: a user who logs only gym days would otherwise appear to have
    exercised on 20% of days when what they actually said was "yes" every
    single time they answered.
    """
    recorded = [
        record
        for record in sorted(dataset.check_ins, key=lambda r: r.date)
        if record.exercise is not None
    ]
    if not recorded:
        return None

    exercised = [record for record in recorded if record.exercise is True]
    window_days = dataset.window.days
    complete_weeks = max(1, len(recorded)) / 7

    metrics: dict[str, Any] = {
        "recorded_days": len(recorded),
        "exercised_days": len(exercised),
        "rest_days": len(recorded) - len(exercised),
        # Denominator is recorded days. Never window days.
        "frequency_ratio": round(len(exercised) / len(recorded), 4),
        "observations_excluded_unknown": window_days - len(recorded),
        "coverage_ratio": round(len(recorded) / window_days, 4),
        "sessions_per_week": round(len(exercised) / complete_weeks, 2),
        "window_days": window_days,
    }

    evidence: list[Evidence] = [
        Evidence(
            kind=EvidenceKind.AGGREGATE,
            label="exercise_observations",
            payload={
                "recorded_days": len(recorded),
                "exercised_days": len(exercised),
                "excluded_unknown": metrics["observations_excluded_unknown"],
            },
        )
    ]
    evidence.extend(
        Evidence(
            kind=EvidenceKind.CHECK_IN,
            label="exercised_day",
            ref_id=record.id,
            payload={"date": record.date.isoformat()},
        )
        for record in exercised[-3:]
    )

    return Insight(
        type=InsightType.HABIT_EXERCISE_FREQUENCY,
        tier=InsightTier.T1_DESCRIPTIVE,
        title_key="HABIT_EXERCISE_FREQUENCY",
        window=dataset.window,
        metrics=metrics,
        evidence=tuple(evidence),
        created_at=now,
        subject="exercise",
    )


def missed_days(dataset: AnalysisDataset, now: datetime) -> Insight:
    """Days in the window with no check-in at all.

    A missed day is not a day the habits did not happen — it is a day with no
    information. Reported as its own figure so nothing downstream is tempted
    to read it as a zero.
    """
    days = list(dataset.window.iter_days())
    by_date = _by_date(dataset)
    missed = [day for day in days if day not in by_date]

    longest_gap, gap_from, gap_to = _longest_run(days, lambda day: day not in by_date)

    metrics: dict[str, Any] = {
        "window_days": len(days),
        "missed_days": len(missed),
        "missed_ratio": round(len(missed) / len(days), 4),
        "missed_dates": [day.isoformat() for day in missed],
        "longest_gap_days": longest_gap,
        "longest_gap_start": gap_from.isoformat() if gap_from else None,
        "longest_gap_end": gap_to.isoformat() if gap_to else None,
        "days_since_last_check_in": (
            (dataset.window.end - max(by_date)).days if by_date else None
        ),
    }

    evidence = (
        Evidence(
            kind=EvidenceKind.AGGREGATE,
            label="missed_days",
            payload={"missed": len(missed), "window_days": len(days)},
        ),
    )

    return Insight(
        type=InsightType.HABIT_MISSED_DAYS,
        tier=InsightTier.T1_DESCRIPTIVE,
        title_key="HABIT_MISSED_DAYS",
        window=dataset.window,
        metrics=metrics,
        evidence=evidence,
        created_at=now,
    )
