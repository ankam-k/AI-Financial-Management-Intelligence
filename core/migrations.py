"""Lightweight, idempotent startup migrations.

V1 creates the schema with ``Base.metadata.create_all`` (ADR-014), which has a
sharp limitation: it creates *missing tables* but never alters an *existing*
one. So when V1.2 adds columns to a table that a pre-V1.2 database already has
(``user`` gains ``email``, ``password_hash``, ``is_demo``), ``create_all`` is
silent and those columns never appear.

This module fills exactly that gap and nothing more. It is **not** a migration
framework — Alembic is still deferred (ADR-014, ADR-011). It is a hand-audited
list of additive, idempotent steps run once at startup, after ``create_all``:

* **Idempotent** — every step checks the live schema first and skips if already
  applied, so repeated startups are safe.
* **Non-destructive** — it only ever ``ADD``s a column or ``CREATE``s an index.
  It never drops or rewrites a table, and it never uses ``drop_all``.
* **Explicit** — each change is spelled out here, not inferred from a model
  diff. A reviewer can read exactly what will run.

If a future change cannot be expressed as a safe additive step (a column that
must be NOT NULL with no default over existing rows, a type change, a rename),
that is the signal to adopt Alembic — not to improvise a destructive step here.
"""

from __future__ import annotations

import logging

from sqlalchemy import Engine, inspect, text

_log = logging.getLogger("app.migrations")

#: Additive column steps: (table, column, DDL type + default clause).
#: Each is applied only if the column is absent. The type/default must be a
#: valid tail for ``ALTER TABLE <t> ADD COLUMN <c> <ddl>`` under SQLite, whose
#: one rule for us is: a NOT NULL column must carry a DEFAULT.
_ADD_COLUMNS: tuple[tuple[str, str, str], ...] = (
    # V1.2 auth (M2): identity on the profile row.
    ("user", "email", "VARCHAR(255)"),
    ("user", "password_hash", "VARCHAR(255)"),
    ("user", "is_demo", "BOOLEAN NOT NULL DEFAULT 0"),
    # V1.2 onboarding & personalisation (M5): all additive and defaulted, so a
    # pre-V1.2 row upgrades to "not yet onboarded, nothing selected" without any
    # rewrite. The JSON columns take a constant '[]' default — SQLite requires a
    # NOT NULL added column to carry one — matching the model's server_default,
    # so a fresh (create_all) row and a migrated row are identical.
    ("user", "onboarding_completed", "BOOLEAN NOT NULL DEFAULT 0"),
    ("user", "life_stage", "VARCHAR(32)"),
    ("user", "income_pattern", "VARCHAR(32)"),
    ("user", "work_context", "VARCHAR(32)"),
    ("user", "household_context", "VARCHAR(32)"),
    ("user", "focus_areas", "JSON NOT NULL DEFAULT '[]'"),
    ("user", "tracked_categories", "JSON NOT NULL DEFAULT '[]'"),
    ("user", "tracked_habits", "JSON NOT NULL DEFAULT '[]'"),
)

#: Index steps: (table, name, CREATE statement). Applied only if the index is
#: absent. ``IF NOT EXISTS`` makes each doubly safe; the presence check keeps
#: the log honest about what actually changed.
_CREATE_INDEXES: tuple[tuple[str, str, str], ...] = (
    (
        "user",
        "uq_user_email",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_user_email "
        "ON user (email) WHERE email IS NOT NULL",
    ),
)


def run_migrations(engine: Engine) -> list[str]:
    """Apply pending additive migrations. Returns the steps actually run.

    An empty list means the database was already current — the normal case on
    every startup after the first. Safe to call repeatedly and safe on a fresh
    database, where ``create_all`` has already produced the final schema and
    every step is a no-op.
    """
    applied: list[str] = []
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    with engine.begin() as connection:
        for table, column, ddl in _ADD_COLUMNS:
            if table not in tables:
                # The table itself doesn't exist yet (e.g. a brand-new column
                # step for a table create_all hasn't made). Nothing to alter.
                continue
            existing = {col["name"] for col in inspector.get_columns(table)}
            if column in existing:
                continue
            connection.execute(text(f'ALTER TABLE "{table}" ADD COLUMN {column} {ddl}'))
            step = f"add {table}.{column}"
            applied.append(step)
            _log.info("migration applied: %s", step)

        # Re-inspect: an index may depend on a column just added above.
        inspector = inspect(engine)
        for table, name, statement in _CREATE_INDEXES:
            if table not in tables:
                continue
            existing = {idx["name"] for idx in inspector.get_indexes(table)}
            if name in existing:
                continue
            connection.execute(text(statement))
            applied.append(f"create index {name}")
            _log.info("migration applied: create index %s", name)

    return applied
