"""Loading the dataset into the database."""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.demo.generator import generate
from app.demo.loader import clear_demo_data, describe, load_demo_data
from app.models.check_in import CheckIn
from app.models.expense import Expense
from app.models.life_event import LifeEvent
from app.models.user import User

REFERENCE = date(2026, 7, 28)


@pytest.fixture(scope="module")
def dataset():
    return generate(REFERENCE)


class TestLoading:
    def test_it_creates_a_profile_when_none_exists(self, db: Session, dataset) -> None:
        status = load_demo_data(db, dataset)

        assert status.profile == dataset.persona.display_name
        assert status.monthly_budget_paise == dataset.persona.monthly_budget_paise

    def test_it_writes_every_record(self, db: Session, dataset) -> None:
        status = load_demo_data(db, dataset)

        assert status.expenses == len(dataset.expenses)
        assert status.check_ins == len(dataset.check_ins)
        assert status.events == len(dataset.events)

    def test_check_ins_bypass_the_backfill_window(self, db: Session, dataset) -> None:
        """⭐ This is what closes OEQ-004.

        The 30-day backfill cap lives in `CheckInService` because it is a rule
        about *user input*. Writing below the API leaves it intact for a real
        check-in while letting a synthetic dataset carry the ≥ 8 weeks of
        history the gates need.
        """
        load_demo_data(db, dataset)
        earliest = db.scalar(select(func.min(CheckIn.log_date)))

        assert (REFERENCE - earliest).days > 30

    def test_loading_twice_leaves_one_dataset(self, db: Session, dataset) -> None:
        """Not two overlapping ones that would double every total."""
        load_demo_data(db, dataset)
        status = load_demo_data(db, dataset)

        assert status.expenses == len(dataset.expenses)

    def test_the_profile_id_survives_a_reseed(self, db: Session, dataset) -> None:
        """A demo that hands out a new profile id on every reset makes
        bookmarked insight ids and screenshots stale for no reason."""
        load_demo_data(db, dataset)
        before = db.scalars(select(User)).one().id

        load_demo_data(db, dataset)

        assert db.scalars(select(User)).one().id == before

    def test_it_marks_the_demo_account_onboarded(self, db: Session, dataset) -> None:
        """Exploring the demo lands on a personalised dashboard, never the
        first-run onboarding wizard."""
        load_demo_data(db, dataset)
        user = db.scalars(select(User)).one()

        assert user.is_demo is True
        assert user.onboarding_completed is True
        assert user.tracked_habits  # personalised, so the demo shows it off

    def test_the_schema_invariants_still_apply(self, db: Session, dataset) -> None:
        """Writing below the API bypasses the transport, not the schema."""
        load_demo_data(db, dataset)

        amounts = db.scalars(select(Expense.amount_paise)).all()
        assert all(amount > 0 for amount in amounts)

        dates = db.scalars(select(CheckIn.log_date)).all()
        assert len(dates) == len(set(dates))


class TestClearing:
    def test_it_removes_every_record(self, db: Session, dataset) -> None:
        load_demo_data(db, dataset)

        status = clear_demo_data(db)

        assert status.is_empty
        assert db.scalars(select(Expense)).all() == []
        assert db.scalars(select(CheckIn)).all() == []
        assert db.scalars(select(LifeEvent)).all() == []

    def test_it_keeps_the_profile(self, db: Session, dataset) -> None:
        load_demo_data(db, dataset)

        status = clear_demo_data(db)

        assert status.profile == dataset.persona.display_name

    def test_clearing_an_empty_database_is_not_an_error(self, db: Session) -> None:
        assert clear_demo_data(db).is_empty


class TestDescribe:
    def test_it_reports_nothing_before_a_profile_exists(self, db: Session) -> None:
        status = describe(db)

        assert status.profile is None
        assert status.is_empty

    def test_it_reports_the_date_range(self, db: Session, dataset) -> None:
        load_demo_data(db, dataset)

        status = describe(db)

        assert status.latest == REFERENCE.isoformat()
        assert status.earliest is not None
        assert status.earliest < status.latest
