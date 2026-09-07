# ADR-004 — Per-bank adapters with a generic column-mapping fallback

**Status:** Accepted · **Date:** 2026-07-27 · **Serves:** PDR-013, SRS-3.1, SRS-3.2, SRS-9.5 · **Closes:** D-12

## Decision

Ship dedicated CSV adapters for **HDFC, ICICI, SBI and Axis**, plus a **GenericCsvAdapter** where the user maps columns once for an unrecognized format. All implement `StatementSourcePort` and emit only `RawRecord`. Format detection is by header fingerprint, with explicit user override.

## Context

PDR-013 requires ingestion behind a port so a V2 Account Aggregator integration changes nothing downstream. PDR-010 approves CSV. The practical problem is that Indian bank CSV exports share no standard: column names, date formats, debit/credit conventions (separate columns vs. signed amount), and narration structure all differ, and banks change them without notice.

The failure mode that matters most is not "we don't support bank X" — it is a user hitting a wall on first upload and never returning (PRD §3 acceptance criteria).

## Alternatives

**A. One universal parser with heuristics.** No per-bank code. But heuristic sign detection is exactly where silent corruption enters — misreading a credit as a debit produces a plausible ledger that is wrong, violating SRS-3.5's spirit and NFR-8's zero-silent-failure invariant.

**B. Per-bank adapters only.** Highest fidelity per supported bank. But an unsupported bank is a hard wall, and there are dozens of Indian banks.

**C. Generic mapping only.** Universal coverage; every user does setup work. Poor first-run experience for the majority who use the top four banks.

**D. Per-bank adapters + generic fallback.** Best-effort automatic for common banks, graceful degradation otherwise.

**E. LLM-based parsing.** Tempting and flexible. Rejected firmly: it puts a non-deterministic component in the ingestion path, violating SRS-9.1 and PDR-031's principle that the model is never the source of truth. Parsing is where determinism matters most.

## Tradeoffs

| Gain | Cost |
|---|---|
| Common banks work with zero configuration | Four adapters to maintain against format drift |
| No user is ever hard-blocked (generic fallback) | Generic path needs a column-mapping UI |
| Deterministic parsing — no model in the ingestion path | Header fingerprints must be updated when banks change exports |
| Adapters isolated; format drift affects one file | Requires per-bank sample fixtures in the test suite |

## Final Choice

**D — four per-bank adapters plus a generic column-mapping fallback.**

Detection is by header fingerprint. Where a fingerprint is ambiguous or unknown, the user is shown the detected columns and asked to confirm the mapping — never silently guessed. Saved mappings are reusable per user.

## Consequences

- `RawRecord` carries `(source_id, row_number, raw_payload JSONB, extracted_fields)` and no bank-specific structure. Nothing downstream can identify the originating adapter (verified by SRS-9.5 test).
- Each adapter ships with anonymized sample fixtures; a contract test suite runs identically against every adapter.
- A format-drift failure produces an explicit unparseable error naming the row and column (SRS-3.6) — never a partial import.
- The generic adapter's saved mappings are per-user data and fall under PDR-033🟠 deletion.
- Adding a bank is a new adapter file plus fixtures. Adding Account Aggregator in V2 is a new adapter implementing the same port.
