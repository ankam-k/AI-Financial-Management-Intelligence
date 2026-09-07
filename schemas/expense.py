"""Expense schemas.

Amounts cross the wire as **integer paise**, never as a decimal rupee number.
JSON has one numeric type and it is a double; accepting ``1234.56`` would put
a float in the middle of the money pipeline at the one place the project
cannot afford it (ADR-003). Responses carry a formatted ``amount_display``
string so a client never has to divide by 100 itself.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.enums import Category, PaymentMethod
from app.domain.money import format_paise
from app.models.expense import Expense

#: Columns that are NOT NULL in the schema. An update may omit them; it may
#: not explicitly set them to null.
_NON_NULLABLE = {"expense_date", "amount_paise", "category", "payment_method"}


class ExpenseCreate(BaseModel):
    """A new expense."""

    model_config = ConfigDict(extra="forbid")

    expense_date: date
    amount_paise: int = Field(gt=0, description="Amount in paise. 1 rupee = 100 paise.")
    category: Category = Category.UNCATEGORIZED
    payment_method: PaymentMethod = PaymentMethod.UPI
    merchant: str | None = Field(default=None, max_length=200)
    notes: str | None = None


class ExpenseUpdate(BaseModel):
    """Partial update. Omitted fields are left untouched."""

    model_config = ConfigDict(extra="forbid")

    expense_date: date | None = None
    amount_paise: int | None = Field(default=None, gt=0)
    category: Category | None = None
    payment_method: PaymentMethod | None = None
    merchant: str | None = Field(default=None, max_length=200)
    notes: str | None = None

    @model_validator(mode="after")
    def _reject_explicit_nulls(self) -> "ExpenseUpdate":
        for name in self.model_fields_set & _NON_NULLABLE:
            if getattr(self, name) is None:
                raise ValueError(f"'{name}' cannot be set to null")
        return self

    def to_column_updates(self) -> dict[str, object]:
        """Return only the fields the client actually sent.

        ``exclude_unset`` is what separates "clear the merchant" (sent as
        null) from "leave the merchant alone" (not sent at all).
        """
        return self.model_dump(exclude_unset=True)


class ExpenseRead(BaseModel):
    """An expense as returned to the client."""

    id: str
    expense_date: date
    amount_paise: int
    amount_display: str
    currency: str
    category: Category
    payment_method: PaymentMethod
    merchant: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, expense: Expense) -> "ExpenseRead":
        return cls(
            id=expense.id,
            expense_date=expense.expense_date,
            amount_paise=expense.amount_paise,
            amount_display=format_paise(expense.amount_paise),
            currency=expense.currency,
            category=expense.category,
            payment_method=expense.payment_method,
            merchant=expense.merchant,
            notes=expense.notes,
            created_at=expense.created_at,
            updated_at=expense.updated_at,
        )
