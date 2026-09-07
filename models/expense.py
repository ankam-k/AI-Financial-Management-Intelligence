"""Expenses — the V1 ledger entry.

This is a deliberately reduced ``transaction`` (05_Database_Design.md §3.4).
V1 is manual entry, so everything the documented table carries for *imported*
rows is absent: no ``raw_record`` provenance link, no ``dedup_key``, no
``normalization_version``, no merchant table. A hand-typed row has no source
row to reconstruct and cannot be imported twice, so those columns would encode
nothing (ADR-014).

What survives is what correctness depends on: integer paise, currency as a
column, an indexed ``(user_id, expense_date)`` for the window queries the
analysis engine will run, and cascade on delete.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    Enum as SAEnum,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums import Category, PaymentMethod
from app.models.base import Base, IdentifiedEntity


class Expense(IdentifiedEntity, Base):
    """A single outflow of money."""

    __tablename__ = "expense"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )

    expense_date: Mapped[date] = mapped_column(Date, nullable=False)

    #: Money is BIGINT paise and always will be. A migration introducing a
    #: float type for money is rejected (05_Database_Design.md §9).
    #: Positive magnitude: in V1 every row is an outflow, so a sign bit would
    #: carry no information and invite "negative expense" ambiguity.
    amount_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)

    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")

    category: Mapped[Category] = mapped_column(
        SAEnum(Category, native_enum=False, length=32, validate_strings=True),
        nullable=False,
        default=Category.UNCATEGORIZED,
    )

    payment_method: Mapped[PaymentMethod] = mapped_column(
        SAEnum(PaymentMethod, native_enum=False, length=16, validate_strings=True),
        nullable=False,
        default=PaymentMethod.UPI,
    )

    #: Free text in V1. Merchant normalisation and the ``merchant`` table are
    #: a categorisation-sprint concern (ADR-005); a string here does not
    #: block that work, it just does not anticipate it.
    merchant: Mapped[str | None] = mapped_column(String(200), nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint("amount_paise > 0", name="ck_expense_amount_positive"),
        CheckConstraint("currency = 'INR'", name="ck_expense_currency_inr"),
        Index("ix_expense_user_date", "user_id", "expense_date"),
        Index("ix_expense_user_category", "user_id", "category"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"<Expense id={self.id!r} date={self.expense_date!r} "
            f"paise={self.amount_paise!r} category={self.category!r}>"
        )
