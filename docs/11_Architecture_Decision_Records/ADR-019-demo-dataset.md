# ADR-019 — Demo V1: planted patterns below the API, validated by the real engine

**Status:** Accepted · **Date:** 2026-07-28 · **Serves:** PDR-012, SRS-3.18, SRS-3.19, SRS-9.1 · **Closes:** OEQ-004 · **Implements:** `07_AI_Architecture.md` §8

## Decision

Four decisions taken while building the demo dataset (Sprint 6):

| # | Decision |
|---|---|
| 1 | The dataset is written **below the API**, not through it. |
| 2 | Patterns are **planted deliberately** and declared before they are generated. |
| 3 | The dataset carries **negative controls**, and zero false positives on them is the primary bar. |
| 4 | Validation runs the **real analysis engine**, and fails a build if the demo stops demonstrating. |

## Context

OEQ-004 recorded a conflict between two approved requirements: check-in backfill is capped at 30 days (SRS-5.6/5.7), while a behavioural association needs ≥ 8 complete weeks at ≥ 60% per-habit coverage (gates G1, G3). The consequence was measured rather than predicted — seeding sixteen weeks through the public API produced eleven descriptive insights and **zero correlational ones**.

That is not a bug. You cannot have behavioural history you did not record, and insight taking weeks to earn is the design (PDR-030). The narrow problem was that **there was no path to a T3 insight at all** — not for a new user, and not for anyone demonstrating the product whose README leads with exactly that finding.

## Alternatives

**1. Where to write.** Three options were recorded in OEQ-004.

*Relax the backfill window* is the cheapest and weakens a rule that exists because week-old self-reports are unreliable — it would trade a correctness property for a demo.

*Lower gate G3 for a first window* was rejected on sight: a gate that relaxes when it fails is not a gate.

*Write below the API* was chosen. The backfill cap lives in `CheckInService` because it is a rule about **user input**, and a synthetic dataset is not user input. Writing through the ORM bypasses the transport, not the schema — cascade, uniqueness and every CHECK constraint apply unchanged, and a test asserts the loaded check-ins reach further back than 30 days while the service still refuses a real one.

**2. Planted versus emergent patterns.** Generating plausible noise and reporting whatever the engine finds would be less work and would prove nothing: a finding nobody planted cannot be distinguished from a false positive. Declaring the patterns in `design.py` first means the validation test asserts against a *specification* rather than against whatever the generator happened to do.

**3. Weekly budgets versus per-transaction effects.** The unit of observation is the ISO week. Planting an effect per transaction and hoping it survives aggregation is how a synthetic dataset ends up not demonstrating the thing it was built for. Weekly totals are set first, then split into transactions that sum to them exactly.

**4. Negative controls.** They could have been omitted — the dataset would be simpler and every habit would show a finding. That is precisely the failure: a generator that manufactures a pattern everywhere proves the engine detects noise. `07_AI_Architecture.md` §8 names zero T3 insights on negative controls as the primary metric, **ahead of recall on planted ones**, and this ADR adopts that ordering.

They are also *recorded on every logged day*. An all-null control would pass vacuously — excluded for coverage rather than found empty.

## Tradeoffs

| Gain | Cost |
|---|---|
| A T3 insight is reachable; the product demonstrates its own headline claim | A second write path into the database exists, gated by `AFI_DEMO_MODE` |
| Patterns are checkable against a declared design | `design.py` and the generator must stay in step; the tests enforce it |
| False positives would fail a build | The validation suite runs the whole engine, so it is slower than a unit test |
| Determinism keeps screenshots and README figures true | Changing the seed changes every published number |
| Backfill rule intact for real input | Demo data does not exercise the API's own validation path |

## Final Choice

**Declare, generate, then check with the real engine.**

`python -m app.demo validate` generates the dataset, analyses it with `app/analysis/`, and reports per pattern whether it survived all five gates and whether either control produced a finding. It exits non-zero if not. The same checks run in `tests/demo/test_validation.py`, so a change to the generator, the gates, or the statistics that broke the demonstration fails a build rather than being discovered in an interview.

Two design defects were caught this way and are recorded because they are the kind that hide:

- **Phase anchoring.** Tiling habit phases forward from the start of the window left ~5 exercise weeks in the default 90-day view against gate G2's ≥ 6. The headline pattern silently vanished from the page the dashboard opens on. Phases are now anchored to the *end* of the window.
- **Degenerate weekly series.** Both utility bills fell in the same week of each month, so `UTILITIES` was zero for three weeks in four. Any split of a mostly-zero series produces a huge apparent effect, and the engine duly reported a `home_cooked_meals ↔ UTILITIES` association at a relative difference of 1.0 — arithmetically correct and entirely an artefact of the billing calendar. Billing days are now spread across the month. **The fix was to the data, not the engine.**

## Consequences

- **OEQ-004 is closed.** Five T3 insights are reachable through `GET /api/insights` on the demo dataset.
- **The demo endpoints are destructive and gated.** `AFI_DEMO_MODE` defaults to on because V1 is a single local profile with no authentication and no network exposure (ADR-014). It is the first thing to turn off if either changes.
- **Changing `DEMO_SEED` invalidates every published figure** — screenshots, the README, this document. It is fixed for that reason.
- **The dataset produces no `DATA_SUFFICIENCY` notices**, deliberately: it is sufficient, so a notice would mean a gate failed. The honest empty state is demonstrated on a short window (`?days=14`) instead.
- **`datasets/` remains empty.** The dataset is generator output, not a committed fixture — which is the reading `.gitignore` declined to assert. A generator is smaller than its output, reviewable as code, and cannot drift from the schema without failing a test.
