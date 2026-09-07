"""Database engine and session lifecycle.

SQLite for V1 (ADR-014). SQLite is a real database, but its safe defaults are
conservative — several correctness and concurrency properties this app depends
on are *off* until a ``PRAGMA`` turns them on, once per connection. They are set
here rather than trusted, on every connection the pool hands out:

1. **Foreign keys are OFF by default.** Without ``foreign_keys=ON`` every
   ``ON DELETE CASCADE`` in the schema is silently inert and deleting a profile
   would leave orphaned expenses behind — cascade is a correctness property
   (05_Database_Design.md §8), not a hint.

2. **Rollback journalling serialises readers against a writer.** ``journal_mode
   =WAL`` lets reads run concurrently with a single writer, which keeps the
   dashboard's several parallel queries from blocking each other and the
   writer. Paired with ``synchronous=NORMAL`` — durable under WAL and markedly
   faster than ``FULL``.

3. **A busy database errors instantly by default.** ``busy_timeout`` makes a
   connection *wait* for a lock (up to five seconds) instead of raising
   ``database is locked`` the moment it sees contention. This is the primary
   lock-handling mechanism; :func:`app.core.unit_of_work.retry_on_locked` only
   covers the residual case where even that wait is exhausted.

4. **In-memory databases need ``StaticPool``.** Each new connection to
   ``sqlite://`` gets its own blank database; pooling one connection is what
   makes an in-memory test database usable across requests. WAL and the
   file-only tunings are skipped there — there is no file, and one shared
   connection has nothing to serialise against.
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings

#: How long a connection waits for a lock before giving up, in milliseconds.
#: Matched by the application-level retry budget in ``unit_of_work``.
_BUSY_TIMEOUT_MS = 5_000


def _is_sqlite(url: str) -> bool:
    return url.startswith("sqlite")


def _is_memory_sqlite(url: str) -> bool:
    return _is_sqlite(url) and (":memory:" in url or url in {"sqlite://", "sqlite:///"})


def build_engine(url: str, *, echo: bool = False) -> Engine:
    """Create an engine configured for the given URL."""
    kwargs: dict[str, object] = {
        "echo": echo,
        "future": True,
        # Verify a pooled connection is still alive before handing it out,
        # rather than letting a stale one surface as an error mid-request.
        "pool_pre_ping": True,
    }

    memory = _is_memory_sqlite(url)

    if _is_sqlite(url):
        # FastAPI serves sync endpoints from a thread pool, so a connection
        # can legitimately be used from a thread other than the one that
        # created it. SQLAlchemy's pool still serialises access.
        kwargs["connect_args"] = {"check_same_thread": False}
        if memory:
            kwargs["poolclass"] = StaticPool

    engine = create_engine(url, **kwargs)

    if _is_sqlite(url):
        # A closure so the listener knows whether WAL applies (file only).
        @event.listens_for(engine, "connect")
        def _configure_sqlite(dbapi_connection, _record):  # noqa: ANN001, ANN202
            _apply_sqlite_pragmas(dbapi_connection, memory=memory)

    return engine


def _apply_sqlite_pragmas(dbapi_connection, *, memory: bool) -> None:  # noqa: ANN001
    """Bring one SQLite connection up to the app's required settings.

    ``foreign_keys`` and ``busy_timeout`` apply to every connection; WAL and
    its companions are meaningful only for an on-disk database.
    """
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute(f"PRAGMA busy_timeout={_BUSY_TIMEOUT_MS}")
        if not memory:
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA temp_store=MEMORY")
    finally:
        cursor.close()


engine = build_engine(settings.database_url, echo=settings.database_echo)

SessionFactory = sessionmaker(
    bind=engine,
    autoflush=False,
    # Responses are serialised after commit; without this every attribute
    # access would trigger a refresh query against a closed session.
    expire_on_commit=False,
)


def get_session() -> Iterator[Session]:
    """FastAPI dependency yielding a request-scoped session.

    Tests override this to bind a per-test engine.
    """
    with SessionFactory() as session:
        yield session
