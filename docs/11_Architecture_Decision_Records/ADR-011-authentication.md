# ADR-011 — JWT bearer auth, Argon2id hashing, constructor-scoped repositories

**Status:** Accepted · **Date:** 2026-07-27 · **Serves:** SRS-8.1, SRS-8.2, PDR-034🟠, PDR-035🟠 · **Closes:** D-16

## Decision

Email/password authentication with **Argon2id** hashing. Short-lived **JWT access tokens** plus rotating refresh tokens. Data isolation is enforced by **repositories that require a `user_id` in their constructor** — there is no method to query without a user scope.

## Context

PDR-035🟠 establishes a multi-user application with strict per-user isolation. PDR-034🟠 forbids cross-user computation entirely. SRS-8.1 requires every data-access operation to be user-scoped.

The realistic threat is not an attacker — it is a developer forgetting a `WHERE user_id = ?` clause in a new query six months from now. Isolation must be structural.

## Alternatives

**Hashing — bcrypt.** Well-understood, widely deployed. 72-byte input truncation is a footgun, and it is weaker against GPU attack than memory-hard alternatives.
**Hashing — Argon2id.** Memory-hard, current best practice, no truncation surprise.

**Sessions — server-side sessions.** Trivial revocation. Requires session storage and complicates horizontal scaling later.
**Sessions — long-lived JWTs.** Simple. Revocation is effectively impossible, which is unacceptable for financial data.
**Sessions — short access JWT + rotating refresh token.** Bounded exposure, workable revocation via refresh-token invalidation.

**Isolation — filter in each query.** Standard, zero infrastructure. Relies entirely on discipline; one forgotten clause is a cross-user data leak.
**Isolation — PostgreSQL Row-Level Security.** Enforced by the database itself, strongest guarantee. But it requires per-request session variables, complicates connection pooling with async SQLAlchemy, and makes tests harder to set up.
**Isolation — constructor-scoped repositories.** The repository is constructed with a `user_id` and exposes no unscoped query method. Forgetting the scope is a construction error, not a silent leak.

## Tradeoffs

| Gain | Cost |
|---|---|
| Unscoped queries are impossible to express, not merely discouraged | Repositories must be constructed per request |
| Argon2id resists GPU attack; no input truncation | Slower and more memory-hungry than bcrypt by design |
| Short access tokens bound the exposure window | Refresh rotation adds flow complexity |
| No RLS complexity in pooling or tests | Weaker than database-enforced isolation — it is application-layer |
| Isolation testable by construction (SRS-10.10) | An admin/reporting feature would need a deliberate, reviewed exception |

## Final Choice

**Argon2id + short-lived JWT with rotating refresh + constructor-scoped repositories.**

RLS was genuinely close, and is the stronger control. It is deferred, not rejected: the scoped-repository pattern is compatible with adding RLS later as defense in depth, and PDR-002's maintainability priority favors the simpler mechanism while the application has exactly one access pattern.

## Consequences

- Repository constructors take `user_id`; no repository method accepts an arbitrary user filter.
- The DI composition root binds repositories to the authenticated user per request — an unauthenticated request cannot construct one.
- No code path can express a cross-user query, satisfying PDR-034🟠 structurally rather than by policy.
- SRS-10.10 tests every data-access path for User A → User B leakage.
- Passwords are never logged; tokens are never logged (SRS-8.9).
- Refresh-token rotation with reuse detection invalidates the family on replay.
- If an aggregate/admin view is ever required, it must be an explicit, reviewed, separately-audited exception — the friction is intentional.
