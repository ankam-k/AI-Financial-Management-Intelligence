# Demo & Release

| Field | Value |
|---|---|
| **Document Name** | 13_Demo_And_Release.md |
| **Product** | AI Financial Intelligence Platform |
| **Version** | 1.0 |
| **Status** | 🟢 **Approved** |
| **Owner** | Engineering |
| **Dependencies** | `07_AI_Architecture.md` §8 · ADR-013, ADR-019 · OEQ-004 |
| **Traceability** | §6 |
| **Blocks** | Nothing |
| **Last Updated** | 2026-07-28 |

---

## Purpose

To make the product demonstrable and deployable: a deterministic dataset that
exercises every analytic the system supports, the commands that load it, and
the release checklist that says whether it is ready to show.

## Scope

**In scope:** dataset design, demo commands, Docker stack, environment
configuration, validation, release checklist.

**Out of scope:** new product capability. Nothing in this sprint adds a
feature; it makes the existing ones visible.

---

## 1. Why this exists — OEQ-004

Two approved requirements disagreed with each other, and the disagreement made
the product's headline feature impossible to see:

- **SRS-5.6/5.7** cap check-in backfill at **30 days**.
- **Gates G1 and G3** need **≥ 8 complete weeks** of history at **≥ 60%
  per-habit coverage**.

A new user can therefore log at most ~4.3 weeks retroactively, capping coverage
over an eight-week window near 54% — below the floor before data quality enters
into it. Measured, not predicted: seeding 16 weeks through the public API
produced **11 descriptive insights and zero correlational ones**.

The engine was behaving exactly as specified. The specification disagreed with
itself.

**The fix writes below the API rather than relaxing the rule.** The backfill
cap lives in `CheckInService` because it is a rule about *user input*; a
synthetic dataset is not user input. `app/demo/loader.py` writes through the
ORM, so every schema invariant — cascade, uniqueness, the CHECK constraints —
applies exactly as always. The rule stays intact for a real check-in.

This was already V1 scope: `datasets/`, `data_source.is_synthetic` and PDR-012
all anticipated it.

**Result:** five T3 correlational insights are now reachable through
`GET /api/insights`, where before there were none.

---

## 2. Dataset design

### Persona

Pranay, 26, a software engineer in Bengaluru — the `01_Product_Vision.md`
persona. ₹82,000 monthly budget against typical months of ₹67,000–79,000, so
the current month lands just over and the budget card has something to say.
Nine months of history, UPI-dominant, rent and subscriptions on fixed days.

### Planted patterns

Declared in `app/demo/design.py`, and asserted by tests that run the **real
analysis engine**:

| Habit | Category | Test | Shape |
|---|---|---|---|
| `exercise` | `FOOD_DINING` | Mann–Whitney U | weeks without the gym cost more |
| `sleep_minutes` | `TRANSPORT` | Spearman ρ | less sleep, more cabs |
| `home_cooked_meals` | `FOOD_DINING` | Spearman ρ | more cooking, less takeaway |

Effects are planted as **weekly budgets**, not per-transaction noise, because
the unit of observation is the ISO week. Planting at the transaction level and
hoping the signal survives aggregation is how a synthetic dataset ends up not
demonstrating the thing it was built for.

Habits move in **six-week phases anchored to the end of the window** — a person
has a good month and a bad month; they do not alternate weekly. The anchoring
is load-bearing: the first draft tiled phases *forward* from the start, which
left ~5 exercise weeks in the default 90-day window against gate G2's
requirement of ≥ 6 in each group. The product's headline pattern silently
failed to appear in the view the dashboard opens on.

### Negative controls

`alcohol` and `work_mode` are generated independently of every category, and
**recorded on every logged day** — an all-null control would pass vacuously,
excluded for coverage rather than found empty.

Per `07_AI_Architecture.md` §8 the primary metric is **zero T3 insights on
negative controls**, ahead of recall on planted ones. A generator that
manufactured a pattern everywhere would prove the engine detects noise, which
is the opposite of the claim the product makes.

### What the dataset does not contain

**No `DATA_SUFFICIENCY` notices.** The data is deliberately sufficient, so a
notice would mean a gate failed. The honest empty state is demonstrable on a
short window instead: `GET /api/insights?days=14`.

---

## 3. Demo commands

```bash
python -m app.demo seed       # load the dataset, replacing what is there
python -m app.demo reset      # the same thing, said out loud
python -m app.demo clear      # remove every record, keep the profile
python -m app.demo status     # what is currently loaded
python -m app.demo validate   # run the engine, check the planted patterns
```

`validate` is the interesting one. It generates, analyses with the real engine,
and exits non-zero if a planted pattern failed a gate or a negative control
produced a finding — so *"the demo still demonstrates what it claims"* is a
check you run, not a belief you hold.

The same three operations are on the API (`POST /api/demo/seed`,
`DELETE /api/demo`, `GET /api/demo/status`) and behind the **Load demo data**
button on the dashboard's empty state, so a demo does not need a terminal
mid-interview. They are gated by `AFI_DEMO_MODE`, which must be turned off the
moment the API is exposed to anything but localhost.

