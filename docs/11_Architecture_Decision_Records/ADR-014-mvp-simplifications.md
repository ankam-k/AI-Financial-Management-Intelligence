# ADR-014 — V1 MVP simplifications: SQLite, sync ORM, no auth, no repository ports

**Status:** Accepted · **Date:** 2026-07-28 · **Serves:** PDR-002 · **Amends:** ADR-001, ADR-002, ADR-011 for V1 only

## Decision

For the V1 MVP, five decisions taken in ADR-001, ADR-002 and ADR-011 are deliberately not implemented as written:

| # | Documented | V1 | Reverts when |
|---|---|---|---|
| 1 | PostgreSQL 16 (ADR-002) | **SQLite** | Concurrency, `JSONB`, or partial indexes are needed |
| 2 | SQLAlchemy async (ADR-002) | **SQLAlchemy 2.0 sync** | A route does real concurrent I/O (LLM calls) |
| 3 | Alembic migrations (ADR-002) | **`create_all` at startup** | The first data exists that cannot be regenerated |
| 4 | JWT + Argon2id (ADR-011) | **A single local profile, no auth** | The app is served to anyone but its operator |
| 5 | Repository ports (ADR-001) | **Services take a `Session`** | A second persistence adapter is genuinely needed |

Plus one scope reduction: `transaction` (05_Database_Design.md §3.4) ships as **`expense`**, a manually-entered subset — no `raw_record` provenance link, no `dedup_key`, no `normalization_version`, no `merchant` table.

## Context

The documentation set was written for the product described in `01_Product_Vision.md` — a deployable, multi-user, statistically-gated financial intelligence platform. The V1 objective is narrower and was stated explicitly: a working AI Financial Behavior Analyzer, demoable at internship interviews, where every sprint ends in something that runs.

Those two targets disagree about cost. Docker Compose with PostgreSQL, an async engine, a migration history, password hashing, and a repository layer with one implementation are all correct for the documented product and all pure overhead for a single-user local app whose schema will change several times before it is finished. The question this ADR answers is not "which is better engineering" but "which of these buy anything during V1."

## Alternatives

**Build the documented architecture as specified.** Highest fidelity to the approved docs, and no rework later. But it front-loads roughly a sprint of infrastructure — Compose, migration scaffolding, auth flows, mappers — before a single feature is demoable, against an explicit priority that every sprint end in a working feature. It also writes migrations against a schema that is still moving.

**Simplify everything, including the invariants.** Fastest. A float column for money and `BOOLEAN NOT NULL DEFAULT FALSE` for habits would remove real code. Rejected outright: those two are not architecture, they are correctness, and both are irreversible in a way infrastructure choices are not. A float that has already rounded a rupee away cannot be un-rounded, and a `DEFAULT FALSE` that has been silently recording "didn't log" as "didn't happen" produces a dataset whose damage is invisible and permanent (ADR-007, SRS-5.5).

**Simplify the reversible layer only.** Chosen. Every item in the table above is a swap whose blast radius is one file or one dependency; none of them changes what is stored or what it means.

## Tradeoffs

| Gain | Cost |
|---|---|
| Clone → run, no Docker, no database server | SQLite's weak concurrent writes; unusable for multi-user |
| Sync ORM reads exactly like the SQL it emits | A future async LLM route needs a thread-pool bridge or an engine swap |
| Schema can change freely while it is still moving | No migration history; early schema changes mean dropping the file |
| No login screen between a demo and the feature | Everything is one profile; not deployable beyond localhost |
| Services are directly readable — no port/adapter indirection | A second persistence backend would need the seam introduced first |
| `expense` has only columns that carry meaning for typed input | CSV import will add the omitted columns back, as a migration |

The costs share a shape: each is paid **later, once, in a known place** — a URL, a dependency, a decorator, a migration. None of them compounds while unpaid, and none is discovered after the fact. That is what separates this list from the invariants below.

## Final Choice

**Simplify the reversible; preserve the irreversible.**

Preserved in full, and asserted by `tests/test_invariants.py` rather than by review:

- **Money is `BIGINT` paise.** No float in any money column, schema, or formatter (SRS-3.10, ADR-003).
- **No habit column has a `DEFAULT`, and every one is nullable.** NULL = UNKNOWN, `false`/`0` = recorded negative (SRS-5.5, ADR-007). ⭐
- **Every owned row carries `user_id` with `ON DELETE CASCADE`**, enforced by the database — which on SQLite requires `PRAGMA foreign_keys=ON` per connection (SRS-8.1, 8.6).
- **Currency is a column constrained to INR**, never a constant (SRS-3.14).
- **The clock is injected.** Nothing calls `date.today()` (ADR-003).
- **The fixed 16-member category taxonomy** (05_Database_Design.md §4).
- **Domain and service layers import no web framework.**

## Consequences

- `backend/app/core/database.py` is the only file that knows the database is SQLite. Item 1 is a URL change plus a migration pass.
- `get_current_user` in `backend/app/api/deps.py` is the single seam where authentication lands. Because every service and query is already scoped by `user_id`, item 4 changes that one dependency and adds a login route — no data-access code moves.
- No Alembic means **the schema is not yet upgradable in place.** Before the first real user data exists, a migration baseline must be generated from the current models. Tracked as an open item in `docs/INDEX.md` §8.
- `expense` will gain provenance columns when CSV import lands; the table is a subset of the documented `transaction`, not a divergent design, so that is an additive migration.
- The API is unauthenticated and binds to localhost. **It must not be exposed to a network** in this state.
