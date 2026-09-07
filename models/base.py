"""Declarative base and shared column mixins.

**Timestamps are naive UTC.** SQLite has no timezone-aware column type and
silently drops ``tzinfo``, so storing aware datetimes would produce values
that read back subtly wrong. ``created_at``/``updated_at`` are server
bookkeeping; every *user-facing* date (``expense_date``, ``log_date``, event
dates) is a plain ``DATE`` carrying IST calendar semantics from the injected
clock (ADR-003).
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base for every ORM model."""


def new_id() -> str:
    """Generate a primary key.

    UUID4 stored as a 36-character string. SQLite has no native UUID type, and
    a string key ports to PostgreSQL's ``UUID`` without changing any value.
    """
    return str(uuid4())


def utcnow() -> datetime:
    """Naive UTC timestamp for audit columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class IdentifiedEntity:
    """Mixin supplying the surrogate key and audit timestamps."""

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, onupdate=utcnow
    )
