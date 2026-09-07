# Backend

FastAPI + SQLAlchemy 2.0 + SQLite, no other runtime dependencies.

* **Sprint 1** — local profile and CRUD for the three data streams.
* **Sprint 2** — the Behavior Analysis Engine that turns them into structured
  `Insight` objects.
* **Sprint 3** — the AI Insight Generator that explains those objects, with
  three validators standing between a generation and a user.

## Run it

```bash
python -m pip install -r backend/requirements-dev.txt
python -m uvicorn app.main:app --reload --app-dir backend
```

Interactive docs: <http://127.0.0.1:8000/docs> · Health: `/health`

A `financial_intelligence.db` file is created in the working directory on
first start, and the local profile is created on the first API request. There
is no sign-up step.

```bash
python -m pytest          # 746 tests, no model required
```

Load nine months of demo data — deterministic, and built to exercise every
analytic the engine supports:

```bash
python -m app.demo seed       # load (replaces what is there)
python -m app.demo clear      # remove every record, keep the profile
python -m app.demo status     # what is loaded
python -m app.demo validate   # check the planted patterns still survive
```

Narration works with no model installed — see *The AI Insight Generator*
below. To enable generated prose:

```bash
ollama pull qwen2.5:7b-instruct
AFI_LLM_PROVIDER=ollama python -m uvicorn app.main:app --app-dir backend
```

## Layout

```
app/
├── main.py          FastAPI app, router registration, table creation
├── core/            config · database engine + session · injected clock
├── domain/          enums · money · errors        (no framework imports)
├── analysis/        the Behavior Analysis Engine  (no I/O of any kind)
│   ├── models.py        Insight · Evidence · InsightType · InsightTier
│   ├── window.py        analysis window, ISO week and month bucketing
│   ├── dataset.py       the engine's frozen, session-free input
│   ├── stats.py         Mann-Whitney · Spearman · Kruskal-Wallis · BH-FDR
│   ├── gates.py         the five gates and their thresholds
│   ├── expenses.py      totals · categories · month/week · trend · budget
│   ├── habits.py        completion · streaks · sleep · exercise · missed
│   ├── events.py        per-event summaries · during-vs-outside impact
│   ├── relationships.py habit ↔ category associations (T3)
│   └── engine.py        analyse(dataset, now, gates) → AnalysisResult
├── narration/       the AI Insight Generator      (no I/O of any kind)
│   ├── models.py        Narration · NarrationSource · ValidationFailure
│   ├── payload.py       what the model sees, and the numbers it is held to
│   ├── prompts.py       system prompt · user prompt · output grammar
│   ├── validators.py    provenance · lexical · advice guard · shape
│   ├── templates.py     deterministic prose for every InsightType
│   └── renderer.py      template first, generation as a reviewed upgrade
├── llm/             model adapters                (the only network I/O)
│   ├── base.py          LLMClient protocol and error hierarchy
│   ├── ollama.py        local Ollama over urllib (ADR-008)
│   ├── null.py          the default: no model configured
│   └── factory.py       provider selection from config
├── models/          SQLAlchemy ORM models
├── schemas/         Pydantic request/response models
├── services/        business rules                (no HTTP imports)
└── api/             dependencies · error mapping · routers
```

The dependency direction is one-way: `api → services → models`, with `domain`
importable from anywhere and importing nothing. Services take a `Session` and
a `Clock` and know nothing about HTTP, which is what lets the rules be tested
without a web server.

`analysis/` goes further: it imports neither SQLAlchemy nor FastAPI. It
consumes frozen dataclasses and returns `Insight` objects, so every analytics
function is unit-testable with literal data — no database, no fixtures.
`services/analysis_service.py` is the only file in the analysis path that
touches a database.

## Endpoints

