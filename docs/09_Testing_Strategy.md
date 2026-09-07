# Testing Strategy

| Field | Value |
|---|---|
| **Document Name** | 09_Testing_Strategy.md |
| **Product** | AI Financial Intelligence Platform |
| **Version** | 1.0 |
| **Status** | 🟢 **Approved** |
| **Owner** | Engineering |
| **Dependencies** | `03_SRS.md` v1.0 · `04_System_Architecture.md` v1.0 · `07_AI_Architecture.md` v1.0 |
| **Traceability** | Every test class maps to SRS-10.*. See §9. |
| **Blocks** | Implementation sign-off |
| **Lifecycle stage** | Draft → Review → **Approved** → Frozen → Superseded |
| **Last Updated** | 2026-07-27 |

---

## Purpose

To define what is tested, how, and — most importantly — which tests are **correctness invariants** whose failure blocks release regardless of schedule.

## Scope

**In scope:** test levels, invariant tests, AI evaluation, coverage policy, CI gates, test data.

**Out of scope:** test implementation, framework configuration.

## Assumptions

**None.** Every test requirement traces to SRS §10.

## References

`03_SRS.md` §10 · `07_AI_Architecture.md` §8 · ADR-007 · ADR-009

## Related Documents

`docs/INDEX.md` · `10_Deployment.md`

---

## 1. Philosophy

Standard coverage percentages are a weak signal in this product. The failures that matter are not crashes — they are **plausible wrong answers**: a duplicated transaction inflating a total, a missing check-in read as a recorded negative, a fabricated number in generated prose. Each produces a system that runs perfectly and lies.

So the strategy has two tiers:

1. **Invariant tests** — a fixed set encoding the correctness properties that define the product. **Any failure blocks release.** No exceptions, no schedule pressure, no "known issue."
2. **Conventional tests** — unit, integration, contract, E2E. Normal engineering rigor.

## 2. Test pyramid

```
        ╱ E2E ╲              few  — critical journeys only
      ╱─────────╲
    ╱ Integration ╲          moderate — API + DB
  ╱─────────────────╲
╱    Unit (domain)    ╲      many — the analysis engine
────────────────────────
   ▓ INVARIANT TESTS ▓       ← cross-cutting, release-blocking
```

The domain layer is pure (ADR-001) — no DB, no network, no model — so the analysis engine, the statistical gates, money arithmetic, and deduplication are all fast unit tests (SRS-9.4). That is a deliberate architectural payoff.

## 3. Invariant tests ⭐

These encode the SRS §10 requirements. **Each is release-blocking.**

### INV-1 — UNKNOWN is never a Recorded Negative *(SRS-10.1, SRS-5.5, PDR-040🟠)*

**The most important test in the suite.**

Asserted at **all four layers**, because a single leak anywhere reintroduces the corruption:

| Layer | Assertion |
|---|---|
| Schema | No habit column declares a `DEFAULT`; a migration adding one fails the test |
| Domain | `HabitValue.Unknown` and `HabitValue.Recorded(false)` are not equal and are not interchangeable |
| API | Response envelope emits `{"state":"UNKNOWN"}` vs `{"state":"RECORDED","value":false}` |
| Analysis | A window with 10 unlogged days and 3 recorded-false days computes n=3, excluded=10 — **never n=13** |

**Adversarial case:** a user logs `exercise: true` on 8 days and nothing on 22 days. The engine must see 8 observations, not 30. A test asserting exactly this is the canary for the entire class of failure.

### INV-2 — No float touches money *(SRS-10.2, SRS-3.10)*

Static check across the codebase: no `float`/`Decimal` in any money-typed path; `Money` rejects float construction; schema check that no money column is a floating type.

### INV-3 — Ingestion idempotency *(SRS-10.3, SRS-10.4)*

- Re-importing an identical file creates **zero** transactions.
- Two statements overlapping by 10 days produce exactly one transaction per real transaction.
- Two genuinely distinct same-day, same-amount transactions are both preserved — the failure ADR-006 rejected alternative B for.
- Ledger totals are byte-identical before and after a duplicate import.

### INV-4 — Negative controls produce nothing *(SRS-10.5)*

Run the engine against synthetic data containing **no planted relationship**. Assert **zero T3 insights**.

This is the primary defense against the multiplicity failure ADR-007 exists to prevent, and it matters more than recall: a product that misses a real pattern disappoints; a product that invents one is finished.

### INV-5 — Planted patterns are detected *(SRS-10.6)*

Against datasets with documented planted relationships, assert the engine finds them with the expected direction and approximate magnitude. Guards against gates so strict the product says nothing.

INV-4 and INV-5 together define the operating point. Neither alone is sufficient.

### INV-6 — No causal language in T3 *(SRS-10.7, PDR-028)*

Lexical scan over generated prose **and static UI copy**. Asserts no banned connective appears in T3 content. T1 arithmetic claims are exempt (PDR-036🟠), so the test is tier-aware.

Runs against UI strings too — the causal-language ban is a product property, not a prompt property.

### INV-7 — Provenance: every number exists in the input *(SRS-10.8)*

For a corpus of structured insights, generate prose and assert every numeric literal in the output appears in the input payload. Fabrication fails the build.

### INV-8 — Advice guard blocks all seven categories *(SRS-10.9, PDR-027)*

