"""Application entry point.

Run with::

    uvicorn app.main:app --reload --app-dir backend

Interactive API docs: http://127.0.0.1:8000/docs
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.errors import register_error_handlers
from app.api.routes import (
    auth,
    chat,
    check_ins,
    demo,
    expenses,
    insights,
    life_events,
    narrations,
    profile,
)
from app.core.config import settings
from app.core.database import engine
from app.core.migrations import run_migrations
from app.models import Base  # noqa: F401 — imports every model into the metadata

DESCRIPTION = """
Sprint 1 of the AI Financial Intelligence Platform.

Records the three streams the analysis engine will later correlate:
**expenses**, daily **habit check-ins**, and **life events**.

Two conventions worth knowing before you call anything:

* **Money is integer paise.** ₹120.50 is sent as `12050`. No float touches an
  amount at any point.
* **A missing habit means UNKNOWN, never "it didn't happen."** Omit a field to
  say you don't know; send `false` or `0` to record that it did not occur.
"""


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Bring the schema up to date on startup.

    Two steps, in order:

    1. ``create_all`` — creates any *missing tables*. On a fresh database this
       produces the whole current schema; on an existing one it is a no-op for
       tables that already exist. Alembic is still deferred (ADR-014): with
       SQLite a full migration history would be churn.
    2. ``run_migrations`` — applies the additive, idempotent column/index steps
       that ``create_all`` cannot, because it never alters an existing table
       (``app.core.migrations``). This is what carries a pre-V1.2 database onto
       the V1.2 auth schema without dropping anything.
    """
    Base.metadata.create_all(bind=engine)
    run_migrations(engine)
    yield


app = FastAPI(
    title=settings.app_name,
    version=__version__,
    description=DESCRIPTION,
    lifespan=lifespan,
)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

register_error_handlers(app)

app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(expenses.router)
app.include_router(check_ins.router)
app.include_router(life_events.router)
app.include_router(insights.router)
app.include_router(narrations.router)
app.include_router(chat.router)
app.include_router(demo.router)


@app.get("/health", tags=["meta"], summary="Liveness probe")
def health() -> dict[str, str]:
    """Return service status. Used by the Compose healthcheck in a later sprint."""
    return {"status": "ok", "version": __version__}
