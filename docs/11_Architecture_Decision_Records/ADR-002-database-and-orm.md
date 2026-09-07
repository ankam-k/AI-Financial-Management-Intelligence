# ADR-002 — PostgreSQL 16 + SQLAlchemy 2.0 (async) + Alembic

**Status:** Accepted · **Date:** 2026-07-27 · **Serves:** PDR-003, PDR-025, SRS-9.3 · **Closes:** D-10

## Decision

PostgreSQL 16 as the database, SQLAlchemy 2.0 in async mode as the ORM, Alembic for migrations. Domain entities are hand-mapped to ORM models rather than sharing classes.

## Context

PDR-003 fixes SQLAlchemy as the ORM but leaves the engine, the async strategy, and migration tooling open. The workload is analytical over a single user's data: moderate row counts (a few thousand transactions, a few hundred check-ins per user), read-heavy analysis runs, and correctness requirements around money (SRS-3.10) and idempotency (SRS-3.7).

## Alternatives

**Engine — SQLite.** Zero-ops, trivial local dev, adequate for single-user volumes. But: no native `NUMERIC`-backed integer safety advantages over PG, weak concurrent-write behavior, no `JSONB` for `RawRecord.raw_payload`, and no partial/expression indexes — which we want for the deduplication key and for user-scoped queries. Migration to PG later would be a real project.

**Engine — MySQL.** Capable, but weaker JSON support than `JSONB` and no transactional DDL, which makes Alembic migrations riskier.

**Engine — PostgreSQL 16.** Chosen. `JSONB` for raw payload provenance (SRS-3.4), transactional DDL, partial and expression indexes, robust `BIGINT` for paise.

**Async vs sync SQLAlchemy.** Sync is simpler to reason about and debug. But FastAPI is async-native (PDR-003); mixing sync ORM into async routes means thread-pool offloading for every request, which is a persistent source of subtle bugs and connection-pool exhaustion. Async 2.0 style is now mature.

**Shared ORM/domain classes vs hand mapping.** Sharing is far less code. But it drags `sqlalchemy` into `domain`, violating ADR-001 and defeating the structural guarantee behind PDR-031.

## Tradeoffs

| Gain | Cost |
|---|---|
| `JSONB` preserves raw source rows for provenance (PDR-017) | Requires a running PG in dev; Docker Compose dependency |
| Transactional DDL makes migrations safe to roll back | Alembic autogenerate is unreliable with hand-mapped entities — migrations are reviewed by hand |
| Async end-to-end, no thread-pool bridging | Async SQLAlchemy has sharper edges (lazy loading must be explicit) |
| Domain stays framework-free | Duplicate entity/model definitions and a mapping layer to maintain |

## Final Choice

**PostgreSQL 16 + SQLAlchemy 2.0 async + Alembic, with hand-written domain↔ORM mapping.**

The hand-mapping cost is accepted deliberately: it is the price of ADR-001's guarantee, and PDR-002 names maintainability as the tiebreaker over convenience.

## Consequences

- Docker Compose must provide PostgreSQL for local development (ADR-013).
- Lazy loading is disabled; all relationship loading is explicit (`selectinload`), preventing N+1 surprises in analysis runs.
- Alembic migrations are written and reviewed manually; autogenerate is used only as a starting draft.
- A `persistence/mappers/` module owns all domain↔ORM translation and is unit-tested independently.
- `JSONB` raw payloads make SRS-3.4 provenance cheap and queryable.
