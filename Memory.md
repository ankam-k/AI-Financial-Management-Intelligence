# Memory — AI Financial Intelligence Platform

> A living progress log so an AI assistant can pick up context without re-reading
> the whole codebase or inventing state. Update it as work lands. It complements
> (does not replace) the persistent auto-memory index at
> `~/.claude/projects/C--AI-Financial-Intelligence/memory/`, which holds the
> authoritative locked decisions and milestone tracking.

## Where the real detail lives

- **Locked V1.2 decisions:** memory `v12-auth-decisions` (isolation, migration,
  demo, token).
- **Live milestone tracking:** memory `v12-implementation-milestones` (M0–M11).
- **Product decisions:** [`docs/00_Product_Decisions_Record.md`](docs/00_Product_Decisions_Record.md).
- **Companion context files:** [`PRD.md`](PRD.md) · [`Architecture.md`](Architecture.md)
  · [`Rules.md`](Rules.md) · [`Phases.md`](Phases.md) · [`Design.md`](Design.md).

## Current state (as of 2026-08-16)

- **V1 / V1.1: shipped.** Full product loop usable from the UI.
- **V1.2 (multi-user / auth): M0–M9 done; the full flow works end-to-end.**
  Sign up → onboarding → personalised dashboard → data entry → analysis →
  insights → evidence, with per-user isolation and a separate `is_demo` account
  reached by a passwordless "Explore the demo". Verified live via curl on a
  fresh DB. **Remaining:** M10 (docs/ADR amendments) and M11 (Docker rebuild +
  live browser walkthrough — not run yet: Docker daemon down, browser extension
  not connected). Not committed — owner reviews each milestone.

### Baseline to not regress
- Backend: **827 tests passing** (804 + demo-separation/onboarding coverage).
- Frontend: **152 tests** green (141 + Auth/Onboarding), typecheck + `vite build`
  green.
- `python -m app.demo validate` still green; Docker stack builds/runs on `:8080`
  (last verified before V1.2 frontend — re-verify in M11).

### What's done in V1.2
- `core/security.py` — Argon2id hashing + JWT, pure, fail-closed on missing
  secret. Access-token TTL = 720 min. Deps: `argon2-cffi`, `PyJWT`.
- `core/migrations.py` — idempotent, ALTER-based startup migration; proven on a
  real pre-V1.2 dev DB copy. No Alembic; never `drop_all`/`create_all`.
- `User` gains `email` / `password_hash` / `is_demo` + partial unique index.
- Auth service + routes: register / login / logout / me, HttpOnly cookie.
- `api/deps.py`: `require_user` now guards all `CurrentUser` routes; public =
  `auth/*`, `/health`, `demo/*`. (`get_current_user` kept as LEGACY profile seam.)
- `tests/conftest.py`: `anon_client`, `client` (auto-registers User A "Local
  User"), `second_client` (User B).
- `delete_all_data` now **clears owned rows but keeps the account** (Phase 18).
- **Isolation audit PASSED:** every user-owned query scoped by `user.id` across
  the 3 CRUD services + `AnalysisService.build_dataset` (×3 queries) +
  narration/chat via `analysis.run(user)`. Only exception: demo loader's "first
  user" — to be scoped to `is_demo` in M6. `tests/test_isolation.py` = 12 tests.

### Known / open items
- **Dev DB reset pending** — the SQLite file was locked by a running
  `python.exe`; left in place to auto-migrate on restart (backup in scratchpad).
- **Demo loader** still seeds the "first user"; M6 scopes it to `is_demo`.
- **Frontend untouched** by V1.2 so far (auth UI is M7–M9).
- **Budgets conflict unresolved:** PDR-046 excludes budgets, but read-only budget
  reporting shipped → [`docs/14_Ratification_Briefing.md`](docs/14_Ratification_Briefing.md).
- 16 provisional product decisions await owner ratification (PDR §K).

## Next up: M5 — profile / onboarding backend

Add to `user`: `life_stage` / `income_pattern` / `work_context` /
`household_context` + `focus_areas` / `tracked_categories` / `tracked_habits`
(JSON cols) + `onboarding_completed`. Endpoints + migration steps. **Preferences
drive UI prominence only — never analysis thresholds.** Then M6 (demo separation),
M7–M9 (frontend auth / onboarding / Explore-Demo), M10 (ADR amendments), M11
(regression + Docker + browser flow).

## Working agreement (carried from the owner)

- Work in **small verified milestones**; stop after each, show the diff, wait.
- **Do not auto-commit** — the owner reviews and commits each milestone himself.
- Preserve the non-negotiables in [`Rules.md`](Rules.md) (engine purity, integer
  paise, three-state habits, five gates + BH-FDR, no low-confidence tier,
  determinism, safety/advice guard). If anything looks unsafe, **STOP and report.**

## Changelog

- **2026-08-15** — Generated the six companion context files (PRD/Architecture/
  Rules/Phases/Design/Memory). Recorded V1.2 status: M0–M4 done, M5 next.
