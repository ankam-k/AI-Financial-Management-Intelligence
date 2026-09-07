"""Loads a window of user data and hands it to the analysis engine.

**This is the only file in the analysis path that touches a database.** It
exists so that ``app/analysis/`` can stay pure: the engine receives frozen
dataclasses and could just as well be fed by a CSV importer, a fixture, or a
future background job.

The split also means the three queries below are the *whole* query cost of an
analysis run. Everything downstream operates on lists already in memory, so no
amount of analytics can accidentally emit SQL.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.analysis.dataset import (
    AnalysisDataset,
    CheckInRecord,
    EventRecord,
    ExpenseRecord,
)
from app.analysis.engine import AnalysisResult, analyse
from app.analysis.gates import DEFAULT_GATES, GateConfig
from app.analysis.window import AnalysisWindow
from app.core.clock import Clock
from app.domain.errors import ValidationError
from app.models.check_in import CheckIn
from app.models.expense import Expense
from app.models.life_event import LifeEvent
from app.models.user import User

#: Default span of an analysis run. Long enough to contain the ≥ 8 complete
#: weeks gate G1 requires (90 days ≈ 12 weeks) and two full calendar months
#: for the monthly comparison, without reaching so far back that a
#: "total spending" figure stops describing the user's current life.
DEFAULT_WINDOW_DAYS = 90

MAX_WINDOW_DAYS = 730


class AnalysisService:
    """Builds an :class:`AnalysisDataset` from stored rows and runs the engine."""

    def __init__(self, session: Session, clock: Clock) -> None:
        self._session = session
        self._clock = clock

    def build_window(
        self,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        days: int | None = None,
    ) -> AnalysisWindow:
        """Resolve the requested window against the injected clock."""
        end = end_date or self._clock.today()

        if start_date is not None:
            if start_date > end:
                raise ValidationError("'start_date' cannot be after 'end_date'")
            window = AnalysisWindow(start=start_date, end=end)
        else:
            span = DEFAULT_WINDOW_DAYS if days is None else days
            if span < 1:
                raise ValidationError("'days' must be at least 1")
            window = AnalysisWindow.trailing(end=end, days=span)

        if window.days > MAX_WINDOW_DAYS:
            raise ValidationError(
                f"Analysis window cannot exceed {MAX_WINDOW_DAYS} days "
                f"(requested {window.days})."
            )
        return window

    def build_dataset(self, user: User, window: AnalysisWindow) -> AnalysisDataset:
        """Load everything the engine is allowed to see, clipped to the window."""
        expenses = self._session.scalars(
            select(Expense)
            .where(
                Expense.user_id == user.id,
                Expense.expense_date >= window.start,
                Expense.expense_date <= window.end,
            )
            .order_by(Expense.expense_date, Expense.id)
        ).all()

        check_ins = self._session.scalars(
            select(CheckIn)
            .where(
                CheckIn.user_id == user.id,
                CheckIn.log_date >= window.start,
                CheckIn.log_date <= window.end,
            )
            .order_by(CheckIn.log_date)
        ).all()

        # Overlap, not containment: an event that began before the window and
        # ended inside it still describes days the window covers.
        events = self._session.scalars(
            select(LifeEvent)
            .where(
                LifeEvent.user_id == user.id,
                LifeEvent.start_date <= window.end,
                _still_running_on(window.start),
            )
            .order_by(LifeEvent.start_date, LifeEvent.id)
        ).all()

        return AnalysisDataset(
            window=window,
            expenses=tuple(
                ExpenseRecord(
                    id=row.id,
                    date=row.expense_date,
                    amount_paise=row.amount_paise,
                    category=row.category,
                    payment_method=row.payment_method,
                    merchant=row.merchant,
                )
                for row in expenses
            ),
            check_ins=tuple(
                CheckInRecord(
                    id=row.id,
                    date=row.log_date,
                    sleep_minutes=row.sleep_minutes,
                    exercise=row.exercise,
                    home_cooked_meals=row.home_cooked_meals,
                    stress_level=row.stress_level,
                    alcohol=row.alcohol,
                    work_mode=row.work_mode,
                )
                for row in check_ins
            ),
            events=tuple(
                EventRecord(
                    id=row.id,
                    event_type=row.event_type,
                    title=row.title,
                    start_date=row.start_date,
                    end_date=row.end_date,
                )
                for row in events
            ),
            monthly_budget_paise=user.monthly_budget_paise,
            currency=user.currency,
        )

    def run(
        self,
        user: User,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        days: int | None = None,
        gates: GateConfig = DEFAULT_GATES,
    ) -> AnalysisResult:
        """Load, then analyse. The engine sees no session and no clock."""
        window = self.build_window(start_date=start_date, end_date=end_date, days=days)
        dataset = self.build_dataset(user, window)
        return analyse(dataset, now=self._clock.now(), gates=gates)


def _still_running_on(start: date):
    """Predicate: the event had not already finished before ``start``.

    A point event (``end_date IS NULL``) occupies ``start_date`` only, so it
    qualifies when that day is on or after the window start.
    """
    return or_(
        LifeEvent.end_date >= start,
        and_(LifeEvent.end_date.is_(None), LifeEvent.start_date >= start),
    )
