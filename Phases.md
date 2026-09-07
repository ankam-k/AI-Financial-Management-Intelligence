# Phases — AI Financial Intelligence Platform

> The build broken into manageable steps, because AI can't build everything at
> once. Product phasing detail is in [`docs/12_Future_Roadmap.md`](docs/12_Future_Roadmap.md);
> live V1.2 milestone status is in [`Memory.md`](Memory.md) and the memory index.

## Release timeline (where we are)

- **V1 / V1.1 — DONE (🟢).** The full product loop is usable from the UI.
- **V1.2 — IN PROGRESS.** Multi-user + authentication, on top of V1.1.

## V1 — foundation (complete)

Each phase produced working, tested code. Summarized as delivered capabilities:

1. **Domain core** — integer-paise money, enums, clock, error types.
2. **Persistence & CRUD** — expenses, check-ins (three-state habits), life events;
   services that own the session.
3. **Ingestion** — CSV statement upload with per-bank adapters; dedup.
4. **Categorization** — merchant normalization + explainable categorization.
5. **Analysis engine (pure)** — dataset → windows → stats → gates → habits /
   events / expenses / relationships → `Insight` objects. I/O-free, model-free,
   import-boundary asserted by test.
6. **Statistical gating** — five gates + Benjamini–Hochberg FDR; no low-confidence
   tier.
7. **Narration** — `Insight` → prose via templates; LLM optional; three
   validators; whole-generation rejection.
8. **Assistant (chat)** — single-turn Q&A; prohibited-topic guard *before*
   classification; intents → context → template/LLM answer.
9. **LLM plumbing** — pluggable `base` / `null` (templates) / `ollama` via factory.
10. **Demo** — synthetic 9-month dataset generator + loader + validation + CLI.
11. **Frontend (V1.1)** — seven sections (Overview · Insights · Expenses ·
    Check-in · Life Events · Assistant · Settings), Evidence drill-down, Data
    Health panel, first-class AI-unavailable state.
12. **Ops** — Docker Compose stack (nginx proxy `:8080`), CI, export + cascading
    deletion.

## V1.2 — multi-user / auth (in progress)

Runs in small verified milestones (M0–M11). Owner reviews each diff and commits
himself; **do not auto-commit**. Stop after each milestone, show diff, wait.

| # | Milestone | Status |
|---|---|---|
| M0 | Record baseline (backend+frontend suites, typecheck, build, demo validate) | ✅ done |
| M1 | Fix check-in edit hydration / data-loss bug (hydrated-gate on edit-submit) | ✅ verified |
| M2 | Auth core: `core/security.py` (Argon2id+JWT), User identity fields, idempotent startup migration, register/login/me, `get_current_user` seam | ✅ done |
| M3 | Flip protected routers to require auth + shared authenticated-client fixture; suite green | ✅ done |
| M4 | Cross-user isolation test suite (`tests/test_isolation.py`) | ✅ done |
| M5 | Profile / onboarding model + endpoints + tracking preferences (JSON cols; drive UI only) | ▶ next |
| M6 | Demo-account separation (`is_demo`) + tests | ⬜ |
| M7 | Frontend auth gate, login/register, cookie-based session client, 401 handling | ⬜ |
| M8 | Frontend onboarding + first-run empty state + preference-driven check-in | ⬜ |
| M9 | "Explore Demo" entry | ⬜ |
| M10 | Docs / ADR amendments (ADR-011 auth, ADR-014 migration, demo-separation note) | ⬜ |
| M11 | Full regression + Docker + live browser flow | ⬜ |

**Locked V1.2 decisions** (owner, 2026-08-14): isolation = service-method
scoping; migration = lightweight idempotent startup migration (no Alembic); demo
= dedicated `is_demo` user; token = short-lived access token only (no refresh
rotation this phase). Full detail in the memory index.

## Definition of done for a milestone

- New behavior is tested; the baseline suite still passes (no regression).
- Typecheck, prod build, and demo-validate stay green where applicable.
- Isolation and safety invariants (Sections 5–7 of [`Rules.md`](Rules.md)) hold.
- Diff shown to the owner; **not** auto-committed.

## Beyond V1.2 (future, not scheduled)

Live bank integrations, goal setting, net worth, multi-turn chat, native mobile —
all explicitly out of current scope. Budgets remain an **unresolved** decision
conflict (PDR-046 vs. shipped read-only budget reporting) →
[`docs/14_Ratification_Briefing.md`](docs/14_Ratification_Briefing.md).
