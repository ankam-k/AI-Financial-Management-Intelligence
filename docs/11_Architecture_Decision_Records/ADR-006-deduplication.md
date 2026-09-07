# ADR-006 — Deterministic content-hash deduplication

**Status:** Accepted · **Date:** 2026-07-27 · **Serves:** SRS-3.7, SRS-3.8, SRS-3.9, NFR-8 · **Closes:** D-14

## Decision

Each transaction carries a deterministic `dedup_key` — a hash over `(user_id, account_id, transaction_date, amount_paise, normalized_narration, running_balance)` — with a unique database constraint. Rows whose key already exists are rejected and reported, not silently dropped.

## Context

Users export overlapping date ranges routinely — a monthly statement in March and again in April will share days. SRS-3.9 requires exactly one Transaction per real-world transaction. Duplicates are uniquely dangerous here: they silently inflate every category total, every weekly aggregate, and therefore every T3 correlation, while each individual row remains perfectly traceable. PDR-045🟠 makes silent ingestion failure a zero-tolerance invariant.

## Alternatives

**A. Bank reference number.** Ideal when present. But many Indian CSV exports omit it, and formats vary, so it cannot be the primary key.

**B. `(date, amount)` pair.** Simple. Wrong: two genuine ₹120 coffee purchases on the same day collapse into one, silently *deleting* real data — a worse failure than duplication.

**C. Fuzzy matching with a similarity threshold.** Handles narration drift between exports. Rejected: non-deterministic behavior at the threshold boundary, and a false match deletes real data irrecoverably.

**D. Content hash including running balance.** Running balance is the natural disambiguator — two identical same-day transactions have different balances after each. Present in every Indian bank CSV we support.

**E. Content hash without running balance, plus an occurrence counter.** Works where balance is absent; needs stable ordering within a day, which exports do not guarantee.

## Tradeoffs

| Gain | Cost |
|---|---|
| Genuinely distinct same-day, same-amount transactions are preserved | Requires running balance in the source; degrades where absent |
| Deterministic — no threshold, no fuzzy boundary | Narration normalization must itself be deterministic and stable |
| Enforced by a DB unique constraint, not application logic | A change to the normalization rule changes all keys — a migration event |
| Re-import is naturally idempotent (SRS-3.8) | Rejected rows must be surfaced, not hidden |

## Final Choice

**D — content hash including running balance**, with fallback to **E** (hash plus intra-day occurrence index) for sources lacking a balance column.

Narration is normalized before hashing — case-folded, whitespace-collapsed, with variable UPI reference numbers stripped — so that cosmetic export differences do not defeat matching. The normalization function is versioned; changing it requires a migration that recomputes keys.

## Consequences

- A unique index on `(user_id, dedup_key)` makes duplication impossible at the storage layer, not merely unlikely.
- Import results report counts of imported, skipped-as-duplicate, and rejected rows. The user sees all three (SRS-3.6).
- Skipped duplicates are visible, not silent — silence is what NFR-8 forbids.
- The normalization function is pure, lives in `domain`, and is unit-tested against per-bank fixtures.
- Where a source lacks running balance, the fallback strategy is recorded on the import so the weaker guarantee is auditable.
