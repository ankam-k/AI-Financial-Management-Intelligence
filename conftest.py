"""Shared test fixtures.

Each test gets its own in-memory SQLite database and a **frozen clock**. The
frozen clock is not a nicety: the check-in backfill window is defined relative
to "today", so a test asserting the boundary would otherwise pass all day and
fail at midnight.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from datetime import date, datetime, timedelta

import pytest

# Point the application at an in-memory database *before* importing it, so
# module-level engine construction and the startup `create_all` never touch a
# file on disk.
os.environ.setdefault("AFI_DATABASE_URL", "sqlite://")

# A deterministic signing secret for the suite, set before the app imports so
# `resolve_auth_secret` returns it instead of the dev fallback (no warning
# noise, and tokens are reproducible). Never a real secret — tests only.
os.environ.setdefault("AFI_AUTH_SECRET", "test-signing-secret-deterministic")

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402

from app.api.deps import get_clock  # noqa: E402
from app.core.clock import IST, FixedClock  # noqa: E402
from app.core.database import build_engine, get_session  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402

#: The instant every test runs at. A Tuesday, so weekday-sensitive assertions
#: added later have a stable reference.
FROZEN_NOW = datetime(2026, 7, 28, 10, 30, tzinfo=IST)
TODAY: date = FROZEN_NOW.date()


@pytest.fixture
def clock() -> FixedClock:
    """A clock frozen at :data:`FROZEN_NOW`."""
    return FixedClock(FROZEN_NOW)


@pytest.fixture
def today() -> date:
    """The frozen clock's date. Exposed as a fixture rather than imported,
    because a conftest is not reliably importable as a module."""
    return TODAY


@pytest.fixture
def days_ago() -> Callable[[int], str]:
    """Return an ISO date N days before the frozen today."""

    def _days_ago(n: int) -> str:
        return (TODAY - timedelta(days=n)).isoformat()

    return _days_ago


@pytest.fixture
def session_factory() -> Iterator[sessionmaker[Session]]:
    """A fresh in-memory database with the full schema, per test."""
    engine = build_engine("sqlite://")
    Base.metadata.create_all(bind=engine)
    yield sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def db(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    """A session against the per-test database, for direct assertions."""
    with session_factory() as session:
        yield session


#: A clearly test-only password shared by the fixture users. Never a real or
#: production secret; it exists only to drive the real register/login flow.
TEST_PASSWORD = "test-password-not-a-secret"


def register_user(tc: TestClient, email: str, display_name: str) -> str:
    """Register (and thereby log in) a user through the real HTTP flow.

    Returns the new account's id. Asserts success so a fixture failure is
    obvious rather than surfacing as a confusing 401 later.
    """
    response = tc.post(
        "/api/auth/register",
        json={"email": email, "password": TEST_PASSWORD, "display_name": display_name},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


@pytest.fixture
def anon_client(
    session_factory: sessionmaker[Session], clock: FixedClock
) -> Iterator[TestClient]:
    """An **unauthenticated** API client on the per-test database and frozen clock.

    Every test gets its own in-memory database (``session_factory``), so users
    and data never leak between tests. Use this for the auth flow itself; for
    ordinary endpoints use :func:`client`, which is already signed in.
    """

    def override_session() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_clock] = lambda: clock

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def client(anon_client: TestClient) -> TestClient:
    """An API client **authenticated as the default test user** (User A).

    Registration happens through the real ``/api/auth/register`` endpoint and
    the session cookie is retained by the client, so every existing route test
    now exercises the genuine authenticated path with no per-test change. The
    display name is "Local User" to match the pre-auth default.
    """
    register_user(anon_client, "user-a@afi.test", "Local User")
    return anon_client


@pytest.fixture
def second_client(client: TestClient) -> TestClient:
    """A second client **authenticated as User B**, sharing User A's database.

    This is the vehicle for cross-user isolation tests: User B is a distinct
    account in the same store, so a request from here must never see or touch
    User A's rows.
    """
    other = TestClient(app)  # shares the app's per-test session override
    register_user(other, "user-b@afi.test", "User B")
    return other


@pytest.fixture
def profile_id(client: TestClient) -> str:
    """The authenticated user's profile id."""
    return client.get("/api/profile").json()["id"]
