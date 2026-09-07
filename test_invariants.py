"""Schema invariants.

These are the rules the design documents call correctness properties rather
than features. They are asserted against the schema itself, so violating one
fails a build instead of relying on a reviewer noticing a migration diff.
"""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import Float, Numeric, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.money import format_paise
from app.models import Base, CheckIn, Expense, LifeEvent, User


@pytest.fixture
def user(db: Session) -> User:
    """A persisted user to hang owned rows off."""
    record = User(display_name="Invariant Fixture")
    db.add(record)
    db.commit()
    return record


class TestHabitColumnsHaveNoDefault:
    """⭐ SRS-5.5 / ADR-007 — the single most important rule in the schema.

    NULL must stay distinguishable from a recorded ``False``/``0``. A DEFAULT
    on any habit column silently converts "didn't log" into "didn't do it",
    which manufactures correlations out of absent data.
    """

    def test_no_habit_column_declares_a_default(self) -> None:
        columns = CheckIn.__table__.columns
        offenders = [
            name
            for name in CheckIn.HABIT_FIELDS
            if columns[name].default is not None or columns[name].server_default is not None
        ]
        assert offenders == [], (
            f"Habit columns must not have defaults: {offenders}. "
            "See models/check_in.py — this is a correctness regression."
        )

    def test_every_habit_column_is_nullable(self) -> None:
        columns = CheckIn.__table__.columns
        not_nullable = [n for n in CheckIn.HABIT_FIELDS if not columns[n].nullable]
        assert not_nullable == [], f"Habit columns must be nullable: {not_nullable}"

    def test_recorded_negative_survives_a_round_trip_distinct_from_unknown(
        self, db: Session, user: User
    ) -> None:
        db.add(CheckIn(user_id=user.id, log_date=date(2026, 7, 1), exercise=False))
        db.add(
            CheckIn(user_id=user.id, log_date=date(2026, 7, 2), exercise=None, stress_level=3)
        )
        db.commit()
        db.expire_all()

        recorded_negative = db.scalars(
            select(CheckIn).where(CheckIn.log_date == date(2026, 7, 1))
        ).one()
        unknown = db.scalars(
            select(CheckIn).where(CheckIn.log_date == date(2026, 7, 2))
        ).one()

        assert recorded_negative.exercise is False, "an explicit 'no' must persist as False"
        assert unknown.exercise is None, "an unlogged habit must persist as NULL"


class TestMoneyIsNeverFloat:
    """SRS-3.10 / ADR-003 — no float type may hold money."""

    def test_amount_column_is_an_integer_type(self) -> None:
        column = Expense.__table__.columns["amount_paise"]
        assert not isinstance(column.type, (Float, Numeric)), (
            "amount_paise must be an integer type. A float column for money "
            "is rejected (05_Database_Design.md §9)."
        )
        assert column.type.python_type is int

    def test_no_table_holds_money_in_a_float_column(self) -> None:
        float_columns = [
            f"{table.name}.{column.name}"
            for table in Base.metadata.tables.values()
            for column in table.columns
            if isinstance(column.type, (Float, Numeric))
        ]
        assert float_columns == [], f"Unexpected float/decimal columns: {float_columns}"

    @pytest.mark.parametrize(
        ("paise", "expected"),
        [(0, "0.00"), (5, "0.05"), (100, "1.00"), (412050, "4120.50"), (-5, "-0.05")],
    )
    def test_formatting_uses_integer_arithmetic(self, paise: int, expected: str) -> None:
        assert format_paise(paise) == expected

    def test_large_amounts_do_not_drift(self) -> None:
        """The case a float would get wrong: beyond 2^53 paise."""
        assert format_paise(9_007_199_254_740_993) == "90071992547409.93"


class TestOwnershipAndCascade:
    """SRS-8.1 / 8.6 — every owned row cascades away with its user."""

    def test_every_owned_table_has_a_cascading_user_id_foreign_key(self) -> None:
        for model in (Expense, CheckIn, LifeEvent):
            foreign_keys = list(model.__table__.columns["user_id"].foreign_keys)
            assert foreign_keys, f"{model.__tablename__} must have a user_id FK"
            assert foreign_keys[0].ondelete == "CASCADE", (
                f"{model.__tablename__}.user_id must cascade on delete"
            )

    def test_deleting_the_user_removes_every_owned_row(
        self, db: Session, user: User
    ) -> None:
        db.add(Expense(user_id=user.id, expense_date=date(2026, 7, 1), amount_paise=100))
        db.add(CheckIn(user_id=user.id, log_date=date(2026, 7, 1), exercise=True))
        db.add(
            LifeEvent(
                user_id=user.id,
                event_type="TRAVEL",
                title="Trip",
                start_date=date(2026, 7, 1),
            )
        )
        db.commit()

        db.delete(user)
        db.commit()

        # No user-attributable row survives — asserted table by table (SRS-10.11).
        assert db.scalars(select(Expense)).all() == []
        assert db.scalars(select(CheckIn)).all() == []
        assert db.scalars(select(LifeEvent)).all() == []

    def test_sqlite_foreign_keys_are_actually_enforced(self, db: Session) -> None:
        """Guards the ``PRAGMA foreign_keys=ON`` in ``core/database.py``.

        SQLite ignores foreign keys unless asked not to. Without the pragma
        the cascade test above would still pass — the ORM would have done the
        deleting — while a direct SQL writer silently orphaned rows.
        """
        db.add(
            Expense(user_id="no-such-user", expense_date=date(2026, 7, 1), amount_paise=100)
        )
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


class TestSchemaConstraints:
    """Constraints that back business rules the API also enforces."""

    def test_one_check_in_per_user_per_date(self, db: Session, user: User) -> None:
        db.add(CheckIn(user_id=user.id, log_date=date(2026, 7, 1), exercise=True))
        db.commit()

        db.add(CheckIn(user_id=user.id, log_date=date(2026, 7, 1), exercise=False))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

    @pytest.mark.parametrize("amount", [0, -1])
    def test_expense_amount_must_be_positive(
        self, db: Session, user: User, amount: int
    ) -> None:
        db.add(Expense(user_id=user.id, expense_date=date(2026, 7, 1), amount_paise=amount))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

    def test_life_event_end_date_cannot_precede_start(
        self, db: Session, user: User
    ) -> None:
        db.add(
            LifeEvent(
                user_id=user.id,
                event_type="TRAVEL",
                title="Backwards",
                start_date=date(2026, 7, 10),
                end_date=date(2026, 7, 1),
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

    def test_all_expected_tables_exist(self, db: Session) -> None:
        tables = set(inspect(db.get_bind()).get_table_names())
        assert {"user", "expense", "check_in", "life_event"} <= tables
