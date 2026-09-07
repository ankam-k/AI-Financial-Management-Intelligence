"""Expense endpoints."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, ExpenseServiceDep
from app.domain.enums import Category
from app.schemas.expense import ExpenseCreate, ExpenseRead, ExpenseUpdate

router = APIRouter(prefix="/api/expenses", tags=["expenses"])


@router.post(
    "",
    response_model=ExpenseRead,
    status_code=status.HTTP_201_CREATED,
    summary="Record an expense",
)
def create_expense(
    payload: ExpenseCreate, user: CurrentUser, expenses: ExpenseServiceDep
) -> ExpenseRead:
    """Record a new expense. ``amount_paise`` is an integer: ₹120.50 → 12050."""
    return ExpenseRead.from_model(expenses.create(user, payload))


@router.get("", response_model=list[ExpenseRead], summary="List expenses")
def list_expenses(
    user: CurrentUser,
    expenses: ExpenseServiceDep,
    start_date: Annotated[date | None, Query(description="Inclusive lower bound")] = None,
    end_date: Annotated[date | None, Query(description="Inclusive upper bound")] = None,
    category: Annotated[Category | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ExpenseRead]:
    """List expenses newest first, optionally filtered by date range and category."""
    rows = expenses.list(
        user,
        start_date=start_date,
        end_date=end_date,
        category=category,
        limit=limit,
        offset=offset,
    )
    return [ExpenseRead.from_model(row) for row in rows]


@router.get("/{expense_id}", response_model=ExpenseRead, summary="Get one expense")
def read_expense(
    expense_id: str, user: CurrentUser, expenses: ExpenseServiceDep
) -> ExpenseRead:
    return ExpenseRead.from_model(expenses.get(user, expense_id))


@router.patch("/{expense_id}", response_model=ExpenseRead, summary="Update an expense")
def update_expense(
    expense_id: str,
    payload: ExpenseUpdate,
    user: CurrentUser,
    expenses: ExpenseServiceDep,
) -> ExpenseRead:
    """Partial update. Omitted fields are unchanged; ``merchant``/``notes``
    may be sent as null to clear them."""
    updated = expenses.update(user, expense_id, payload.to_column_updates())
    return ExpenseRead.from_model(updated)


@router.delete(
    "/{expense_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an expense",
)
def delete_expense(expense_id: str, user: CurrentUser, expenses: ExpenseServiceDep) -> None:
    expenses.delete(user, expense_id)