| Method | Path | |
|---|---|---|
| GET · PATCH | `/api/profile` | The local profile |
| DELETE | `/api/profile/data` | Hard-delete the profile and everything it owns |
| POST · GET | `/api/expenses` | Filters: `start_date`, `end_date`, `category`, `limit`, `offset` |
| GET · PATCH · DELETE | `/api/expenses/{id}` | |
| POST · GET | `/api/check-ins` | Filters: `start_date`, `end_date` |
| GET · PATCH · DELETE | `/api/check-ins/{log_date}` | Keyed by date — one check-in per day |
| POST · GET | `/api/life-events` | Filters: `start_date`, `end_date`, `event_type` |
| GET · PATCH · DELETE | `/api/life-events/{id}` | |
| GET | `/api/insights` | Full run. Window: `start_date`/`end_date`, or `days` (default 90) |
| GET | `/api/insights/types` | The closed set of insight types |
| GET | `/api/insights/{type}` | Filtered view of the same run |
| GET | `/api/narrations` | Every insight, explained in five sections |
| GET | `/api/narrations/status` | Whether a model is configured and reachable |
| GET | `/api/narrations/prompt/{id}` | The exact prompt one insight produces |
| POST | `/api/chat` | Ask one question. Single-turn — no conversation id, no history |
| GET | `/api/chat/capabilities` | What it can be asked, served from the routing rules |
| GET · POST · DELETE | `/api/demo` | Status, seed, clear. Gated by `AFI_DEMO_MODE` |
| GET | `/api/demo/design` | The planted patterns and negative controls |

## The analysis engine

`GET /api/insights` runs the engine and returns `Insight` objects — the single
structure the dashboard, reports, and (later) the model all consume.

```jsonc
{
  "id": "a1b2c3d4e5f60718",       // content-addressed, stable across runs
  "type": "BEHAVIOR_RELATIONSHIP",
  "tier": "T3",                    // T1 arithmetic · T2 comparison · T3 statistical
  "title_key": "RELATIONSHIP_EXERCISE_FOOD_DINING",   // a key, never prose
  "subject": "exercise:FOOD_DINING",
  "metrics": { /* every number the user will ever see */ },
  "evidence": [ /* rows the user can open and check */ ],
  "confidence": 0.999,             // T3 only — a sum is not uncertain
  "created_at": "2026-06-22T09:00:00+05:30"
}
```

**The engine writes no natural language.** `title_key` is a stable identifier a
renderer maps to a sentence. That is what makes the eventual model output
checkable: every number exists in `metrics` before generation begins, so a
validator has an authoritative set to test generated prose against.

**Five gates stand between a detected pattern and a shown insight.** Six habits
against fourteen spending categories is 84 hypotheses per run, of which four
would clear α = 0.05 by chance alone. Gates: ≥ 8 complete weeks, ≥ 6 weeks per
compared group, ≥ 60% per-habit coverage, effect ≥ ₹500/week **and** ≥ 15%, and
Benjamini–Hochberg FDR at q = 0.10. A failure suppresses the insight entirely —
there is no low-confidence tier. When history or coverage is the blocker, a
`DATA_SUFFICIENCY` notice says so instead.

**A missing habit is excluded, never imputed.** Weeks with no recorded value for
a habit are dropped from that habit's tests and counted in
`observations.excluded_unknown`. Coverage is per-habit: a check-in holding only
`sleep_hours` gives zero coverage for `exercise`.

Statistics are computed on the standard library — Mann–Whitney U for binary
habits, Spearman ρ for ordinal and numeric, Kruskal–Wallis H for `work_mode`,
Benjamini–Hochberg for multiplicity. p-values are approximate; see
[ADR-015](../docs/11_Architecture_Decision_Records/ADR-015-analysis-engine-v1.md)
for why SciPy was not added and when it should be.

Insights are computed on demand, not stored. `GET /api/insights` is a fresh run
every time.

## The AI Insight Generator

`GET /api/narrations` explains every insight in five sections. The model never
computes anything — it receives a finished `Insight` and writes prose about it.

