"""Tests for the transaction and connection hardening (V1.2).

These cover the machinery that stands between a service and the database:

* the SQLite pragmas every connection is brought up to (WAL, foreign keys,
  busy timeout);
* :func:`app.core.unit_of_work.atomic` — commit on success, roll back and
  translate on failure;
* :func:`app.core.unit_of_work.retry_on_locked` — bounded retry for the
  transient-lock case only.
"""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import build_engine
from app.core.unit_of_work import atomic, retry_on_locked
from app.domain.errors import ConflictError, ValidationError
from app.models.base import Base
from app.models.check_in import CheckIn
from app.models.user import User


# ── Connection pragmas ───────────────────────────────────────────────────────


def _pragma(engine, name: str):
    with engine.connect() as conn:
        return conn.exec_driver_sql(f"PRAGMA {name}").scalar()


def test_file_database_enables_wal_and_foreign_keys(tmp_path) -> None:
    """An on-disk database gets WAL journalling and enforced foreign keys."""
    engine = build_engine(f"sqlite:///{(tmp_path / 'afi.db').as_posix()}")
    try:
        assert _pragma(engine, "journal_mode").lower() == "wal"
        assert _pragma(engine, "foreign_keys") == 1
        assert _pragma(engine, "busy_timeout") == 5000
    finally:
        engine.dispose()


def test_memory_database_keeps_foreign_keys_but_not_wal() -> None:
    """In-memory databases enforce foreign keys but skip WAL (there is no file)."""
    engine = build_engine("sqlite://")
    try:
        assert _pragma(engine, "foreign_keys") == 1
        assert _pragma(engine, "journal_mode").lower() == "memory"
    finally:
        engine.dispose()


def test_foreign_key_cascade_actually_deletes_children(tmp_path) -> None:
    """The point of the pragma: ON DELETE CASCADE fires. A user's check-ins go
    with the user instead of being left orphaned."""
    engine = build_engine(f"sqlite:///{(tmp_path / 'fk.db').as_posix()}")
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        with factory() as s:
            user = User(display_name="Casc")
            s.add(user)
            s.flush()
            s.add(CheckIn(user_id=user.id, log_date=date(2026, 7, 1), exercise=True))
            s.commit()
            uid = user.id
        with factory() as s:
            s.execute(text("DELETE FROM \"user\" WHERE id = :i"), {"i": uid})
            s.commit()
        with factory() as s:
            remaining = s.scalars(
                select(CheckIn).where(CheckIn.user_id == uid)
            ).all()
            assert remaining == []
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


# ── atomic() ─────────────────────────────────────────────────────────────────


@pytest.fixture
def db(tmp_path) -> Session:
    engine = build_engine("sqlite://")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    yield session
    session.close()
    engine.dispose()


def test_atomic_commits_on_success(db: Session) -> None:
    with atomic(db):
        db.add(User(display_name="Committed"))
    assert db.scalars(select(User)).first().display_name == "Committed"


def test_atomic_rolls_back_on_error(db: Session) -> None:
    with pytest.raises(RuntimeError):
        with atomic(db):
            db.add(User(display_name="Doomed"))
            raise RuntimeError("boom")
    # Rolled back: the pending insert never reached the table, and the session
    # is usable again rather than stuck in a failed transaction.
    assert db.scalars(select(User)).all() == []


def test_atomic_maps_unique_violation_to_conflict(db: Session) -> None:
    user = User(display_name="U")
    with atomic(db):
        db.add(user)
    db.add(CheckIn(user_id=user.id, log_date=date(2026, 7, 1), exercise=True))
    db.commit()

    # A second check-in for the same (user, date) violates the unique index.
    with pytest.raises(ConflictError):
        with atomic(db):
            db.add(CheckIn(user_id=user.id, log_date=date(2026, 7, 1), alcohol=False))


def test_atomic_maps_check_violation_to_validation(db: Session) -> None:
    user = User(display_name="U")
    with atomic(db):
        db.add(user)
    # stress_level must be 1..5; 9 trips the CHECK constraint.
    with pytest.raises(ValidationError):
        with atomic(db):
            db.add(CheckIn(user_id=user.id, log_date=date(2026, 7, 2), stress_level=9))


def test_atomic_passes_domain_errors_through(db: Session) -> None:
    with pytest.raises(ValidationError, match="mine"):
        with atomic(db):
            db.add(User(display_name="Rolled"))
            raise ValidationError("mine")
    assert db.scalars(select(User)).all() == []


# ── retry_on_locked() ────────────────────────────────────────────────────────


def _locked_error() -> OperationalError:
    return OperationalError("stmt", {}, Exception("database is locked"))


def test_retry_succeeds_after_transient_lock() -> None:
    calls = {"n": 0}

    @retry_on_locked(attempts=3, base_delay=0)
    def flaky() -> str:
        calls["n"] += 1
        if calls["n"] < 3:
            raise _locked_error()
        return "ok"

    assert flaky() == "ok"
    assert calls["n"] == 3


def test_retry_gives_up_after_attempts() -> None:
    calls = {"n": 0}

    @retry_on_locked(attempts=2, base_delay=0)
    def always_locked() -> None:
        calls["n"] += 1
        raise _locked_error()

    with pytest.raises(OperationalError):
        always_locked()
    assert calls["n"] == 2


def test_retry_does_not_swallow_other_operational_errors() -> None:
    calls = {"n": 0}

    @retry_on_locked(attempts=4, base_delay=0)
    def other() -> None:
        calls["n"] += 1
        raise OperationalError("stmt", {}, Exception("no such table: nope"))

    with pytest.raises(OperationalError):
        other()
    assert calls["n"] == 1  # not a lock → no retry
