"""Transaction management — the one place a write is committed.

Through V1.1 every service ended a mutation with a bare ``session.commit()``.
That works until a commit fails: a raced ``UNIQUE`` insert, a violated
``CHECK``, a dropped SQLite lock. A bare commit leaves two problems behind —
the session is left in a half-open state that the *next* request inherits, and
the failure surfaces as a raw :class:`sqlalchemy.exc.IntegrityError`, i.e. an
opaque HTTP 400 with a driver string in it.

This module gives every write one disciplined exit:

* :func:`atomic` — a context manager that commits on success and, on **any**
  failure, rolls the session back before the exception propagates. Database
  integrity failures are translated into the project's own
  :mod:`app.domain.errors`, so the API layer maps them to a real status code
  (a raced check-in becomes a 409, a bad amount a 422) instead of a 400 with a
  DBAPI message.
* :func:`retry_on_locked` — a decorator for the narrow, **idempotent** write
  paths (bulk deletes, the demo loader, startup migrations) that retries a
  transient ``database is locked`` a few times with backoff. It is deliberately
  *not* used for row inserts, where a retry could double-write.

The lock *wait* itself is handled at the connection level by
``PRAGMA busy_timeout`` (see :mod:`app.core.database`); this decorator only
covers the residual case where the timeout is exhausted under heavy contention.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from functools import wraps
from typing import TypeVar

from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.domain.errors import ConflictError, DomainError, ValidationError

T = TypeVar("T")


@contextmanager
def atomic(session: Session) -> Iterator[Session]:
    """Run a unit of work and commit it, or roll back and raise.

    Usage::

        with atomic(self._session):
            self._session.add(expense)

    On a clean exit the transaction is committed. If the body raises — or the
    commit itself fails — the session is rolled back first, so no request ever
    hands a poisoned session to the next one. A :class:`IntegrityError` is
    re-raised as the matching :class:`app.domain.errors.DomainError`; a
    ``DomainError`` the body raised on purpose passes straight through (already
    rolled back); anything else propagates unchanged.
    """
    try:
        yield session
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise _translate_integrity_error(exc) from exc
    except DomainError:
        # A rule the service enforced itself (e.g. "at least one habit").
        # Roll back the pending mutation so the in-memory object matches the
        # row, then let the original error travel to the API mapper untouched.
        session.rollback()
        raise
    except Exception:
        session.rollback()
        raise


def _translate_integrity_error(exc: IntegrityError) -> DomainError:
    """Map a database integrity failure onto a domain error.

    The DBAPI message is the only portable signal SQLite gives, so it is
    matched case-insensitively. Every branch degrades to a safe default, so an
    unrecognised constraint still becomes a clean 409 rather than a 500.
    """
    detail = str(getattr(exc, "orig", exc)).lower()

    if "unique" in detail:
        return ConflictError(_UNIQUE_MESSAGES.get(_constraint_name(detail), _UNIQUE_DEFAULT))
    if "check" in detail:
        return ValidationError(
            "That value is outside the allowed range for this field."
        )
    if "foreign key" in detail:
        return ConflictError(
            "That record refers to something that no longer exists."
        )
    if "not null" in detail:
        return ValidationError("A required field was missing.")

    # Unknown integrity failure: a collision by definition, so 409 not 500.
    return ConflictError("That change conflicts with data already stored.")


def _constraint_name(detail: str) -> str:
    """Best-effort extraction of the failing table/constraint from a message.

    SQLite phrases a unique violation as
    ``unique constraint failed: check_in.user_id, check_in.log_date`` — the
    table name is enough to give a human-readable reason.
    """
    marker = "failed:"
    if marker in detail:
        return detail.split(marker, 1)[1].strip().split(".", 1)[0].strip()
    return ""


_UNIQUE_DEFAULT = "That record already exists."
_UNIQUE_MESSAGES: dict[str, str] = {
    "check_in": "A check-in already exists for that date. Update it instead.",
    "user": "An account with that email already exists.",
}


def retry_on_locked(
    *, attempts: int = 4, base_delay: float = 0.05
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Retry an **idempotent** write when SQLite reports a transient lock.

    Only ``database is locked`` / ``database is busy`` operational errors are
    retried, with exponential backoff (``base_delay``, doubled each time).
    Every other error — including any translated :class:`DomainError` — is
    raised immediately. Wrap only operations that are safe to run twice
    (bulk deletes, migrations, the demo reload); never a single-row insert.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: object, **kwargs: object) -> T:
            delay = base_delay
            last: OperationalError | None = None
            for attempt in range(1, attempts + 1):
                try:
                    return func(*args, **kwargs)
                except OperationalError as exc:
                    if not _is_locked(exc) or attempt == attempts:
                        raise
                    last = exc
                    time.sleep(delay)
                    delay *= 2
            # Unreachable: the loop either returns or raises on the last try.
            raise last  # pragma: no cover
        return wrapper

    return decorator


def _is_locked(exc: OperationalError) -> bool:
    detail = str(getattr(exc, "orig", exc)).lower()
    return "database is locked" in detail or "database is busy" in detail
