r"""Daily habit check-in.

⭐ **The most important table in the schema** (05_Database_Design.md §5.1).

    NO HABIT COLUMN HAS A DEFAULT.

Three states must stay distinguishable:

* **no row for a date**  → UNKNOWN for all habits          (SRS-5.5a)
* **NULL in a row**      → UNKNOWN for that habit only     (SRS-5.5b)
* **``False`` / ``0``**  → Recorded Negative: an explicit assertion that the
  behaviour did not occur                                  (SRS-5.5c)

A ``BOOLEAN NOT NULL DEFAULT FALSE`` on ``exercise`` would silently encode
"user didn't log" as "user didn't exercise." A user who logs gym visits only
on the days they go would appear to have skipped every unlogged day —
manufacturing a correlation out of nothing, while every individual row stayed
perfectly traceable.

**A migration adding a DEFAULT to any of these six columns is a correctness
regression and must be rejected in review.** ``tests/test_invariants.py``
asserts this at the schema level so the rule fails a build, not a code review.

``sleep_minutes`` note: the design document specifies ``NUMERIC(3,1)`` hours.
Stored here as integer minutes instead — SQLite has no exact decimal type and
would fall back to a float, which is precisely the representation this project
refuses elsewhere. The API still speaks in hours; ``app/domain`` owns nothing,
the schema layer converts. Integers in, integers out.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums import WorkMode
from app.models.base import Base, IdentifiedEntity


class CheckIn(IdentifiedEntity, Base):
    """One day's self-reported habits. Every habit field is optional."""

    __tablename__ = "check_in"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )

    log_date: Mapped[date] = mapped_column(Date, nullable=False)

    # ── The six habits. NULL allowed. NO DEFAULT. ───────────────────────────
    sleep_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    exercise: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    home_cooked_meals: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    stress_level: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    alcohol: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    work_mode: Mapped[WorkMode | None] = mapped_column(
        SAEnum(WorkMode, native_enum=False, length=16, validate_strings=True),
        nullable=True,
    )
    # ────────────────────────────────────────────────────────────────────────

    __table_args__ = (
        UniqueConstraint("user_id", "log_date", name="uq_checkin_user_date"),
        CheckConstraint(
            "sleep_minutes IS NULL OR (sleep_minutes >= 0 AND sleep_minutes <= 1440)",
            name="ck_checkin_sleep_range",
        ),
        CheckConstraint(
            "home_cooked_meals IS NULL OR (home_cooked_meals >= 0 AND home_cooked_meals <= 3)",
            name="ck_checkin_meals_range",
        ),
        CheckConstraint(
            "stress_level IS NULL OR (stress_level >= 1 AND stress_level <= 5)",
            name="ck_checkin_stress_range",
        ),
        Index("ix_checkin_user_date", "user_id", "log_date"),
    )

    #: The six habit columns, named once so tests and future analysis code
    #: iterate over a single source of truth.
    HABIT_FIELDS: tuple[str, ...] = (
        "sleep_minutes",
        "exercise",
        "home_cooked_meals",
        "stress_level",
        "alcohol",
        "work_mode",
    )

    def is_empty(self) -> bool:
        """True when every habit is UNKNOWN.

        A row in this state records nothing a missing row would not, so the
        service layer rejects it rather than storing a fact-free row that
        would inflate logging-coverage statistics (SRS-6.2).
        """
        return all(getattr(self, field) is None for field in self.HABIT_FIELDS)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<CheckIn id={self.id!r} log_date={self.log_date!r}>"
