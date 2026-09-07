"""The engine's input: plain, frozen, session-free records.

The engine deliberately does **not** consume SQLAlchemy models. Two reasons,
both concrete:

1. An ORM instance attached to a session emits SQL on attribute access. Inside
   an analysis loop that is an N+1 query nobody sees until the dataset grows.
   A frozen dataclass cannot reach a database — the guarantee is structural
   rather than a rule to remember.
2. Tests construct these in one line. Every analytics function is unit-testable
   with literal data, no fixtures, no session, no schema.

Mapping ORM rows to these records happens in
``app/services/analysis_service.py`` — the only place in the analysis path
that touches a database.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from app.analysis.window import AnalysisWindow
from app.domain.enums import Category, EventType, PaymentMethod, WorkMode

#: Categories excluded from "spending". A transfer between a user's own
#: accounts is not consumption, and income is not an outflow at all. Including
#: either would inflate every total and pollute every correlation
#: (05_Database_Design.md §4).
NON_SPENDING_CATEGORIES: frozenset[Category] = frozenset(
    {Category.TRANSFERS, Category.INCOME}
)

#: The six habits, in a fixed order so output is deterministic.
HABIT_FIELDS: tuple[str, ...] = (
    "sleep_minutes",
    "exercise",
    "home_cooked_meals",
    "stress_level",
    "alcohol",
    "work_mode",
)


@dataclass(frozen=True, slots=True)
class ExpenseRecord:
    """One outflow. ``amount_paise`` is a positive integer, always."""

    id: str
    date: date
    amount_paise: int
    category: Category
    payment_method: PaymentMethod
    merchant: str | None = None

    @property
    def is_spending(self) -> bool:
        return self.category not in NON_SPENDING_CATEGORIES


@dataclass(frozen=True, slots=True)
class CheckInRecord:
    """One day's habits. Any field may be ``None``, meaning UNKNOWN.

    ``None`` is never "did not happen". ``exercise=False`` is "did not
    happen"; ``exercise=None`` is "no information". Conflating them is the
    failure mode this entire schema is shaped to prevent (SRS-5.5).
    """

    id: str
    date: date
    sleep_minutes: int | None = None
    exercise: bool | None = None
    home_cooked_meals: int | None = None
    stress_level: int | None = None
    alcohol: bool | None = None
    work_mode: WorkMode | None = None

    def habit(self, name: str) -> Any | None:
        """Read one habit by name. ``None`` means UNKNOWN."""
        if name not in HABIT_FIELDS:
            raise KeyError(f"unknown habit: {name!r}")
        return getattr(self, name)

    @property
    def recorded_habit_count(self) -> int:
        """How many of the six habits this row actually asserts."""
        return sum(1 for name in HABIT_FIELDS if getattr(self, name) is not None)


@dataclass(frozen=True, slots=True)
class EventRecord:
    """A user-annotated life event. ``end_date is None`` means a point event."""

    id: str
    event_type: EventType
    title: str
    start_date: date
    end_date: date | None = None

    @property
    def last_day(self) -> date:
        return self.end_date or self.start_date

    @property
    def day_count(self) -> int:
        return (self.last_day - self.start_date).days + 1

    def covers(self, day: date) -> bool:
        return self.start_date <= day <= self.last_day


@dataclass(frozen=True, slots=True)
class AnalysisDataset:
    """Everything the engine is allowed to look at, for one window.

    Records outside the window are the loader's problem, not the engine's:
    every function here assumes the collections are already clipped.
    """

    window: AnalysisWindow
    expenses: tuple[ExpenseRecord, ...] = ()
    check_ins: tuple[CheckInRecord, ...] = ()
    events: tuple[EventRecord, ...] = ()
    #: ``None`` means the user has not set one. Budget insights are then
    #: suppressed rather than computed against a guessed figure.
    monthly_budget_paise: int | None = None
    currency: str = "INR"

    def __post_init__(self) -> None:
        if self.monthly_budget_paise is not None and self.monthly_budget_paise <= 0:
            raise ValueError("monthly_budget_paise must be positive when set")

    # ── Derived views ───────────────────────────────────────────────────────

    @property
    def spending(self) -> tuple[ExpenseRecord, ...]:
        """Expenses that represent consumption, oldest first."""
        return tuple(
            sorted(
                (e for e in self.expenses if e.is_spending),
                key=lambda e: (e.date, e.id),
            )
        )

    @property
    def total_spending_paise(self) -> int:
        return sum(e.amount_paise for e in self.spending)

    def check_in_on(self, day: date) -> CheckInRecord | None:
        """The check-in for a date, or ``None`` if the user logged nothing."""
        for record in self.check_ins:
            if record.date == day:
                return record
        return None

    def events_covering(self, day: date) -> tuple[EventRecord, ...]:
        return tuple(e for e in self.events if e.covers(day))

    def event_days(self) -> frozenset[date]:
        """Every day in the window covered by at least one life event."""
        covered: set[date] = set()
        for event in self.events:
            for day in self.window.iter_days():
                if event.covers(day):
                    covered.add(day)
        return frozenset(covered)

    @property
    def is_empty(self) -> bool:
        return not (self.expenses or self.check_ins or self.events)
