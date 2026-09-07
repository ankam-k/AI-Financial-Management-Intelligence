# ADR-015 — Analysis engine V1: the Insight contract, stdlib statistics, no persistence

**Status:** Accepted · **Date:** 2026-07-28 · **Serves:** PDR-031, SRS-2.1, SRS-6.* · **Implements:** ADR-007, `07_AI_Architecture.md` §2–3

## Decision

Five decisions taken while building the Behavior Analysis Engine (Sprint 2):

| # | Decision |
|---|---|
| 1 | `Insight` carries a **`title_key`**, never a title. The engine emits no natural language. |
| 2 | **`confidence` is optional** — required for T3, forbidden for T1/T2. |
| 3 | The statistical tests are **implemented on the standard library**. SciPy is not added. |
| 4 | Insights are **computed on demand and not persisted**. |
| 5 | For rank-correlation habits, the **effect size for gate G4 comes from a median split**, while the test itself remains Spearman over all weeks. |

Plus one schema addition: `user.monthly_budget_paise`, nullable.

## Context

`07_AI_Architecture.md` fixes the analysis design — four stages, weekly unit of observation, five gates, non-parametric tests — but not the shape of the object those stages produce, nor how the statistics get computed. Sprint 2 had to settle both.

The proposed starting sketch was:

```python
class Insight:
    id: str
    type: InsightType
    title: str
    evidence: list[Evidence]
    metrics: dict
    confidence: float
    created_at: datetime
```

Right in its central instinct — one object, defined once, that dashboard, reports, recommendations and the model all consume — and wrong in two details that matter, both addressed below.

## Alternatives

**1. `title: str` versus `title_key: str`.** A title is convenient: a renderer can print it directly. But a title is prose, and prose from the engine cannot be validated. ADR-009's provenance validator works by extracting every numeric literal from generated text and asserting set-membership against the insight's numbers — a check that is only possible because the insight is *finished, and finished in structured form*, before generation begins. `"You spent ₹4,120 on food"` emitted by the engine is an unvalidatable sentence, and the guarantee is gone with it. `title_key` keeps the identifying intent and moves the sentence downstream.

**2. `confidence: float` versus `float | None`.** Always-present confidence forces a value onto insights that have none. A total is a sum; there is no uncertainty to report, and `1.0` would be a fabricated number in a system whose entire claim is that it fabricates none. Making it nullable and *enforcing* the rule — required for T3, rejected for T1/T2 — keeps the field meaningful wherever it appears (SRS-2.1, PDR-032🟠).

**3. SciPy versus the standard library.** SciPy gives exact small-sample p-values and is the obvious production choice. Against it: Sprint 2 was scoped to add no dependency unless necessary, and gate G2 already requires n ≥ 6 per group, which is the range where the normal and chi-square approximations are serviceable. Mann–Whitney U (tie-corrected normal approximation), Spearman ρ (Fisher z), Kruskal–Wallis H (chi-square, df ≤ 2 in closed form) and Benjamini–Hochberg are ~200 lines of `math`. The approximation is stated on each function, and `chi_square_sf` raises rather than guess above df = 2.

**4. Persisting insights versus computing on demand.** `05_Database_Design.md` §6 specifies `insight`, `insight_evidence` and `insight_feedback` tables, and SRS-6.7 needs stored history to promote a T3 claim from `TENTATIVE` to `ESTABLISHED`. Against persisting now: a stored insight goes stale the moment a check-in in its window is edited (SRS-5.8), so persistence brings an invalidation problem with it, and V1 datasets are small enough that a full run is milliseconds. Computing on demand also makes insight ids content-addressed rather than surrogate, which is strictly more useful until there is a feedback row to point at one.

**5. Effect size for rank correlations.** Gate G4 is stated in ₹/week, which a correlation coefficient does not produce. Options: skip G4 for Spearman habits (rejected — G4 is what keeps trivial findings out), or express the effect as ρ (rejected — the threshold is in rupees, and ρ is not convertible to it), or split the weeks at their median habit value and compare the halves. The third keeps the gate meaningful and the test unchanged.

## Tradeoffs

| Gain | Cost |
|---|---|
| Prose is a downstream view, so every generated sentence is validatable | Renderers need a `title_key` → text lookup table; an unmapped key shows as a raw key |
| `confidence` means something wherever it appears | Consumers must handle `None`; a naive `insight.confidence > 0.8` filter breaks |
| Zero new dependencies; the engine runs anywhere Python does | p-values are approximate — stated per function, and adequate only because G2 bounds n from below |
| No staleness problem, no invalidation logic, no migration | `ESTABLISHED` stability is unreachable; every T3 claim stays `TENTATIVE` |
| G4 applies uniformly across all six habits | The reported effect for a Spearman habit is a derived split, not the tested quantity — recorded as such on the insight |
| Budget utilisation has a real budget to measure against | One additive column on a Sprint 1 table |

## Final Choice

**Structured truth, enforced at construction.**

`Insight.__post_init__` rejects: an insight with no evidence (SRS-2.5), a T3 without confidence, a T1/T2 with one, and any metric value that is not JSON-serialisable. These are not documented conventions — they are constructor failures, so a violation is a crash in a unit test rather than a wrong number in a dashboard.

The engine is pure: `analyse(dataset, now, gates)` takes frozen dataclasses and a timestamp, performs no I/O, and returns byte-identical output for identical input, insight ids included. `app/services/analysis_service.py` is the only file in the analysis path that touches a database. That is ADR-001's boundary, realised without the repository ports ADR-014 deferred.

## Consequences

- **`app/analysis/` must not import SQLAlchemy or FastAPI.** The engine consumes `ExpenseRecord`/`CheckInRecord`/`EventRecord`, not ORM models — partly for purity, and partly because an ORM instance emits SQL on attribute access, which inside an analysis loop is an N+1 nobody sees until the dataset grows.
- **Every renderer needs a `title_key` table.** The set is closed and enumerable at `GET /api/insights/types`.
- **Adding a categorical habit with more than three levels breaks `chi_square_sf`** — deliberately, with `NotImplementedError`. Such a habit needs an incomplete gamma function or SciPy.
- **`stability_status` is always `TENTATIVE`.** Promotion needs stored history; when insight persistence lands, SRS-6.7 becomes implementable and this ADR's decision 4 should be revisited.
- **Changing any computation requires bumping `ENGINE_VERSION`**, which is recorded on every run.
- **`user.monthly_budget_paise` is a schema change with no migration path** — V1 has no Alembic (ADR-014), so an existing local database must be deleted and recreated. Tracked as OEQ-002.