A phrasing corpus per prohibited category — stocks, mutual funds, ETFs, insurance, loans, tax planning, investment products — including indirect phrasings ("where should I park my savings for growth?").

Also asserts **no over-blocking** on legitimate factual questions ("how much did I pay in loan EMIs last quarter?"), which ADR-010 identified as the guard's real failure mode.

### INV-9 — User isolation *(SRS-10.10, PDR-034🟠)*

For **every** data-access path: User A cannot read User B's data. Asserts a repository cannot be constructed without a user scope, and that no aggregate query spans users.

### INV-10 — Deletion is complete *(SRS-10.11, PDR-033🟠)*

After account deletion, assert zero user-attributable rows remain, **table by table** — the test enumerates tables so a newly added table without a cascade fails it.

Also: source deletion cascades to derived insights and evidence.

### INV-11 — Product works without the model *(SRS-10.12, NFR-7)*

With the LLM unavailable, assert insights are still generated, still displayed via template, and no endpoint returns 503 for insights.

### INV-12 — Determinism *(SRS-9.1)*

The same dataset with a frozen clock produces byte-identical structured claims across runs. Prose may vary; claims may not.

## 4. Unit tests

| Area | Focus |
|---|---|
| `domain/shared` | Money arithmetic, allocation, rounding policy; DateRange |
| `domain/behavior` | `HabitValue` sum type exhaustiveness |
| `domain/analysis/signals` | Aggregations against hand-computed fixtures |
| `domain/analysis/rules` | Recurring detection: true positives and near-miss negatives |
| `domain/analysis/statistics` | Each test; each gate independently; BH-FDR against published examples |
| `domain/analysis/ranking` | Ordering, cap of 5, novelty penalty |
| Normalization | Narration normalization, dedup key stability |

**Gate tests are written per-gate.** Each gate must be independently falsifiable — a suite that only tests the composite cannot tell which gate failed, and gate thresholds are the parameters most likely to be tuned.

## 5. Integration tests

- **Ingestion:** per-bank fixtures through the full pipeline to persisted ledger. One contract suite runs identically against every adapter (ADR-004).
- **Repositories:** user scoping, cascade behavior, unique constraints — including asserting the DB rejects a duplicate `dedup_key`, proving the constraint exists rather than trusting application logic.
- **API contract:** every endpoint in `06_API_Design.md` — status codes, envelope shapes, and specifically the habit two-state envelope and the money envelope.
- **Analysis run:** end-to-end from seeded data to persisted insights with evidence rows.

## 6. E2E tests

Five journeys only:

1. Land → explore demo → see insights (no account).
2. Register → consent → upload → see categorized ledger.
3. Log check-ins → run analysis → receive insight → drill to evidence.
4. New user → receive sufficiency notice → verify it is not an error state.
5. Ask a prohibited question → receive refusal.

## 7. AI evaluation

Distinct from testing: measured and tracked, not pass/fail on every run (`07_AI_Architecture.md` §8).

| Metric | Target |
|---|---|
| False positives on negative controls | **0** (also INV-4, blocking) |
| Recall on planted patterns | Tracked, high |
| Provenance validation failure rate | Tracked; rising = regression |
| Lexical validation failure rate | Tracked |
| Template fallback rate | Tracked |
| Guard precision/recall | Tracked |

Run against the SRS-3.18/3.19 synthetic corpus on every model, prompt, or threshold change.

## 8. Coverage and CI

**Coverage policy:** ≥90% on `domain/` (pure, cheap to test, and where correctness lives); ≥80% on `application/`; no numeric target on `infrastructure/` or `interface/` — behavior there is covered by integration and contract tests.

**Line coverage is a floor, not a goal.** A 95%-covered engine that fails INV-4 ships nothing.

**CI pipeline:**

```
lint → type-check (strict) → import-linter (ADR-001 boundaries)
     → unit → INVARIANT TESTS → integration → contract → E2E
     → AI evaluation (on AI-touching changes)
```

The import-linter stage enforces the dependency rule that makes PDR-031 structural. It is a build gate, not a lint warning.

**Any invariant failure fails the build. There is no override.**

## 9. Traceability

| Invariant | SRS | PDR / ADR |
|---|---|---|
| INV-1 UNKNOWN ≠ negative | SRS-10.1, 5.5 | **PDR-040🟠, ADR-007** |
| INV-2 No float money | SRS-10.2, 3.10 | ADR-003 |
| INV-3 Idempotency | SRS-10.3, 10.4 | ADR-006, PDR-045🟠 |
| INV-4 Negative controls | SRS-10.5, 3.19 | **PDR-043🟠, ADR-007** |
| INV-5 Planted patterns | SRS-10.6, 3.18 | PDR-012 |
| INV-6 No causal language | SRS-10.7 | **PDR-028**, PDR-036🟠 |
| INV-7 Provenance | SRS-10.8 | **PDR-017**, ADR-009 |
| INV-8 Advice guard | SRS-10.9 | **PDR-027**, ADR-010 |
| INV-9 User isolation | SRS-10.10 | PDR-034🟠, 035🟠, ADR-011 |
| INV-10 Deletion | SRS-10.11 | PDR-033🟠 |
| INV-11 Model-free operation | SRS-10.12 | NFR-7, ADR-009 |
| INV-12 Determinism | SRS-9.1 | PDR-031, ADR-003 |
