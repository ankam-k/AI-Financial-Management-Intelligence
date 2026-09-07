"""Expense CRUD."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import Clock
from app.core.unit_of_work import atomic, retry_on_locked
from app.domain.enums import Category
from app.domain.errors import NotFoundError, ValidationError
from app.models.expense import Expense
from app.models.user import User
from app.schemas.expense import ExpenseCreate


class ExpenseService:
    """Business rules for expenses.

    Every query is scoped by ``user_id``. Scoping at the service boundary
    rather than in the router means a future endpoint cannot forget it.
    """

    def __init__(self, session: Session, clock: Clock) -> None:
        self._session = session
        self._clock = clock

    def create(self, user: User, payload: ExpenseCreate) -> Expense:
        """Record a new expense."""
        expense = Expense(
            user_id=user.id,
            expense_date=payload.expense_date,
            amount_paise=payload.amount_paise,
            currency=user.currency,
            category=payload.category,
            payment_method=payload.payment_method,
            merchant=_clean(payload.merchant),
            notes=_clean(payload.notes),
        )
        with atomic(self._session):
            self._session.add(expense)
        self._session.refresh(expense)
        return expense

    def get(self, user: User, expense_id: str) -> Expense:
        """Fetch one expense, or raise ``NotFoundError``."""
        expense = self._session.scalars(
            select(Expense).where(Expense.id == expense_id, Expense.user_id == user.id)
        ).first()
        if expense is None:
            raise NotFoundError(f"No expense with id '{expense_id}'")
        return expense

    def list(
        self,
        user: User,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        category: Category | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Expense]:
        """List expenses, newest first, with optional filters."""
        if start_date is not None and end_date is not None and end_date < start_date:
            raise ValidationError("'end_date' cannot be before 'start_date'")

        query = select(Expense).where(Expense.user_id == user.id)
        if start_date is not None:
            query = query.where(Expense.expense_date >= start_date)
        if end_date is not None:
            query = query.where(Expense.expense_date <= end_date)
        if category is not None:
            query = query.where(Expense.category == category)

        # `id` breaks ties so pagination is stable when several expenses share
        # a date — without it, offset paging can repeat or skip rows.
        query = query.order_by(Expense.expense_date.desc(), Expense.id.desc())
        query = query.limit(limit).offset(offset)

        return list(self._session.scalars(query))

    #: Free-text columns that get whitespace-trimmed on write.
    TEXT_FIELDS = frozenset({"merchant", "notes"})

    def update(self, user: User, expense_id: str, updates: dict[str, object]) -> Expense:
        """Apply a partial update."""
        expense = self.get(user, expense_id)
        with atomic(self._session):
            for field, value in updates.items():
                setattr(
                    expense,
                    field,
                    _clean(value) if field in self.TEXT_FIELDS else value,
                )
        self._session.refresh(expense)
        return expense

    @retry_on_locked()
    def delete(self, user: User, expense_id: str) -> None:
        """Delete an expense."""
        expense = self.get(user, expense_id)
        with atomic(self._session):
            self._session.delete(expense)


def _clean(value: object) -> object:
    """Trim whitespace and collapse an empty string to ``None``.

    ``""`` and ``None`` are the same absence of information; storing both
    means every later query has to test for two things.
    """
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    return stripped or None
