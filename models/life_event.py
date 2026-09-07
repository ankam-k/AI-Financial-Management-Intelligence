"""Life events — user-annotated context.

A life event is the honest alternative to guessing. When spending spikes, a
statistical engine cannot tell "moved house" from "developed a habit"; the
user can, in one annotation. Events exist so the analysis engine can say
"excluding your relocation week" instead of reporting a pattern that was
really a one-off (SRS-5.9, SRS-5.10).

``end_date IS NULL`` means a point event, not an ongoing one.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import (
    CheckConstraint,
    Date,
    Enum as SAEnum,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums import EventType
from app.models.base import Base, IdentifiedEntity


class LifeEvent(IdentifiedEntity, Base):
    """Something that happened which might explain a spending change."""

    __tablename__ = "life_event"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )

    event_type: Mapped[EventType] = mapped_column(
        SAEnum(EventType, native_enum=False, length=20, validate_strings=True),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)

    start_date: Mapped[date] = mapped_column(Date, nullable=False)

    #: NULL = point event (SRS-5.10).
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "end_date IS NULL OR end_date >= start_date",
            name="ck_life_event_date_order",
        ),
        Index("ix_life_event_user_start", "user_id", "start_date"),
    )

    @property
    def is_point_event(self) -> bool:
        """True when the event occupies a single day."""
        return self.end_date is None

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<LifeEvent id={self.id!r} type={self.event_type!r} title={self.title!r}>"
