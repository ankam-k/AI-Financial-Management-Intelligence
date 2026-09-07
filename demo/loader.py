"""Writing the demo dataset to the database — and clearing it again.

**The only file in the demo path that performs I/O**, and the reason the
generator stays testable without a database.

This is also the file that closes OEQ-004, and it does so by writing below the
API rather than by relaxing a rule. The 30-day check-in backfill limit
(SRS-5.6/5.7) lives in ``CheckInService`` because it is a rule about *user
input*; a synthetic dataset is not user input. Nothing here weakens the
constraint for a real check-in, and the schema's own invariants — cascade,
uniqueness, the CHECK constraints — apply exactly as they always do.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.demo.generator import DemoDataset
from app.domain.enums import Category
from app.domain.preferences import (
    FocusArea,
    HouseholdContext,
    IncomePattern,
    LifeStage,
    WorkContext,
)
from app.models.check_in import CheckIn
from app.models.expense import Expense
from app.models.life_event import LifeEvent
from app.models.user import User


#: The display name a freshly-created demo account carries until
#: :func:`load_demo_data` overwrites it with the dataset persona. It only shows
#: if someone enters the demo account before it has been seeded.
_DEMO_PLACEHOLDER_NAME = "Demo"


def get_demo_user(session: Session) -> User | None:
    """Return the dedicated demo account, or ``None`` if it does not exist yet.

    The demo dataset lives in its **own** account (``is_demo = True``), never in
    a real user's rows. This is the V1.2 boundary (§9): seeding or clearing the
    demo can never touch — or be touched by — a signed-up user's data. There is
    at most one such account; ``order_by(created_at)`` makes the choice
    deterministic even if one were ever duplicated.
    """
    return session.scalars(
        select(User).where(User.is_demo.is_(True)).order_by(User.created_at)
    ).first()


def get_or_create_demo_user(session: Session) -> User:
    """Return the demo account, creating an empty one if it does not exist.

    The account is passwordless (``password_hash`` stays null) and has no email,
    so it can never be reached through the login flow — it is entered only by
    the explicit "Explore demo" path. Its id is stable across reseeds, so
    bookmarked insight ids and screenshots do not go stale.
    """
    user = get_demo_user(session)
    if user is None:
        user = User(display_name=_DEMO_PLACEHOLDER_NAME, is_demo=True)
        session.add(user)
        session.commit()
        session.refresh(user)
    return user


@dataclass(frozen=True, slots=True)
class DemoStatus:
    """What is currently in the database."""

    profile: str | None
    expenses: int
    check_ins: int
    events: int
    monthly_budget_paise: int | None
    earliest: str | None
    latest: str | None

    @property
    def is_empty(self) -> bool:
        return self.expenses == 0 and self.check_ins == 0 and self.events == 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "profile": self.profile,
            "expenses": self.expenses,
            "check_ins": self.check_ins,
            "events": self.events,
            "monthly_budget_paise": self.monthly_budget_paise,
            "earliest": self.earliest,
            "latest": self.latest,
            "is_empty": self.is_empty,
        }


def describe(session: Session) -> DemoStatus:
    """Report what is loaded in the demo account, without changing anything."""
    user = get_demo_user(session)
    if user is None:
        return DemoStatus(None, 0, 0, 0, None, None, None)

    counts = {
        "expenses": session.scalar(
            select(func.count()).select_from(Expense).where(Expense.user_id == user.id)
        )
        or 0,
        "check_ins": session.scalar(
            select(func.count()).select_from(CheckIn).where(CheckIn.user_id == user.id)
        )
        or 0,
        "events": session.scalar(
            select(func.count()).select_from(LifeEvent).where(LifeEvent.user_id == user.id)
        )
        or 0,
    }
    earliest: date | None = session.scalar(
        select(func.min(Expense.expense_date)).where(Expense.user_id == user.id)
    )
    latest: date | None = session.scalar(
        select(func.max(Expense.expense_date)).where(Expense.user_id == user.id)
    )

    return DemoStatus(
        profile=user.display_name,
        expenses=counts["expenses"],
        check_ins=counts["check_ins"],
        events=counts["events"],
        monthly_budget_paise=user.monthly_budget_paise,
        earliest=earliest.isoformat() if earliest else None,
        latest=latest.isoformat() if latest else None,
    )


def clear_demo_data(session: Session) -> DemoStatus:
    """Delete every user-owned row, keeping the profile itself.

    Bulk deletes rather than ``session.delete(user)``: removing the profile
    would cascade correctly but would also change the profile id, and a demo
    that hands out a new id on every reset makes bookmarked insight ids and
    screenshots stale for no reason.
    """
    user = get_demo_user(session)
    if user is None:
        return DemoStatus(None, 0, 0, 0, None, None, None)

    for model in (Expense, CheckIn, LifeEvent):
        session.execute(delete(model).where(model.user_id == user.id))
    session.commit()

    return describe(session)


def load_demo_data(session: Session, dataset: DemoDataset) -> DemoStatus:
    """Replace whatever is loaded with this dataset.

    Idempotent by construction: it clears first, so running it twice leaves
    the same database rather than two overlapping datasets that would double
    every total.

    The data always lands in the dedicated demo account (``is_demo = True``),
    never in a real user's rows — so seeding is safe regardless of who triggers
    it and how many real accounts exist.
    """
    user = get_or_create_demo_user(session)

    clear_demo_data(session)

    user.display_name = dataset.persona.display_name
    user.monthly_budget_paise = dataset.persona.monthly_budget_paise

    # The demo is already "onboarded": exploring it drops straight onto a
    # personalised dashboard, never into the first-run wizard. The preferences
    # match the persona and exist to *show* personalisation — they change which
    # cards lead, never the analysis (the engine never sees the User row).
    user.onboarding_completed = True
    user.life_stage = LifeStage.EARLY_CAREER.value
    user.income_pattern = IncomePattern.SALARIED_FIXED.value
    user.work_context = WorkContext.HYBRID.value
    user.household_context = HouseholdContext.LIVING_ALONE.value
    user.focus_areas = [FocusArea.UNDERSTAND_SPENDING.value, FocusArea.BUILD_HEALTHY_HABITS.value]
    user.tracked_categories = [
        Category.FOOD_DINING.value,
        Category.TRANSPORT.value,
        Category.GROCERIES.value,
        Category.SHOPPING.value,
    ]
    user.tracked_habits = ["sleep_minutes", "exercise", "home_cooked_meals", "stress_level"]

    session.add_all(
        Expense(
            user_id=user.id,
            expense_date=seed.expense_date,
            amount_paise=seed.amount_paise,
            currency=user.currency,
            category=seed.category,
            payment_method=seed.payment_method,
            merchant=seed.merchant,
            notes=seed.notes,
        )
        for seed in dataset.expenses
    )
    session.add_all(
        CheckIn(
            user_id=user.id,
            log_date=seed.log_date,
            sleep_minutes=seed.sleep_minutes,
            exercise=seed.exercise,
            home_cooked_meals=seed.home_cooked_meals,
            stress_level=seed.stress_level,
            alcohol=seed.alcohol,
            work_mode=seed.work_mode,
        )
        for seed in dataset.check_ins
    )
    session.add_all(
        LifeEvent(
            user_id=user.id,
            event_type=seed.event_type,
            title=seed.title,
            start_date=seed.start_date,
            end_date=seed.end_date,
            notes=seed.notes,
        )
        for seed in dataset.events
    )
    session.commit()

    return describe(session)
