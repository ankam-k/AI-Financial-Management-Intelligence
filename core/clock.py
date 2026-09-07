"""Injected clock (ADR-003).

Nothing in the application calls ``date.today()`` or ``datetime.now()``
directly. Every "what time is it" question goes through a ``Clock``, so a test
can pin the date and assert on windows, backfill limits, and — later — on
analysis runs that must be reproducible.

The clock is the reason `test_check_ins.py` can assert the exact boundary of
the 30-day backfill window without being a flaky test that breaks at midnight.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Protocol, runtime_checkable

#: Asia/Kolkata. Fixed offset — India observes no daylight saving, so a
#: `timedelta` is exact and avoids a tzdata dependency (ADR-003).
IST = timezone(timedelta(hours=5, minutes=30), name="IST")


@runtime_checkable
class Clock(Protocol):
    """The only source of current time in the application."""

    def now(self) -> datetime:
        """Current instant, timezone-aware, in IST."""

    def today(self) -> date:
        """Current calendar date in IST."""


class SystemClock:
    """Reads the wall clock. The production implementation."""

    def now(self) -> datetime:
        return datetime.now(IST)

    def today(self) -> date:
        return self.now().date()


class FixedClock:
    """A clock frozen at a chosen instant. For tests and reproducible runs."""

    def __init__(self, moment: datetime) -> None:
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=IST)
        self._moment = moment.astimezone(IST)

    def now(self) -> datetime:
        return self._moment

    def today(self) -> date:
        return self._moment.date()

    def advance(self, **timedelta_kwargs: float) -> None:
        """Move the clock forward. Convenience for multi-day test scenarios."""
        self._moment += timedelta(**timedelta_kwargs)
