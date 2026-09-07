"""Check-in endpoints.

The resource is keyed by ``log_date``, not by an opaque id — there is at most
one check-in per day, so the date *is* the identifier. ``GET
/api/check-ins/2026-07-20`` reads better than fetching a list to find a uuid,
and it makes the one-per-day rule visible in the URL space.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import CheckInServiceDep, CurrentUser
from app.schemas.check_in import CheckInCreate, CheckInRead, CheckInUpdate

router = APIRouter(prefix="/api/check-ins", tags=["check-ins"])


@router.post(
    "",
    response_model=CheckInRead,
    status_code=status.HTTP_201_CREATED,
    summary="Log a daily check-in",
)
def create_check_in(
    payload: CheckInCreate, user: CurrentUser, check_ins: CheckInServiceDep
) -> CheckInRead:
    """Log habits for a date.

    Every habit is optional. **Omitting a habit means UNKNOWN — it does not
    mean it did not happen.** Send ``false``/``0`` to record that it did not.
    """
    return CheckInRead.from_model(check_ins.create(user, payload))


@router.get("", response_model=list[CheckInRead], summary="List check-ins")
def list_check_ins(
    user: CurrentUser,
    check_ins: CheckInServiceDep,
    start_date: Annotated[date | None, Query(description="Inclusive lower bound")] = None,
    end_date: Annotated[date | None, Query(description="Inclusive upper bound")] = None,
) -> list[CheckInRead]:
    """List check-ins newest first.

    Dates the user never logged are absent from the response rather than
    returned as blank rows.
    """
    rows = check_ins.list(user, start_date=start_date, end_date=end_date)
    return [CheckInRead.from_model(row) for row in rows]


@router.get(
    "/{log_date}",
    response_model=CheckInRead,
    summary="Get the check-in for a date",
)
def read_check_in(
    log_date: date, user: CurrentUser, check_ins: CheckInServiceDep
) -> CheckInRead:
    """Fetch one day's check-in. A 404 means UNKNOWN, not "nothing happened"."""
    return CheckInRead.from_model(check_ins.get(user, log_date))


@router.patch(
    "/{log_date}",
    response_model=CheckInRead,
    summary="Update the check-in for a date",
)
def update_check_in(
    log_date: date,
    payload: CheckInUpdate,
    user: CurrentUser,
    check_ins: CheckInServiceDep,
) -> CheckInRead:
    """Partial update.

    Omitting a field leaves it unchanged. Sending it as ``null`` resets that
    habit to UNKNOWN. Those are different requests and produce different rows.
    """
    updated = check_ins.update(user, log_date, payload.to_column_updates())
    return CheckInRead.from_model(updated)


@router.delete(
    "/{log_date}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete the check-in for a date",
)
def delete_check_in(log_date: date, user: CurrentUser, check_ins: CheckInServiceDep) -> None:
    """Delete a day's check-in, returning that date to UNKNOWN."""
    check_ins.delete(user, log_date)
