"""Life event endpoints."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, LifeEventServiceDep
from app.domain.enums import EventType
from app.schemas.life_event import LifeEventCreate, LifeEventRead, LifeEventUpdate

router = APIRouter(prefix="/api/life-events", tags=["life-events"])


@router.post(
    "",
    response_model=LifeEventRead,
    status_code=status.HTTP_201_CREATED,
    summary="Record a life event",
)
def create_life_event(
    payload: LifeEventCreate, user: CurrentUser, events: LifeEventServiceDep
) -> LifeEventRead:
    """Record something that might explain a change in spending.

    Omit ``end_date`` for a single-day event.
    """
    return LifeEventRead.from_model(events.create(user, payload))


@router.get("", response_model=list[LifeEventRead], summary="List life events")
def list_life_events(
    user: CurrentUser,
    events: LifeEventServiceDep,
    start_date: Annotated[date | None, Query(description="Window start")] = None,
    end_date: Annotated[date | None, Query(description="Window end")] = None,
    event_type: Annotated[EventType | None, Query()] = None,
) -> list[LifeEventRead]:
    """List events overlapping the window, most recent first."""
    rows = events.list(
        user, start_date=start_date, end_date=end_date, event_type=event_type
    )
    return [LifeEventRead.from_model(row) for row in rows]


@router.get("/{event_id}", response_model=LifeEventRead, summary="Get one life event")
def read_life_event(
    event_id: str, user: CurrentUser, events: LifeEventServiceDep
) -> LifeEventRead:
    return LifeEventRead.from_model(events.get(user, event_id))


@router.patch("/{event_id}", response_model=LifeEventRead, summary="Update a life event")
def update_life_event(
    event_id: str,
    payload: LifeEventUpdate,
    user: CurrentUser,
    events: LifeEventServiceDep,
) -> LifeEventRead:
    """Partial update. Send ``end_date: null`` to turn a range into a point event."""
    updated = events.update(user, event_id, payload.to_column_updates())
    return LifeEventRead.from_model(updated)


@router.delete(
    "/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a life event",
)
def delete_life_event(event_id: str, user: CurrentUser, events: LifeEventServiceDep) -> None:
    events.delete(user, event_id)
