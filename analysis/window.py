"""The analysis window and its calendar bucketing.

The ISO week (Monday-start) is the unit of observation for behavioural
analysis (07_AI_Architecture.md §2.3). Weekly aggregation suits the
habit/spending relationship and matches how the persona experiences routine —
a bad week of sleep shows up as a week of takeaway, not as a same-day
correlation.

Only **complete** periods are compared. A month that the window covers for
nine days is not a month, and comparing it to a full one manufactures a drop
that is an artefact of the window rather than a fact about spending.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterator


def week_start(day: date) -> date:
    """The Monday of the ISO week containing ``day``."""
    return day - timedelta(days=day.weekday())


def week_key(day: date) -> str:
    """Stable sortable ISO week label, e.g. ``"2026-W31"``."""
    iso_year, iso_week, _ = day.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


def month_key(day: date) -> str:
    """Stable sortable month label, e.g. ``"2026-07"``."""
    return f"{day.year:04d}-{day.month:02d}"


def month_start(day: date) -> date:
    return day.replace(day=1)


def month_end(day: date) -> date:
    """Last calendar day of the month containing ``day``."""
    if day.month == 12:
        return date(day.year, 12, 31)
    return date(day.year, day.month + 1, 1) - timedelta(days=1)


@dataclass(frozen=True, slots=True)
class AnalysisWindow:
    """A closed date interval, inclusive at both ends."""

    start: date
    end: date

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise ValueError("window end cannot precede window start")

    @classmethod
    def trailing(cls, end: date, days: int) -> "AnalysisWindow":
        """The ``days``-long window ending on ``end`` inclusive."""
        if days < 1:
            raise ValueError("window must span at least one day")
        return cls(start=end - timedelta(days=days - 1), end=end)

    @property
    def days(self) -> int:
        return (self.end - self.start).days + 1

    @property
    def weeks(self) -> float:
        """Length in weeks, fractional. For gate G1 (history ≥ 8 weeks)."""
        return self.days / 7

    def contains(self, day: date) -> bool:
        return self.start <= day <= self.end

    def iter_days(self) -> Iterator[date]:
        day = self.start
        while day <= self.end:
            yield day
            day += timedelta(days=1)

    def complete_weeks(self) -> list[tuple[str, date, date]]:
        """ISO weeks lying entirely inside the window, oldest first.

        Returns ``(key, monday, sunday)``. A partial week at either edge is
        excluded — a three-day fragment compared against a seven-day week is
        a comparison of window shape, not of behaviour.
        """
        weeks: list[tuple[str, date, date]] = []
        monday = week_start(self.start)
        if monday < self.start:
            monday += timedelta(days=7)
        while monday + timedelta(days=6) <= self.end:
            weeks.append((week_key(monday), monday, monday + timedelta(days=6)))
            monday += timedelta(days=7)
        return weeks

    def complete_months(self) -> list[tuple[str, date, date]]:
        """Calendar months lying entirely inside the window, oldest first."""
        months: list[tuple[str, date, date]] = []
        cursor = month_start(self.start)
        if cursor < self.start:
            cursor = month_start(cursor + timedelta(days=32))
        while True:
            last = month_end(cursor)
            if last > self.end:
                break
            months.append((month_key(cursor), cursor, last))
            cursor = month_start(last + timedelta(days=1))
        return months

    def as_dict(self) -> dict[str, str | int]:
        return {
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "days": self.days,
        }

    def __str__(self) -> str:
        return f"{self.start.isoformat()}..{self.end.isoformat()}"
