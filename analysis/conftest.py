"""Builders for analysis tests.

The engine consumes plain frozen dataclasses, so every test here constructs
its input literally — no database, no session, no fixtures beyond these
helpers. That is the payoff of keeping ``app/analysis/`` free of the ORM.
"""

from __future__ import annotations

import itertools
from datetime import date, datetime, timedelta

import pytest

from app.analysis.dataset import (
    AnalysisDataset,
    CheckInRecord,
    EventRecord,
    ExpenseRecord,
)
from app.analysis.window import AnalysisWindow
from app.core.clock import IST
from app.domain.enums import Category, EventType, PaymentMethod

#: A Wednesday, so weekday-sensitive assertions have a stable reference.
NOW = datetime(2026, 7, 1, 9, 0, tzinfo=IST)

_ids = itertools.count(1)


def _next_id(prefix: str) -> str:
    return f"{prefix}-{next(_ids)}"


def expense(
    day: date,
    amount_paise: int,
    category: Category = Category.FOOD_DINING,
    *,
    payment_method: PaymentMethod = PaymentMethod.UPI,
    merchant: str | None = None,
    record_id: str | None = None,
) -> ExpenseRecord:
    return ExpenseRecord(
        id=record_id or _next_id("exp"),
        date=day,
        amount_paise=amount_paise,
        category=category,
        payment_method=payment_method,
        merchant=merchant,
    )


def check_in(day: date, *, record_id: str | None = None, **habits: object) -> CheckInRecord:
    """A check-in. **Unlisted habits are UNKNOWN, not False.**"""
    return CheckInRecord(id=record_id or _next_id("chk"), date=day, **habits)


def life_event(
    start: date,
    end: date | None = None,
    *,
    event_type: EventType = EventType.TRAVEL,
    title: str = "Trip",
    record_id: str | None = None,
) -> EventRecord:
    return EventRecord(
        id=record_id or _next_id("evt"),
        event_type=event_type,
        title=title,
        start_date=start,
        end_date=end,
    )


def dataset(
    *,
    window: AnalysisWindow | None = None,
    expenses: tuple[ExpenseRecord, ...] = (),
    check_ins: tuple[CheckInRecord, ...] = (),
    events: tuple[EventRecord, ...] = (),
    monthly_budget_paise: int | None = None,
) -> AnalysisDataset:
    return AnalysisDataset(
        window=window or AnalysisWindow(date(2026, 6, 1), date(2026, 6, 30)),
        expenses=expenses,
        check_ins=check_ins,
        events=events,
        monthly_budget_paise=monthly_budget_paise,
    )


def days_from(start: date, count: int) -> list[date]:
    return [start + timedelta(days=offset) for offset in range(count)]


@pytest.fixture
def now() -> datetime:
    return NOW


@pytest.fixture
def june() -> AnalysisWindow:
    """A whole calendar month: 30 days, 4 complete ISO weeks."""
    return AnalysisWindow(date(2026, 6, 1), date(2026, 6, 30))
