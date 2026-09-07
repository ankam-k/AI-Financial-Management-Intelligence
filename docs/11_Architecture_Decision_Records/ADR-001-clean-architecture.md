# ADR-001 — Clean Architecture with ports and adapters

**Status:** Accepted · **Date:** 2026-07-27 · **Serves:** PDR-002, PDR-004, PDR-013, PDR-031

## Decision

Four layers — Interface, Application, Domain, Infrastructure — with dependencies pointing strictly inward. The Domain layer depends on nothing. Boundaries are enforced by an import-linter contract in CI, not by review discipline.

## Context

`CLAUDE.md` mandates Clean Architecture and SOLID (PDR-004). But the decisive requirement is PDR-031: *the analysis engine is the source of truth, and the LLM must not fabricate results.* We need that to be a structural guarantee, not a rule someone can forget.

We also need PDR-013's ingestion abstraction to survive contact with a V2 Account Aggregator integration, which is exactly the point at which most layering discipline collapses.

## Alternatives

**A. Layered MVC (routers → services → models).** Familiar, fast to start, minimal ceremony. But service layers in this style routinely acquire ORM session access, and once the analysis code can reach a session it can reach anything — including, eventually, an LLM client. Nothing structural prevents PDR-031 from being violated.

**B. Modular monolith by feature slice.** Good cohesion, easy to navigate. But feature slices tend to duplicate the analysis engine's concerns across ingestion, insight and Q&A slices, and traceability (PDR-017) needs one authoritative evidence model, not three.

**C. Clean Architecture with enforced boundaries.** More ceremony up front. Some indirection that looks gratuitous in the first month.

**D. Hexagonal with full CQRS + event sourcing.** Excellent auditability — genuinely attractive given PDR-017. But event sourcing for a single-user-scoped analytical workload is a large complexity bill against PDR-002's maintainability priority.

## Tradeoffs

| Gain | Cost |
|---|---|
| Domain cannot import `sqlalchemy`, `fastapi`, or the LLM client — PDR-031 becomes structurally true | More files; a use case touches 3–4 layers |
| Analysis engine unit-testable with no DB, no network, no model (SRS-9.4) | Port/adapter indirection can feel like overhead at small scale |
| Ingestion sources swappable without downstream change (PDR-013) | Mapping between domain entities and ORM models is hand-written |
| Determinism (SRS-9.1) follows from purity rather than being tested for | Newcomers need orientation |

## Final Choice

**C — Clean Architecture with CI-enforced boundaries.** Rejected D as over-engineering for V1 (PDR-004 explicitly warns against unnecessary abstraction); rejected A and B because neither makes PDR-031 structurally unviolatable, and that requirement is the product's core promise.

## Consequences

- `domain/` has zero third-party imports beyond the standard library.
- The analysis engine is *incapable* of calling the LLM, because it cannot perform I/O.
- CI fails on any inward-dependency violation.
- Adding an ingestion source means implementing `StatementSourcePort` and registering it — nothing else changes (verified by SRS-9.5).
- Hand-written domain↔ORM mapping is accepted maintenance cost.
- If CQRS is ever needed, it can be added inside Application without disturbing Domain.
