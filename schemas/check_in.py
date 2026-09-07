"""Check-in schemas.

Two things here carry real weight.

**1. Explicit null is meaningful.** ``PATCH {"exercise": null}`` means "I do
not know whether I exercised" and must clear the column. ``PATCH {}`` means
"change nothing" and must leave it alone. Pydantic's ``model_fields_set`` is
what distinguishes them; ``exclude_unset=True`` is not an optimisation here,
it is the semantics (SRS-5.5).

**2. Hours in, minutes stored.** The client speaks ``sleep_hours: 7.5``. The
column is integer minutes, so no float is ever persisted (see
``models/check_in.py``). Conversion happens here and nowhere else.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import WorkMode
from app.models.check_in import CheckIn

MINUTES_PER_HOUR = 60

#: Sleep is reported to a tenth of an hour; finer precision is not something a
#: person can self-report meaningfully.
_SLEEP_HOURS_PRECISION = 1


def hours_to_minutes(hours: float | None) -> int | None:
    """Convert reported hours to stored minutes."""
    if hours is None:
        return None
    return int(round(hours * MINUTES_PER_HOUR))


def minutes_to_hours(minutes: int | None) -> float | None:
    """Convert stored minutes back to reported hours."""
    if minutes is None:
        return None
    return round(minutes / MINUTES_PER_HOUR, _SLEEP_HOURS_PRECISION)


class _CheckInHabits(BaseModel):
    """The six habit fields. Every one is optional; none has a default value.

    ``None`` means UNKNOWN. ``False``/``0`` means the user asserted it did not
    happen. These are different facts and the schema keeps them different.
    """

    model_config = ConfigDict(extra="forbid")

    sleep_hours: float | None = Field(default=None, ge=0, le=24)
    exercise: bool | None = None
    home_cooked_meals: int | None = Field(default=None, ge=0, le=3)
    stress_level: int | None = Field(default=None, ge=1, le=5)
    alcohol: bool | None = None
    work_mode: WorkMode | None = None

    def to_column_updates(self) -> dict[str, object | None]:
        """Map the fields the client sent onto column names.

        Only fields present in the request appear in the result — that is what
        makes "set to unknown" and "leave unchanged" distinguishable.
        """
        updates: dict[str, object | None] = {}
        for name in self.model_fields_set:
            value = getattr(self, name)
            if name == "sleep_hours":
                updates["sleep_minutes"] = hours_to_minutes(value)
            else:
                updates[name] = value
        return updates


class CheckInCreate(_CheckInHabits):
    """A new check-in for a given date."""

    log_date: date


class CheckInUpdate(_CheckInHabits):
    """Partial update of an existing check-in.

    ``log_date`` is absent by design: the date identifies the resource, so
    moving a check-in is a delete plus a create, not an edit.
    """


class CheckInRead(BaseModel):
    """A check-in as returned to the client."""

    id: str
    log_date: date
    sleep_hours: float | None
    exercise: bool | None
    home_cooked_meals: int | None
    stress_level: int | None
    alcohol: bool | None
    work_mode: WorkMode | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, check_in: CheckIn) -> "CheckInRead":
        return cls(
            id=check_in.id,
            log_date=check_in.log_date,
            sleep_hours=minutes_to_hours(check_in.sleep_minutes),
            exercise=check_in.exercise,
            home_cooked_meals=check_in.home_cooked_meals,
            stress_level=check_in.stress_level,
            alcohol=check_in.alcohol,
            work_mode=check_in.work_mode,
            created_at=check_in.created_at,
            updated_at=check_in.updated_at,
        )
