"""Builders for narration tests.

The insights here come from running the real analysis engine rather than being
hand-constructed. A narration test that invents its own insight shape would
keep passing after the engine changed the metrics its templates read.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Callable

import pytest

from app.analysis.dataset import AnalysisDataset, CheckInRecord, EventRecord, ExpenseRecord
from app.analysis.engine import analyse
from app.analysis.models import Insight, InsightType
from app.analysis.window import AnalysisWindow
from app.core.clock import IST
from app.domain.enums import Category, EventType, PaymentMethod
from app.llm.base import LLMHealth

NOW = datetime(2026, 7, 1, 9, 0, tzinfo=IST)

#: 2026-03-02 is a Monday. Sixteen whole weeks satisfies gate G1.
SIGNAL_START = date(2026, 3, 2)
SIGNAL_WEEKS = 16


class FakeLLMClient:
    """A scriptable stand-in for a model.

    Tests drive the renderer through every branch — a clean generation, an
    invented number, causal phrasing, prohibited advice, a timeout — without
    needing Ollama installed or a model downloaded.
    """

    provider = "fake"

    def __init__(
        self,
        response: dict[str, Any] | Callable[[str, str], dict[str, Any]] | None = None,
        *,
        error: Exception | None = None,
        model: str = "fake-model",
        available: bool = True,
    ) -> None:
        self.model = model
        self._response = response
        self._error = error
        self._available = available
        #: Every call, so tests can assert on what the model was actually sent.
        self.calls: list[dict[str, Any]] = []

    def complete_json(
        self, *, system: str, user: str, schema: dict[str, Any]
    ) -> dict[str, Any]:
        self.calls.append({"system": system, "user": user, "schema": schema})
        if self._error is not None:
            raise self._error
        if callable(self._response):
            return self._response(system, user)
        return dict(self._response or {})

    def health(self) -> LLMHealth:
        return LLMHealth(
            provider=self.provider,
            model=self.model,
            available=self._available,
            detail="fake",
        )


def signal_dataset(*, with_events: bool = True, budget: int | None = 2_500_000):
    """Sixteen weeks in which exercise weeks show lower food spending.

    The same shape as the Sprint 2 relationship fixture, so a T3 insight is
    actually produced and its narration can be tested against a real one.
    """
    window = AnalysisWindow(SIGNAL_START, SIGNAL_START + timedelta(days=SIGNAL_WEEKS * 7 - 1))
    expenses: list[ExpenseRecord] = []
    check_ins: list[CheckInRecord] = []

    for index in range(SIGNAL_WEEKS):
        exercising = index % 2 == 0
        monday = SIGNAL_START + timedelta(days=index * 7)
        expenses.append(
            ExpenseRecord(
                id=f"exp-{index}",
                date=monday,
                amount_paise=(400_000 if exercising else 600_000) + index * 1_000,
                category=Category.FOOD_DINING,
                payment_method=PaymentMethod.UPI,
                merchant="Swiggy",
            )
        )
        expenses.append(
            ExpenseRecord(
                id=f"exp-t-{index}",
                date=monday + timedelta(days=2),
                amount_paise=80_000,
                category=Category.TRANSPORT,
                payment_method=PaymentMethod.CASH,
            )
        )
        for offset in range(7):
            check_ins.append(
                CheckInRecord(
                    id=f"chk-{index}-{offset}",
                    date=monday + timedelta(days=offset),
                    exercise=exercising,
                    sleep_minutes=420 + offset,
                )
            )

    events = (
        (
            EventRecord(
                id="evt-1",
                event_type=EventType.TRAVEL,
                title="Goa trip",
                start_date=date(2026, 4, 6),
                end_date=date(2026, 4, 9),
            ),
        )
        if with_events
        else ()
    )

    return AnalysisDataset(
        window=window,
        expenses=tuple(expenses),
        check_ins=tuple(check_ins),
        events=events,
        monthly_budget_paise=budget,
    )


@pytest.fixture
def now() -> datetime:
    return NOW


@pytest.fixture
def every_insight() -> dict[InsightType, Insight]:
    """One real insight of every ``InsightType``.

    Assembled from two runs: a rich sixteen-week dataset for the descriptive,
    comparative and correlational families, and a deliberately short window
    for the data-sufficiency notice.
    """
    collected: dict[InsightType, Insight] = {}

    rich = analyse(signal_dataset(), NOW)
    for insight in rich.insights + rich.notices:
        collected.setdefault(insight.type, insight)

    short_window = AnalysisWindow(date(2026, 6, 1), date(2026, 6, 14))
    sparse = analyse(AnalysisDataset(window=short_window), NOW)
    for insight in sparse.insights + sparse.notices:
        collected.setdefault(insight.type, insight)

    return collected


@pytest.fixture
def relationship_insight(every_insight: dict[InsightType, Insight]) -> Insight:
    """The T3 insight — the one with the strictest narration rules."""
    return every_insight[InsightType.BEHAVIOR_RELATIONSHIP]


@pytest.fixture
def total_insight(every_insight: dict[InsightType, Insight]) -> Insight:
    """A T1 insight, where causal phrasing is permitted (PDR-036)."""
    return every_insight[InsightType.SPENDING_TOTAL]


@pytest.fixture
def sufficiency_insight(every_insight: dict[InsightType, Insight]) -> Insight:
    return every_insight[InsightType.DATA_SUFFICIENCY]
