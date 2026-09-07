"""The idempotent startup migration (``app.core.migrations``).

The contract is narrow and safety-critical: additive, idempotent, and
non-destructive, so it can carry a pre-V1.2 SQLite database (including a
persistent Docker volume) onto the V1.2 auth schema without dropping anything.
Every scenario the owner asked to be proven is here: fresh DB, pre-V1.2 DB,
already-applied, and repeated runs.
"""

from __future__ import annotations

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from sqlalchemy.orm import Session

from app.core.database import build_engine
from app.core.migrations import run_migrations
from app.models import Base, User

#: The auth columns added in M2.
AUTH_COLUMNS = {"email", "password_hash", "is_demo"}

#: The onboarding / personalisation columns added in M5.
ONBOARDING_COLUMNS = {
    "onboarding_completed",
    "life_stage",
    "income_pattern",
    "work_context",
    "household_context",
    "focus_areas",
    "tracked_categories",
    "tracked_habits",
}

#: Everything the migration must add to a pre-V1.2 ``user`` table.
NEW_COLUMNS = AUTH_COLUMNS | ONBOARDING_COLUMNS


def user_columns(engine) -> set[str]:
    return {c["name"] for c in inspect(engine).get_columns("user")}


def user_indexes(engine) -> set[str]:
    return {i["name"] for i in inspect(engine).get_indexes("user")}


def _legacy_v11_database():
    """An engine whose ``user`` table is the pre-V1.2 shape — no auth columns."""
    engine = build_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE "user" (
                    id VARCHAR(36) PRIMARY KEY,
                    display_name VARCHAR(120) NOT NULL,
                    timezone VARCHAR(64) NOT NULL,
                    currency VARCHAR(3) NOT NULL,
                    monthly_budget_paise BIGINT,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL
                )
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO "user"
                    (id, display_name, timezone, currency, created_at, updated_at)
                VALUES
                    ('legacy-1', 'Local User', 'Asia/Kolkata', 'INR',
                     '2026-07-01 00:00:00', '2026-07-01 00:00:00')
                """
            )
        )
    return engine


class TestFreshDatabase:
    def test_create_all_then_migrate_is_a_noop(self):
        engine = build_engine("sqlite://")
        Base.metadata.create_all(bind=engine)
        # create_all already built the final schema from the models.
        assert NEW_COLUMNS <= user_columns(engine)

        applied = run_migrations(engine)
        assert applied == []  # nothing left to do
        assert "uq_user_email" in user_indexes(engine)

    def test_migrate_with_no_tables_yet_is_safe(self):
        engine = build_engine("sqlite://")  # empty database, no user table
        assert run_migrations(engine) == []


class TestLegacyUpgrade:
    def test_missing_columns_and_index_are_added(self):
        engine = _legacy_v11_database()
        assert not (NEW_COLUMNS & user_columns(engine))  # start without them

        applied = run_migrations(engine)

        assert set(applied) == {f"add user.{c}" for c in NEW_COLUMNS} | {
            "create index uq_user_email"
        }
        assert NEW_COLUMNS <= user_columns(engine)
        assert "uq_user_email" in user_indexes(engine)

    def test_the_existing_row_survives_untouched(self):
        engine = _legacy_v11_database()
        run_migrations(engine)
        with engine.begin() as conn:
            row = conn.execute(
                text(
                    "SELECT display_name, email, is_demo, onboarding_completed, "
                    'life_stage, focus_areas FROM "user" WHERE id = :i'
                ),
                {"i": "legacy-1"},
            ).one()
        assert row.display_name == "Local User"  # preserved
        assert row.email is None  # new column, defaulted to NULL
        assert row.is_demo == 0  # NOT NULL DEFAULT 0
        # M5 columns upgrade a legacy row to "not yet onboarded, nothing chosen".
        assert row.onboarding_completed == 0  # NOT NULL DEFAULT 0
        assert row.life_stage is None  # nullable, unanswered
        assert row.focus_areas == "[]"  # NOT NULL DEFAULT '[]'

    def test_running_twice_applies_nothing_the_second_time(self):
        engine = _legacy_v11_database()
        first = run_migrations(engine)
        second = run_migrations(engine)
        assert first  # the first run did work
        assert second == []  # the second is a clean no-op

    def test_repeated_runs_never_error(self):
        engine = _legacy_v11_database()
        for _ in range(5):
            run_migrations(engine)
        assert NEW_COLUMNS <= user_columns(engine)


class TestOnboardingColumnsRoundTrip:
    """The M5 JSON columns must behave identically whether the row came from a
    fresh ``create_all`` or from migrating a legacy database — the ``JSON``
    ALTER DDL and the model's JSON type have to agree, or a migrated store would
    read a raw string where a fresh one reads a list."""

    def test_migrated_json_column_reads_back_as_a_list(self):
        engine = _legacy_v11_database()
        run_migrations(engine)

        with Session(engine) as session:
            legacy = session.get(User, "legacy-1")
            assert legacy is not None
            assert legacy.focus_areas == []  # not the string "[]"
            assert legacy.tracked_categories == []
            assert legacy.tracked_habits == []
            assert legacy.onboarding_completed is False

            legacy.focus_areas = ["SAVE_MORE"]
            legacy.tracked_habits = ["exercise", "sleep_minutes"]
            session.commit()

        with Session(engine) as session:
            reloaded = session.get(User, "legacy-1")
            assert reloaded is not None
            assert reloaded.focus_areas == ["SAVE_MORE"]
            assert reloaded.tracked_habits == ["exercise", "sleep_minutes"]


class TestEmailUniqueness:
    def _migrated(self):
        engine = _legacy_v11_database()
        run_migrations(engine)
        return engine

    def _insert(self, engine, uid: str, email):
        with engine.begin() as conn:
            conn.execute(
                text(
                    'INSERT INTO "user" (id, display_name, timezone, currency, '
                    "email, is_demo, created_at, updated_at) VALUES "
                    "(:id, 'x', 'Asia/Kolkata', 'INR', :email, 0, "
                    "'2026-07-02 00:00:00', '2026-07-02 00:00:00')"
                ),
                {"id": uid, "email": email},
            )

    def test_duplicate_non_null_emails_are_rejected(self):
        engine = self._migrated()
        self._insert(engine, "u1", "same@example.com")
        with pytest.raises(IntegrityError):
            self._insert(engine, "u2", "same@example.com")

    def test_multiple_null_emails_are_allowed(self):
        # The partial index (WHERE email IS NOT NULL) must not collide the
        # credential-less legacy/demo rows against each other.
        engine = self._migrated()
        self._insert(engine, "u1", None)
        self._insert(engine, "u2", None)  # must not raise