```jsonc
{
  "observation":    "Higher spending on food and dining was observed alongside weeks without exercise.",
  "evidence":       "In weeks without exercise, the median spending was 608,000 paise, compared to 407,000 paise in weeks with exercise.",
  "interpretation": "This is an association and does not establish a cause.",
  "confidence":     "Confidence 99.9%. It was one of 28 associations tested in this run…",
  "suggestion":     "Consider maintaining a consistent exercise routine…",
  "source": "LLM",  "model": "ollama:qwen2.5:7b",
  "validation_failures": [], "fallback_reason": null
}
```

**It works with no model installed.** The default provider is `none` and every
narration is rendered from a hand-written template. Templates are not a stub —
they are what runs by default, and `source` tells you which you got. Nothing
factual differs between the two; only fluency.

**Three validators stand between a generation and a user**, and a failure
discards the whole generation rather than editing it:

| Validator | Rejects |
|---|---|
| **Provenance** | Any numeric literal absent from the payload the model was given. `₹4,120.00` ≡ `412000 paise` ≡ `4,120` — formatting is not fabrication. |
| **Lexical** | Causal connectives in T2 and T3 content. Only T1 is exempt, where the claim is an accounting identity (PDR-036). Denials of causation are exempt — "not a cause" is the wanted phrasing. |
| **Advice guard** | Investments, funds, SIPs, insurance products, loans, tax schemes, crypto — and unhedged instructions. Runs independently of the other two (ADR-010). |

**Confidence is written by code, never by the model.** The output schema has
no confidence field, so there is no slot for a fabricated figure to occupy.
The sentence is derived from the insight's own tier and q-value.

`GET /api/narrations/prompt/{insight_id}` returns the exact system prompt,
user prompt, output grammar, and the full set of numbers the model will be
held to — so "what did it actually see?" is answerable without a debugger.

Measured against `qwen2.5:7b`: 3 of 4 attempted generations passed; the
rejection cited a figure that was not in its input. Roughly 18s per insight
locally, so `AFI_LLM_MAX_GENERATED` (default 5) caps generation per request
and spends it on the highest tier first. Every insight is still explained.

See [ADR-016](../docs/11_Architecture_Decision_Records/ADR-016-narration-layer.md).

## Two conventions that are not negotiable

**Money is integer paise.** ₹450.00 is sent as `45000`. No float touches an
amount anywhere — not the column, not the schema, not the formatter. Responses
include `amount_display` (`"450.00"`) so no client divides by 100 itself.

**A missing habit means UNKNOWN, never "it didn't happen."**

```jsonc
// "I did not exercise" — a recorded fact
{"log_date": "2026-07-27", "exercise": false}

// "I don't know whether I exercised" — an absence of fact
{"log_date": "2026-07-27", "sleep_hours": 7.5}
```

The same distinction applies to `PATCH`: omitting a field leaves it alone,
sending it as `null` resets that habit to UNKNOWN. These are different
requests and produce different rows.

This is the schema's most important rule. A `BOOLEAN NOT NULL DEFAULT FALSE`
on `exercise` would make a user who only logs gym days look like they skipped
every unlogged day — manufacturing a correlation out of nothing, while every
individual row stayed perfectly traceable. `tests/test_invariants.py` fails
the build if a default is ever added.

See [ADR-007](../docs/11_Architecture_Decision_Records/ADR-007-statistical-method.md)
and [ADR-014](../docs/11_Architecture_Decision_Records/ADR-014-mvp-simplifications.md).

## Not implemented yet

CSV import, OCR, merchant normalisation, automatic categorisation, the bounded
Q&A subsystem, and the React client. Insights are not persisted, so
`stability_status` is always `TENTATIVE`.

The backend is unauthenticated by design (ADR-014) — **do not expose it to a
network.**

Schema changed in Sprint 2 (`user.monthly_budget_paise`). There is no Alembic
in V1, so delete `financial_intelligence.db` and restart if you have a
database from Sprint 1.
