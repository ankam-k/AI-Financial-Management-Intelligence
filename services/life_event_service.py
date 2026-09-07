"""Life event CRUD."""

from __future__ import annotations

from datetime import date

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.core.clock import Clock
from app.core.unit_of_work import atomic, retry_on_locked
from app.domain.enums import EventType
from app.domain.errors import NotFoundError, ValidationError
from app.models.life_event import LifeEvent
from app.models.user import User
from app.schemas.life_event import LifeEventCreate


class LifeEventService:
    """Business rules for user-annotated life events."""

    #: Free-text columns that get whitespace-trimmed on write.
    TEXT_FIELDS = frozenset({"title", "notes"})

    def __init__(self, session: Session, clock: Clock) -> None:
        self._session = session
        self._clock = clock

    def create(self, user: User, payload: LifeEventCreate) -> LifeEvent:
        """Record a new life event."""
        event = LifeEvent(
            user_id=user.id,
            event_type=payload.event_type,
            title=payload.title.strip(),
            start_date=payload.start_date,
            end_date=payload.end_date,
            notes=_clean(payload.notes),
        )
        with atomic(self._session):
            self._session.add(event)
        self._session.refresh(event)
        return event

    def get(self, user: User, event_id: str) -> LifeEvent:
        """Fetch one event, or raise ``NotFoundError``."""
        event = self._session.scalars(
            select(LifeEvent).where(
                LifeEvent.id == event_id, LifeEvent.user_id == user.id
            )
        ).first()
        if event is None:
            raise NotFoundError(f"No life event with id '{event_id}'")
        return event

    def list(
        self,
        user: User,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        event_type: EventType | None = None,
    ) -> list[LifeEvent]:
        """List events **overlapping** the given window, most recent first.

        Overlap, not containment: a relocation that began before the window
        and ended inside it still explains spending inside the window, so
        filtering on ``start_date`` alone would hide exactly the events an
        analyst most needs to see.
        """
        if start_date is not None and end_date is not None and end_date < start_date:
            raise ValidationError("'end_date' cannot be before 'start_date'")

        query = select(LifeEvent).where(LifeEvent.user_id == user.id)

        if end_date is not None:
            # The event must begin on or before the window ends.
            query = query.where(LifeEvent.start_date <= end_date)
        if start_date is not None:
            # ...and must not have finished before the window began. A point
            # event (end_date IS NULL) occupies start_date only.
            query = query.where(
                or_(
                    and_(
                        LifeEvent.end_date.is_(None),
                        LifeEvent.start_date >= start_date,
                    ),
                    LifeEvent.end_date >= start_date,
                )
            )
        if event_type is not None:
            query = query.where(LifeEvent.event_type == event_type)

        query = query.order_by(LifeEvent.start_date.desc(), LifeEvent.id.desc())
        return list(self._session.scalars(query))

    def update(self, user: User, event_id: str, updates: dict[str, object]) -> LifeEvent:
        """Apply a partial update.

        Date ordering is re-checked against the merged result, because a
        request may send only one of the two dates.
        """
        event = self.get(user, event_id)

        start = updates.get("start_date", event.start_date)
        end = updates["end_date"] if "end_date" in updates else event.end_date
        if end is not None and start is not None and end < start:
            raise ValidationError("'end_date' cannot be before 'start_date'")

        # `min_length=1` accepts "   ", which would trim to NULL on a NOT NULL
        # column. Caught here rather than left to an integrity error.
        if isinstance(updates.get("title"), str) and not updates["title"].strip():
            raise ValidationError("'title' cannot be blank")

        with atomic(self._session):
            for field, value in updates.items():
                setattr(
                    event,
                    field,
                    _clean(value) if field in self.TEXT_FIELDS else value,
                )
        self._session.refresh(event)
        return event

    @retry_on_locked()
    def delete(self, user: User, event_id: str) -> None:
        """Delete a life event."""
        event = self.get(user, event_id)
        with atomic(self._session):
            self._session.delete(event)


def _clean(value: object) -> object:
    """Trim whitespace and collapse an empty string to ``None``."""
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    return stripped or None
