"""Local profile management."""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.unit_of_work import atomic, retry_on_locked
from app.models.check_in import CheckIn
from app.models.expense import Expense
from app.models.life_event import LifeEvent
from app.models.user import User


class ProfileService:
    """Reads and updates the single local profile.

    V1 has no sign-up flow. The profile is created on first access so a fresh
    clone is usable immediately — the alternative, a mandatory onboarding
    call before any other endpoint works, buys nothing while there is exactly
    one user.
    """

    DEFAULT_DISPLAY_NAME = "Local User"

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_or_create(self) -> User:
        """Return the local profile, creating it on first call."""
        user = self._session.scalars(select(User).order_by(User.created_at)).first()
        if user is not None:
            return user

        user = User(display_name=self.DEFAULT_DISPLAY_NAME)
        with atomic(self._session):
            self._session.add(user)
        self._session.refresh(user)
        return user

    def update(self, user: User, updates: dict[str, object]) -> User:
        """Apply a partial update to the profile.

        The caller (the schema layer) has already validated and mapped the
        fields onto column names, so this only writes what it was handed —
        nothing here decides what is allowed to change.
        """
        with atomic(self._session):
            for field, value in updates.items():
                setattr(user, field, value)
        self._session.refresh(user)
        return user

    def complete_onboarding(self, user: User, updates: dict[str, object]) -> User:
        """Record the onboarding answers and mark the account onboarded.

        Marking ``onboarding_completed`` is what this method adds over a plain
        :meth:`update`: the answers are optional (onboarding can be skipped),
        but reaching this endpoint always means the user is past the first-run
        flow, so the flag flips regardless of how much was filled in. Idempotent
        — submitting again just updates the answers and leaves the flag true.
        """
        return self.update(user, {**updates, "onboarding_completed": True})

    @retry_on_locked()
    def delete_all_data(self, user: User) -> None:
        """Delete everything the user owns, **keeping the account itself**.

        This is Phase 18's "Delete all data": the user stays logged in and lands
        back on the empty first-run state, rather than being logged out with a
        vanished account. Deleting the *account* (email, credentials and all) is
        a separate, deliberately heavier action, not this one.

        The deletes are scoped by ``user_id`` — one user emptying their data can
        never touch another's — and are real and cascading at the row level (no
        soft-delete flag, 05_Database_Design.md §8, SRS-8.6).
        """
        # One transaction for all three deletes: either the account is fully
        # emptied or nothing changes — a partial wipe would leave orphaned
        # streams that read as a corrupted profile.
        with atomic(self._session):
            for model in (Expense, CheckIn, LifeEvent):
                self._session.execute(delete(model).where(model.user_id == user.id))
