<div align="center">

# 💰 AI Financial Intelligence Platform

### Understand your financial *behaviour* — with the evidence.

An **explainable** personal-finance intelligence tool. It doesn't just show you *what* you spent — it shows you what your spending was **connected to**, and proves every claim with evidence you can open and check in a tap.

> _“Food & Dining spending was higher in weeks without exercise.”_
> `With exercise ₹4,120/wk (7 weeks) · Without ₹5,870/wk (6 weeks) · +42% · Confidence 82%`

![Landing page](screenshots/30-landing-dark.png)

**FastAPI · SQLAlchemy 2.0 · SQLite · React · TypeScript · Vite · Local LLM (Ollama, optional)**

</div>

---

## 📑 Table of Contents

1. [The Problem — and why we built this](#-the-problem--and-why-we-built-this)
2. [The Core Idea](#-the-core-idea)
3. [What's Included](#-whats-included)
4. [Screenshots](#-screenshots)
5. [Tech Stack](#-tech-stack)
6. [Architecture](#-architecture)
7. [Project Structure](#-project-structure)
8. [Getting Started](#-getting-started)
9. [Configuration](#-configuration)
10. [The Analysis Engine](#-the-analysis-engine)
11. [The AI Narration Layer](#-the-ai-narration-layer)
12. [API Reference](#-api-reference)
13. [Data Conventions](#-data-conventions-non-negotiable)
14. [Testing](#-testing)
15. [Deployment](#-deployment)
16. [Roadmap](#-roadmap--not-yet-implemented)
17. [Security](#-security)

---

## 🎯 The Problem — and why we built this

Most personal-finance apps are **ledgers**. They tell you *what* you spent and *where* — a pie chart of categories, a running balance, maybe a budget bar. What they never tell you is the thing that actually changes behaviour: **why** your spending moves, and what it's connected to in the rest of your life.

At the same time, a wave of "AI money coaches" swung to the opposite extreme — confident, black-box advice with no traceable reasoning, no visible math, and a habit of nudging users toward financial products.

**This project sits deliberately in the gap between those two.** It was built for a specific person:

> A **24–32 year-old salaried professional in an Indian metro** who transacts primarily over **UPI**, wants to understand their own financial *behaviour* (not just track balances), distrusts black-box "AI advice", and insists their financial data never leaves their own machine.

The thesis: if you also record a few things about your **life** — daily habits (sleep, exercise, home-cooked meals, stress) and **life events** (a trip, a move, an illness) — a rigorous statistical engine can surface **honest, checkable associations** between how you live and how you spend. Not causation. Not advice. Just evidence, with its working shown.

It is explicitly **not** regulated financial advice, and it **never directs capital** (no "buy this fund", no "switch this loan"). That boundary is enforced in code, not just in copy.

---

## 💡 The Core Idea

> **The analysis engine is the source of truth. The LLM is only a renderer of truth already established.**

Every number a user ever sees is computed by a **pure, deterministic analysis engine** and frozen into a structured `Insight` object **before any language model runs**. The optional LLM receives a finished insight and writes prose *about* it — it never computes, never invents a figure, and every sentence it produces is checked against the insight's own numbers before a user sees it.

```
 Expenses     Check-ins     Life Events
     └─────────────┼─────────────┘
                   ▼
   ╔═══════════════════════════════════╗
   ║   ANALYSIS ENGINE (pure domain)   ║   ← truth established here
   ║   no I/O · no model · no network  ║
   ╚═══════════════════════════════════╝
                   ▼
          Structured Insight              ← complete BEFORE any model runs
                   │
        ┌──────────┴───────────┐
        ▼                      ▼
   LLM narration        Template renderer
        │                      │
   [3 validators] ──fail──────▶│
        ▼                      ▼
      Prose            Deterministic prose
```

The product is **fully usable with the AI switched off** — narration falls back to hand-written templates, and every response tells you which one you got. Nothing factual differs between the two; only fluency.

---

## ✨ What's Included

| Area | Included |
|---|---|
| 💸 **Expenses** | Manual entry with 15 categories, 6 payment methods, merchant & notes; integer-paise money; filtered, paginated listing |
| 📆 **Daily check-ins** | Six habits (sleep, exercise, home-cooked meals, stress, alcohol, work-mode) with **three-state** semantics: `true` / `false` / **unknown** |
| 📍 **Life events** | Annotate trips, moves, illness, job changes, festivals — point events or ranges — so the engine can exclude or attribute their impact |
| 📊 **Dashboard** | Spending totals, typical-day, largest expense, budget usage, spending-trend chart, month comparison, category donut |
| 🔬 **Insights** | Statistically **gated** behaviour ↔ spending associations, with tiered confidence and **evidence you can open** |
| 🩺 **Data health** | An "insight readiness" panel: what's missing and what unlocks more analysis |
| 💬 **Ask (Q&A)** | A bounded, single-turn assistant that answers from your recorded data and **refuses to recommend financial products** |
| 🤖 **AI narration** | Optional local LLM (Ollama) rewrites insights as fluent prose — validated for provenance, causation-language, and advice-safety |
| 🔐 **Auth** | Real accounts (Argon2id + short-lived JWT in an HttpOnly cookie), per-user data isolation |
| 🎨 **UI** | Warm "Organic" theme, hand-built SVG charts (no chart library), full **light / dark / auto**, fully responsive down to mobile, colour-blind-validated palette |
| 🧪 **Quality** | **838 backend tests · 159 frontend tests**, an import-boundary purity test, and a schema-invariant test that fails the build on unsafe defaults |

---

## 📸 Screenshots

> Captured from the running app against the built-in nine-month demo dataset.

### Landing & Sign-in

| Landing | Sign in / Explore demo |
|---|---|
| ![Landing](screenshots/01-landing.png) | ![Sign in](screenshots/03-auth-signin.png) |
| The public landing page: the product promise and "the loop" it runs on. | Register, log in, or enter the **passwordless demo** — a sample profile entirely separate from any real account. |

### The Dashboard (Overview)

![Dashboard overview](screenshots/04-dashboard-top.png)

_The overview at a glance: **Total spent**, **Typical day**, **Largest expense** and **Budget usage** tiles, a **Spending-trend** line chart (days with no spend shown as zero, not skipped), and a **Month comparison** that only compares complete months. A window switcher (30 / 90 days / 6 months) and a **Template / AI-written** narration toggle sit at the top._

<details>
<summary><b>Full-length dashboard (click to expand)</b></summary>

![Dashboard full](screenshots/05-dashboard-overview-full.png)

_The complete overview: spending, category breakdown, data-health readiness, habit completion & streaks, habit coverage, life events, and a preview of the strongest insights._
</details>

### Expenses, Check-in & Life Events

| Expenses | Daily check-in |
|---|---|
| ![Expenses](screenshots/06-expenses-full.png) | ![Check-in](screenshots/07-checkin-full.png) |
| Add and browse expenses — category, payment method, merchant, notes; amounts stored as integer paise. | Log a day's habits. Omitting a field means **UNKNOWN**, not "it didn't happen" — a distinction the whole analysis depends on. |

![Life events](screenshots/08-life-events-full.png)
_Life & Context: annotate the events that explain spending the statistics otherwise couldn't — a trip, a festival, a move._

### History

![History](screenshots/09-history-full.png)
_A unified timeline of everything recorded — expenses, check-ins and events — for the selected window, so you can scroll through what actually happened._

### Insights — evidence, not opinions

![Insights](screenshots/10-insights-full.png)

_Every insight states **what was observed**, **what it means** (explicitly *"an association, not a cause"*), a **statistical-confidence** bar, and a **Show evidence** drill-down. The footer is honest about the run: how many hypotheses were tested and how many were suppressed by the gates. Insights that fail a gate are hidden entirely — there is no low-confidence tier._

### The Q&A Assistant

![Explore / Ask](screenshots/11-explore.png)

_"Ask about your money" — a single-turn assistant that answers only from analysis already run over your data. A prohibited-topic guard runs **before** anything else, so questions that ask the system to direct capital are refused without ever reaching a model._

### Settings

![Settings](screenshots/12-settings-full.png)
_Profile, budget, preferences, and a first-class **export / delete-all-data** flow (real, cascading deletion — no soft-delete flags)._

### Light & Dark themes

| Light | Dark |
|---|---|
| ![Light dashboard](screenshots/04-dashboard-top.png) | ![Dark dashboard](screenshots/31-dashboard-dark.png) |

_The palette is not an automatic inversion — the dark set is separately stepped for a dark surface, and both were checked with a colour-blindness validator._

### Mobile (fully responsive)

| Overview | Insights |
|---|---|
| <img src="screenshots/20-mobile-overview.png" width="280"/> | <img src="screenshots/21-mobile-insights.png" width="280"/> |

_On small screens the sidebar becomes a bottom tab bar with a floating "add" action; every chart and table reflows._

---

## 🛠 Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| **Backend** | Python 3.13 · [FastAPI](https://fastapi.tiangolo.com/) | Sync endpoints served from a thread pool |
| **ORM** | SQLAlchemy 2.0 (typed, `Mapped[...]`) | Sync engine |
| **Database** | SQLite (WAL mode) | PostgreSQL is a URL change away by design |
| **Validation** | Pydantic v2 + pydantic-settings | Request/response contracts and env config |
| **Auth** | argon2-cffi (Argon2id) · PyJWT (HS256) | Short-lived token in an HttpOnly cookie |
| **Statistics** | **Python standard library only** | Mann–Whitney U · Spearman ρ · Kruskal–Wallis H · Benjamini–Hochberg FDR — no SciPy/NumPy |
| **AI (optional)** | [Ollama](https://ollama.com/) + `qwen2.5:7b-instruct` | Local inference over `urllib`; JSON-schema-constrained decoding |
| **Frontend** | React 18 · TypeScript · Vite 6 | **Zero UI / chart libraries** — charts are hand-built SVG |
| **Testing** | pytest · httpx · Vitest · Testing Library | 838 backend + 159 frontend tests |
| **Deployment** | Docker Compose + nginx (`:8080`) | Single-host stack; optional Ollama profile |

---

## 🏗 Architecture

**Clean / layered architecture — dependencies point inward, never outward.**

```
api/         FastAPI routers + deps + error mapping      (HTTP edge)
services/    orchestration; own the DB session; scope every query by user.id
analysis/    PURE domain engine — no I/O, no model, no network
narration/   Insight → prose: templates, prompts, renderer, validators
chat/        single-turn Q&A: guard → intents → context → templates/prompts
llm/         pluggable model: base · null (templates) · ollama · factory
demo/        synthetic data generator + loader + validation + CLI
models/      SQLAlchemy ORM
schemas/     Pydantic request/response contracts
domain/      money (integer paise), enums, errors  — imports nothing
core/        config · database · clock · security · migrations · unit-of-work
```

- **`api → services → models`** is one-way. `domain` is importable from anywhere and imports nothing.
- **`analysis/` performs no I/O of any kind** — it imports neither SQLAlchemy nor FastAPI. It consumes frozen dataclasses and returns `Insight` objects, so every analytic is unit-testable with literal data. This boundary is asserted by a test that parses the package's imports, not by code review.
- Services take a `Session` and a `Clock` and know nothing about HTTP — the rules are testable without a web server.

### A request, end to end
1. **Router** receives HTTP, resolves the current user (`api/deps.py → require_user`), validates with a Pydantic **schema**.
2. **Service** owns the session, **scopes every query by `user.id`**, and commits through the **`atomic()` unit-of-work** (rollback-on-error, integrity errors translated to typed domain errors).
3. For insights: the service loads rows and hands a plain dataset to the **analysis engine**, which returns fully-formed `Insight` objects.
4. **Narration / chat** optionally renders prose via the **LLM**; three validators check it; failure falls back to templates.
5. The response is serialised through a schema; domain errors are mapped to status codes in one place.

---

## 📂 Project Structure

```
AI-Financial-Intelligence/
├── backend/
│   └── app/
│       ├── main.py            FastAPI app, router registration, startup migration
│       ├── core/              config · database (engine + pragmas) · clock · security
│       │   ├── database.py         SQLite engine: WAL, busy_timeout, FK enforcement
│       │   ├── unit_of_work.py     atomic() transaction ctx + retry_on_locked
│       │   └── migrations.py       idempotent, additive startup migration (no Alembic)
│       ├── domain/            enums · money · errors · preferences  (no framework imports)
│       ├── analysis/          the Behaviour Analysis Engine  (no I/O of any kind)
│       │   ├── engine.py           analyse(dataset, now, gates) → AnalysisResult
│       │   ├── stats.py            Mann–Whitney · Spearman · Kruskal–Wallis · BH-FDR
│       │   ├── gates.py            the five gates and their thresholds
│       │   ├── expenses.py · habits.py · events.py · relationships.py
│       │   └── models.py           Insight · Evidence · InsightType · InsightTier
│       ├── narration/         Insight → prose: payload · prompts · validators · templates
│       ├── llm/               base · null (default) · ollama · factory
│       ├── models/            SQLAlchemy ORM: user · expense · check_in · life_event
│       ├── schemas/           Pydantic contracts
│       ├── services/          business rules, one per resource
│       └── api/               deps · error mapping · routes/
├── frontend/
│   └── src/
│       ├── pages/             Landing · Auth · Dashboard · Expenses · CheckIn ·
│       │                      LifeEvents · History · Insights · Chat · Settings · Onboarding
│       ├── components/        cards, charts (BarChart/LineChart/DonutChart), forms, chat
│       ├── hooks/             useAuth · useChat · useDashboardData · useTheme · …
│       ├── lib/               money · format · metrics · enums (integer-paise safe)
│       ├── api/               client · endpoints · types
│       └── index.css          design tokens + the whole theme (light/dark)
├── tests/                     838 backend tests (mirrors the package layout)
├── docs/                      14 design documents + 19 Architecture Decision Records
├── docker/                    Dockerfile.backend · Dockerfile.frontend · compose · nginx
├── screenshots/               the images used in this README
├── requirements.txt · requirements-dev.txt · pyproject.toml
```

---

## 🚀 Getting Started

### Prerequisites
- **Python 3.11+** (developed on 3.13)
- **Node.js 18+** and npm
- _(optional)_ **[Ollama](https://ollama.com/)** for AI-generated narration

### 1 · Backend

```bash
# from the repository root
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

pip install -r requirements-dev.txt
```

Load the deterministic nine-month demo dataset (built to exercise every analytic):

```bash
PYTHONPATH=backend AFI_DEMO_MODE=true python -m app.demo seed
```

Run the API:

```bash
AFI_DEMO_MODE=true AFI_AUTH_SECRET=dev-secret python -m uvicorn app.main:app --app-dir backend --port 8000
```

- API: **http://127.0.0.1:8000** · Interactive docs: **http://127.0.0.1:8000/docs** · Health: `/health`

### 2 · Frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**. The Vite dev server proxies `/api` to the backend on port 8000, so the browser only ever talks to one origin.

> On the sign-in screen, click **“Explore the demo”** to enter the passwordless sample profile with all the data loaded.

### 3 · (Optional) Enable AI narration

```bash
ollama pull qwen2.5:7b-instruct
# then start the backend with the ollama provider:
AFI_LLM_PROVIDER=ollama AFI_LLM_MODEL=qwen2.5:7b-instruct \
AFI_DEMO_MODE=true AFI_AUTH_SECRET=dev-secret \
python -m uvicorn app.main:app --app-dir backend --port 8000
```

Flip the **“AI-written”** toggle in the UI. Generation runs locally; a 7B model on CPU takes tens of seconds per insight, so `AFI_LLM_MAX_GENERATED` (default 5) caps generation per request and spends it on the highest-confidence insights first. Every insight is still explained — the rest use templates.

### Demo CLI

```bash
PYTHONPATH=backend AFI_DEMO_MODE=true python -m app.demo seed      # load (replaces existing)
PYTHONPATH=backend AFI_DEMO_MODE=true python -m app.demo status    # what is loaded
PYTHONPATH=backend AFI_DEMO_MODE=true python -m app.demo clear     # remove records, keep profile
PYTHONPATH=backend AFI_DEMO_MODE=true python -m app.demo validate  # check planted patterns survive
```

---

## ⚙️ Configuration

Settings are read from the environment with the `AFI_` prefix (a `.env` file is also honoured). A fresh clone runs with **zero configuration** in development.

| Variable | Default | Description |
|---|---|---|
| `AFI_DATABASE_URL` | `sqlite:///…/financial_intelligence.db` | Any SQLAlchemy URL. In-memory (`sqlite://`) is used by tests. |
| `AFI_ENVIRONMENT` | `development` | `production` makes the auth secret **fail closed**. |
| `AFI_AUTH_SECRET` | dev fallback | JWT signing secret. **Required** in production. Generate: `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `AFI_DEMO_MODE` | `false` | Enables the destructive seed/clear endpoints and the "Explore demo" account. |
| `AFI_LLM_PROVIDER` | `none` | `none` (templates) or `ollama`. |
| `AFI_LLM_MODEL` | `qwen2.5:7b-instruct` | Ollama model tag. |
| `AFI_LLM_BASE_URL` | `http://127.0.0.1:11434` | Ollama endpoint. |
| `AFI_LLM_MAX_GENERATED` | `5` | Max LLM generations per request; the rest use templates. |
| `AFI_CORS_ORIGINS` | `[]` | Allowed origins (only needed if not using the dev proxy). |

---

## 🔬 The Analysis Engine

`GET /api/insights` runs the engine and returns `Insight` objects — the single structure the dashboard, the narrator, and the assistant all consume. **The engine writes no natural language**; `title_key` is a stable identifier a renderer maps to a sentence, which is what makes generated prose checkable.

**Insight tiers:** `T1` arithmetic · `T2` comparison · `T3` statistical.

**Five gates stand between a detected pattern and a shown insight.** Six habits against fourteen categories is 84 hypotheses per run, of which ~4 would clear α = 0.05 by chance. A failure **suppresses the insight entirely** — there is no low-confidence tier.

| Gate | Requirement |
|---|---|
| **G1 — History** | ≥ 8 complete weeks |
| **G2 — Group size** | ≥ 6 observations in *each* compared group |
| **G3 — Coverage** | ≥ 60 % per-habit coverage |
| **G4 — Effect size** | ≥ ₹500/week **and** ≥ 15 % relative |
| **G5 — Significance** | Benjamini–Hochberg FDR at q = 0.10 across **all** hypotheses in the run |

When history or coverage is the blocker, a **Data Sufficiency notice** tells the user what's missing instead. Statistics use the standard library: Mann–Whitney U (binary habits), Spearman ρ (ordinal/numeric), Kruskal–Wallis H (`work_mode`), BH for multiplicity.

---

## 🤖 The AI Narration Layer

`GET /api/narrations` explains each insight in five sections (observation, evidence, interpretation, confidence, suggestion). The model receives a finished `Insight` and writes prose about it — **it computes nothing**.

**Three validators stand between a generation and the user**, and any failure discards the whole generation (falling back to a template) rather than editing it:

| Validator | Rejects |
|---|---|
| **Provenance** | Any numeric literal absent from the payload the model was given (formatting-aware: `₹4,120.00` ≡ `412000 paise`). |
| **Lexical** | Causal connectives in T2/T3 content — an association is never phrased as a cause. |
| **Advice guard** | Investments, funds, SIPs, insurance, loans, tax schemes, crypto — and any unhedged instruction. |

**Confidence is written by code, never the model** — the output schema has no confidence field, so there is no slot for a fabricated figure. `GET /api/narrations/prompt/{id}` returns the exact prompts and the numbers the model is held to, so "what did it actually see?" is answerable without a debugger.

---

## 🌐 API Reference

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/auth/register` · `/login` · `/logout` · `/demo` | Accounts and sessions (`/demo` is passwordless, gated by demo mode) |
| `GET` | `/api/auth/me` | The current authenticated user |
| `GET · PATCH` | `/api/profile` | The profile; `DELETE /api/profile/data` hard-deletes everything owned |
| `POST · GET` | `/api/expenses` | Filters: `start_date`, `end_date`, `category`, `limit`, `offset` |
| `GET · PATCH · DELETE` | `/api/expenses/{id}` | |
| `POST · GET` | `/api/check-ins` | Keyed by date — one check-in per day |
| `GET · PATCH · DELETE` | `/api/check-ins/{log_date}` | |
| `POST · GET` | `/api/life-events` | Filters incl. `event_type` |
| `GET` | `/api/insights` · `/api/insights/types` · `/api/insights/{type}` | Fresh engine run (window: `days`, default 90) |
| `GET` | `/api/narrations` · `/status` · `/prompt/{id}` | Explained insights + model reachability + exact prompt |
| `POST` | `/api/chat` | Single-turn Q&A; `GET /api/chat/capabilities` lists what it can be asked |
| `GET · POST · DELETE` | `/api/demo` | Status / seed / clear (gated by `AFI_DEMO_MODE`) |
| `GET` | `/health` | Liveness probe |

Full interactive documentation is served at `/docs` (Swagger UI) and `/redoc`.

---

## 🔒 Data Conventions (non-negotiable)

**Money is integer paise.** ₹450.00 is sent as `45000`. No float ever touches an amount — not the column, not the schema, not the formatter. Responses include `amount_display` (`"450.00"`) so no client divides by 100.

**A missing habit means UNKNOWN, never "it didn't happen."**

```jsonc
{ "log_date": "2026-07-27", "exercise": false }   // recorded: did NOT exercise
{ "log_date": "2026-07-27", "sleep_hours": 7.5 }  // exercise is UNKNOWN, not false
```

A `BOOLEAN NOT NULL DEFAULT FALSE` on a habit would make a user who only logs gym days look like they skipped every unlogged day — manufacturing a correlation from nothing. A schema-invariant test fails the build if such a default is ever added.

---

## 🧪 Testing

```bash
# Backend — 838 tests, no model required
python -m pytest

# Frontend — 159 tests
cd frontend && npm test

# Frontend type-check + production build
cd frontend && npm run typecheck && npm run build
```

Notable guardrails: an **import-boundary test** parses the `analysis/` package and fails if it ever imports a DB driver or web framework; a **schema-invariant test** rejects unsafe column defaults; a **cross-user isolation suite** proves one account can never read another's rows.

---

## 🐳 Deployment

Single-host Docker Compose stack (nginx serves the built frontend and proxies `/api` to the API container, which is never published to the host).

```bash
docker compose -f docker/docker-compose.yml up --build
# seed the demo data:
docker compose -f docker/docker-compose.yml run --rm api python -m app.demo seed
# open http://localhost:8080
```

Optional local LLM (adds an Ollama sidecar):

```bash
docker compose -f docker/docker-compose.yml --profile llm up --build
```

For a real deployment set `AFI_ENVIRONMENT=production` and a strong `AFI_AUTH_SECRET` — with production set and no secret, the API **refuses to start**.

---

## 🗺 Roadmap / Not Yet Implemented

Live bank integrations · CSV import & OCR · merchant normalisation & automatic categorisation · multi-turn chat · goal setting / net worth · native mobile · investment/tax/insurance/loan advice (a **regulatory boundary**, not a feature gap). Insights are computed on demand and not persisted, so `stability_status` is always `TENTATIVE`.

---

## 🔐 Security

- Passwords are hashed with **Argon2id**; plaintext is never stored or logged.
- Sessions are **short-lived JWTs** delivered as an **HttpOnly cookie** (unreadable by page JavaScript).
- Every user-owned query is **scoped by `user.id`** at the service boundary and covered by a cross-user isolation test suite.
- Writes go through an **`atomic()` unit-of-work** — no half-committed state, and integrity failures surface as clean typed errors.
- SQLite runs in **WAL** with foreign-key enforcement and a busy timeout.

The demo/seed endpoints are **off by default** and, when on, wipe data without authentication — keep `AFI_DEMO_MODE` off outside a local demo, and do not expose an unauthenticated instance to a network.

---

<div align="center">

_Built as an explainable, privacy-first alternative to both dumb ledgers and black-box money coaches._
_The engine is the truth. The model only helps you read it._

</div>
