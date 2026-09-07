"""Life event schemas."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.enums import EventType
from app.models.life_event import LifeEvent
from app.schemas.common import EventTitle

_NON_NULLABLE = {"event_type", "title", "start_date"}


class LifeEventCreate(BaseModel):
    """A new life event."""

    model_config = ConfigDict(extra="forbid")

    event_type: EventType
    title: EventTitle
    start_date: date
    end_date: date | None = Field(
        default=None, description="Omit or null for a single-day event."
    )
    notes: str | None = None

    @model_validator(mode="after")
    def _check_date_order(self) -> "LifeEventCreate":
        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("'end_date' cannot be before 'start_date'")
        return self


class LifeEventUpdate(BaseModel):
    """Partial update. Omitted fields are left untouched.

    Date ordering cannot be validated here alone: a request sending only
    ``end_date`` must be checked against the *stored* ``start_date``. The
    service performs that check; the model catches only what it can see.
    """

    model_config = ConfigDict(extra="forbid")

    event_type: EventType | None = None
    title: EventTitle | None = None
    start_date: date | None = None
    end_date: date | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def _reject_explicit_nulls(self) -> "LifeEventUpdate":
        for name in self.model_fields_set & _NON_NULLABLE:
            if getattr(self, name) is None:
                raise ValueError(f"'{name}' cannot be set to null")
        return self

    def to_column_updates(self) -> dict[str, object]:
        """Return only the fields the client actually sent."""
        return self.model_dump(exclude_unset=True)


class LifeEventRead(BaseModel):
    """A life event as returned to the client."""

    id: str
    event_type: EventType
    title: str
    start_date: date
    end_date: date | None
    is_point_event: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, event: LifeEvent) -> "LifeEventRead":
        return cls(
            id=event.id,
            event_type=event.event_type,
            title=event.title,
            start_date=event.start_date,
            end_date=event.end_date,
            is_point_event=event.is_point_event,
            notes=event.notes,
            created_at=event.created_at,
            updated_at=event.updated_at,
        )