`GET /api/demo/design` publishes the planted patterns and negative controls, so
a reviewer can check that the associations on screen are the ones the generator
set out to create rather than taking it on trust.

---

## 4. Architecture

```
                    ┌──────────────────────────────────────────┐
   browser  ───────▶│  web (nginx)   static bundle + /api proxy │
                    └───────────────────┬──────────────────────┘
                                        │  one origin, so no CORS
                                        ▼
   ╔════════════════════════════════════════════════════════════════════╗
   ║  api (FastAPI)                                                     ║
   ║                                                                    ║
   ║   api/routes ──▶ services ──▶ models ──▶ SQLite (volume)           ║
   ║       │              │                                             ║
   ║       │              ├──▶ analysis/    ⭐ no I/O, no framework      ║
   ║       │              │      dataset → gates → Insight              ║
   ║       │              │                                             ║
   ║       │              ├──▶ narration/   ⭐ no I/O, no adapter        ║
   ║       │              │      Insight → prompt → validators → prose  ║
   ║       │              │                                             ║
   ║       │              └──▶ chat/        ⭐ guard runs first          ║
   ║       │                     question → guard → intent → context    ║
   ║       ▼                                                            ║
   ║     llm/  ◀── the only network I/O ──────────────────────┐         ║
   ╚═══════════════════════════════════════════════════════════│════════╝
                                                               ▼
                                              ┌────────────────────────┐
                                              │ ollama (optional)      │
                                              │ qwen2.5:7b-instruct    │
                                              └────────────────────────┘
```

Three boundaries are enforced by a test that parses the import graph
(`tests/analysis/test_purity.py`), not by review:

- `analysis/` imports no database driver, no web framework, no HTTP client.
- `narration/` imports no adapter — only the `LLMClient` protocol.
- Neither can reach a database, which is the structural form of *"the LLM never
  queries the database directly"*.

### The data path

```
expenses + check-ins + events
        │
        ▼  app/analysis/          exact arithmetic, five gates, BH-FDR
   Insight objects                 every number fixed here
        │
        ├─▶ app/narration/        template first; a generation must pass
        │     three validators to be used, and is discarded whole if not
        │
        ├─▶ app/chat/             guard → intent → minimum context → answer
        │
        └─▶ frontend/             renders; computes nothing
```

---

## 5. Release checklist

| # | Item | State |
|---|---|---|
| 1 | Backend suite green | ✅ 746 tests |
| 2 | Frontend suite green | ✅ 109 tests |
| 3 | Typecheck clean (`tsc -b --noEmit`) | ✅ |
| 4 | Production bundle builds | ✅ 182 KB / 59 KB gzipped |
| 5 | Runs from a clean checkout with no model installed | ✅ |
| 6 | Demo dataset validates (patterns + controls) | ✅ `python -m app.demo validate` |
| 7 | Every insight type demonstrable from the demo data | ✅ 14 of 14 (see §2) |
| 8 | T3 correlational insight reachable through the API | ✅ closes OEQ-004 |
| 9 | Docker Compose stack defined | ✅ `docker/docker-compose.yml` |
| 10 | Environment documented with working defaults | ✅ `.env.example` |
| 11 | API documented | ✅ OpenAPI at `/docs`; endpoint table in `backend/README.md` |
| 12 | Screenshots current | ✅ `docs/screenshots/` |
| 13 | Architecture diagram | ✅ §4 |
| 14 | Setup instructions | ✅ root `README.md` |
| 15 | ADRs recorded for every architectural decision | ✅ 19 |

### Known gaps, stated rather than hidden

| Gap | Why it is acceptable for V1 | Tracked |
|---|---|---|
| No authentication; single local profile | Localhost-only deployment. **Do not expose to a network.** | ADR-014 |
| SQLite, no Alembic baseline | Schema still moving; the local database is disposable | OEQ-002 |
| Insights are not persisted | `stability_status` is always `TENTATIVE`; SRS-6.7 unreachable | ADR-015 |
| Chat is single-turn | A follow-up has no antecedent. Changing it means revisiting PDR-037🟠 | ADR-018 |
| Validators catch fabricated numbers and causal claims, not hedged elaboration | Narrowing needs claim-level entailment | ADR-016 |
| No CSV import, OCR, categorisation | Deferred V1 features, not regressions | ADR-014 |
| 16 provisional PDR decisions unratified | Blast radius stated per decision | PDR §K |

---

## 6. Traceability

| Element | Requirement | Decision |
|---|---|---|
| Synthetic dataset below the API | SRS-3.18, SRS-3.19 | PDR-012, OEQ-004 |
| Planted patterns + negative controls | `07_AI_Architecture.md` §8 | ADR-019 |
| Zero false positives as primary metric | `07_AI_Architecture.md` §8 | ADR-019 |
| Deterministic generation | SRS-9.1 | ADR-019 |
| Compose stack, single host | — | ADR-013 |
| One origin, no CORS | — | ADR-017 |
| Demo endpoints gated | SRS-8.1 | ADR-014, ADR-019 |
