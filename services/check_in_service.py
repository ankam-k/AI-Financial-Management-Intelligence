"""Check-in CRUD.

Three rules live here rather than in the schema, because each needs something
the schema cannot see — the clock, or the stored row.

1. **Backfill window** (SRS-5.6/5.7): a check-in may be logged for today or
   any of the previous 30 days, never the future. Enforced against the
   injected clock, not as a database CHECK — ``CURRENT_DATE`` in a constraint
   is not deterministic and would make the schema unreproducible.

2. **One check-in per date** (SRS-5.3): the unique constraint enforces it;
   this layer turns the collision into a 409 with a usable message instead of
   an integrity error.

3. **No fact-free rows**: a check-in with all six habits UNKNOWN records
   nothing that a missing row does not, and would inflate the logging-coverage
   ratio the analysis engine gates on (SRS-6.2).
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import Clock
from app.core.unit_of_work import atomic, retry_on_locked
from app.domain.errors import ConflictError, NotFoundError, ValidationError
from app.models.check_in import CheckIn
from app.models.user import User
from app.schemas.check_in import CheckInCreate, hours_to_minutes


class CheckInService:
    """Business rules for daily habit logs."""

    def __init__(self, session: Session, clock: Clock, backfill_days: int = 30) -> None:
        self._session = session
        self._clock = clock
        self._backfill_days = backfill_days

    # ── Queries ─────────────────────────────────────────────────────────────

    def get(self, user: User, log_date: date) -> CheckIn:
        """Fetch the check-in for a date, or raise ``NotFoundError``.

        A 404 here means UNKNOWN, not "the user did nothing" — the caller must
        not read absence as a recorded negative (SRS-5.5a).
        """
        check_in = self._find(user, log_date)
        if check_in is None:
            raise NotFoundError(f"No check-in logged for {log_date.isoformat()}")
        return check_in

    def list(
        self,
        user: User,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[CheckIn]:
        """List check-ins in a date range, newest first.

        Dates with no row are simply absent from the result. The API does not
        fabricate placeholder rows, because a placeholder is indistinguishable
        from a logged day once it reaches the client.
        """
        if start_date is not None and end_date is not None and end_date < start_date:
            raise ValidationError("'end_date' cannot be before 'start_date'")

        query = select(CheckIn).where(CheckIn.user_id == user.id)
        if start_date is not None:
            query = query.where(CheckIn.log_date >= start_date)
        if end_date is not None:
            query = query.where(CheckIn.log_date <= end_date)

        return list(self._session.scalars(query.order_by(CheckIn.log_date.desc())))

    # ── Commands ────────────────────────────────────────────────────────────

    def create(self, user: User, payload: CheckInCreate) -> CheckIn:
        """Log a new check-in."""
        self._assert_within_backfill_window(payload.log_date)

        if self._find(user, payload.log_date) is not None:
            raise ConflictError(
                f"A check-in already exists for {payload.log_date.isoformat()}. "
                "Update it instead."
            )

        check_in = CheckIn(
            user_id=user.id,
            log_date=payload.log_date,
            sleep_minutes=hours_to_minutes(payload.sleep_hours),
            exercise=payload.exercise,
            home_cooked_meals=payload.home_cooked_meals,
            stress_level=payload.stress_level,
            alcohol=payload.alcohol,
            work_mode=payload.work_mode,
        )

        if check_in.is_empty():
            raise ValidationError("A check-in must record at least one habit.")

        # The pre-check above closes the common case; the unique constraint is
        # the real guard against a concurrent insert for the same date, and
        # ``atomic`` turns that raced IntegrityError into the same 409.
        with atomic(self._session):
            self._session.add(check_in)
        self._session.refresh(check_in)
        return check_in

    def update(self, user: User, log_date: date, updates: dict[str, object | None]) -> CheckIn:
        """Apply a partial update.

        ``updates`` contains only the fields the client sent. A field present
        with value ``None`` clears the habit to UNKNOWN — that is a legitimate
        correction ("I logged 7 hours but I actually don't remember"), and it
        is why this method cannot simply skip null values.
        """
        check_in = self.get(user, log_date)

        # The mutation and its guard run inside one unit of work: if the result
        # would be a fact-free row, the ValidationError unwinds the pending
        # changes so the caller never holds a mutated object the DB rejected.
        with atomic(self._session):
            for field, value in updates.items():
                setattr(check_in, field, value)

            if check_in.is_empty():
                raise ValidationError(
                    "That update would leave the check-in with no recorded habits. "
                    "Delete it instead."
                )
        self._session.refresh(check_in)
        return check_in

    @retry_on_locked()
    def delete(self, user: User, log_date: date) -> None:
        """Delete the check-in for a date, returning it to UNKNOWN."""
        check_in = self.get(user, log_date)
        with atomic(self._session):
            self._session.delete(check_in)

    # ── Internals ───────────────────────────────────────────────────────────

    def _find(self, user: User, log_date: date) -> CheckIn | None:
        return self._session.scalars(
            select(CheckIn).where(
                CheckIn.user_id == user.id, CheckIn.log_date == log_date
            )
        ).first()

    def _assert_within_backfill_window(self, log_date: date) -> None:
        today = self._clock.today()
        earliest = today - timedelta(days=self._backfill_days)

        if log_date > today:
            raise ValidationError("Cannot log a check-in for a future date.")
        if log_date < earliest:
            raise ValidationError(
                f"Check-ins can only be backfilled {self._backfill_days} days. "
                f"Earliest allowed date is {earliest.isoformat()}."
            )
