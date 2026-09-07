# Architecture — AI Financial Intelligence Platform

> Working summary for AI-assisted development. The authoritative version is
> [`docs/04_System_Architecture.md`](docs/04_System_Architecture.md) plus the
> [19 ADRs](docs/11_Architecture_Decision_Records/). What V1 deliberately
> simplifies from the documented target (and why) is
> [ADR-014](docs/11_Architecture_Decision_Records/ADR-014-mvp-simplifications.md).

## 1. The one idea that governs everything

**The analysis engine is the source of truth. The LLM is a renderer of truth
already established.**

```
 Transactions   Check-ins   Life Events
       └────────────┼────────────┘
                    ▼
   ╔═════════════════════════════════╗
   ║  ANALYSIS ENGINE (pure domain)  ║   ← truth established here
   ║  no I/O · no model · no network ║
   ╚═════════════════════════════════╝
                    ▼
           Structured Insight            ← complete BEFORE any model runs
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
  LLM narration          Template renderer
        │                       │
   [validators] ───fail────────▶│
        ▼                       ▼
     Prose             Deterministic prose
```

The engine (`backend/app/analysis/`) **cannot perform I/O**. It imports no DB
driver, no web framework, no HTTP client — a boundary asserted by a test that
parses the package's imports, not by code review. Loading happens in exactly one
service outside it (`analysis_service.py`).

## 2. Layered / Clean Architecture

Dependencies point inward. Outer layers depend on inner; never the reverse.
→ [ADR-001](docs/11_Architecture_Decision_Records/ADR-001-clean-architecture.md)

```
api/         FastAPI routers + deps + error mapping   (HTTP edge)
  └─ routes/ expenses, check_ins, life_events, insights, narrations,
             chat, demo, auth, profile
services/    orchestration; own the DB session; scope every query by user.id
  └─ expense_service, check_in_service, life_event_service,
     analysis_service, narration_service, chat_service,
     auth_service, profile_service
analysis/    PURE domain engine — no I/O, no model, no network
  └─ engine, dataset, window, stats, gates, habits, events,
     expenses, relationships, models, __init__ (import-boundary test)
narration/   Insight → prose: templates, prompts, renderer, validators
chat/        single-turn Q&A: guard → intents → context → templates/prompts
llm/         pluggable model: base, null (templates), ollama, factory
demo/        synthetic data generator + loader + validation + CLI
models/      SQLAlchemy ORM: user, expense, check_in, life_event, base
schemas/     Pydantic request/response contracts
domain/      money (integer paise), enums, errors
core/        config, database, clock, security, migrations
```

## 3. Data flow (a request)

1. **Router** (`api/routes/*`) receives HTTP, resolves the current user via
   `api/deps.py` (`require_user`), validates with a Pydantic **schema**.
2. **Service** owns the DB session and scopes **every** query by `user.id`.
3. For insights: service loads rows, hands a plain dataset to the **analysis
   engine**, which returns fully-formed `Insight` objects (all numbers final).
4. **Narration / chat** optionally renders prose via the **LLM**; validators
   check provenance/lexical/advice; failure falls back to templates.
5. Response serialized through a schema; errors mapped in `api/errors.py`.

A question takes the same path with one gate in front: the **prohibited-topic
guard** runs *before* classification, so anything asking the system to direct
capital is refused without ever reaching a model.

## 4. Tech stack

| Layer | Documented target | V1 reality (ADR-014) |
|---|---|---|
| Backend | FastAPI · SQLAlchemy 2.0 **async** · **PostgreSQL 16** | FastAPI · SQLAlchemy **sync** · **SQLite** |
| Architecture | Clean Architecture, CI-enforced boundaries | same |
| AI | Qwen2.5-7B-Instruct via local **Ollama** | pluggable; `null` templates by default |
| Frontend | React · TypeScript · Vite | same |
| Deployment | Docker Compose, single host, nginx proxy `:8080` | same |
| Auth (V1.2) | Argon2id + short-lived JWT, HttpOnly cookie | in progress |

The V1 simplifications (SQLite for Postgres, sync ORM, no auth in V1) are
intentional and documented, not accidental. What V1 **refuses** to simplify — the
analysis engine's purity, integer paise, three-state semantics, the five gates —
is the core, and is never traded away.

## 5. Persistence & migration

- ORM models in `models/`, base in `models/base.py`.
- V1 used `create_all` at lifespan startup (`main.py`); **no Alembic**.
- V1.2 adds `core/migrations.py`: a **lightweight idempotent, non-destructive,
  ALTER-based startup migration**. Never `drop_all`/`create_all` as the migration
  mechanism. → ADR-014.

## 6. Multi-user & isolation (V1.2)

- **Isolation = service-method scoping** (not constructor-scoped repos). Every
  user-owned query is scoped by `user.id`; enforced by a cross-user isolation
  test suite (`tests/test_isolation.py`).
- `require_user` in `api/deps.py` is the auth seam; public routes are
  `auth/*`, `/health`, `demo/*`.
- Demo is a dedicated `is_demo=true` user — demo data never contaminates a real
  account and real accounts start empty.
- See [`Memory.md`](Memory.md) for the locked decisions and live milestones.

## 7. Repository map

```
docs/       14 design documents + 19 ADRs (authoritative)
backend/    FastAPI app: CRUD + analysis + narration + chat + demo + auth
tests/      backend test suite
frontend/   React app, 7 sections
datasets/   placeholder — demo dataset is generated in app/demo/
docker/     Compose stack (builds + runs on :8080)
.github/    CI (pytest · demo validate · frontend typecheck/test/build)
```
