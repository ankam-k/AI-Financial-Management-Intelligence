# Rules — AI Financial Intelligence Platform

> Boundaries for anyone (human or AI) writing code here. These override
> convenience. When a rule and a shortcut conflict, the rule wins or you STOP and
> report. Detailed rationale lives in the ADRs under
> [`docs/11_Architecture_Decision_Records/`](docs/11_Architecture_Decision_Records/).

## 1. Prime directives

- **This is a production-quality platform, NOT a college CRUD project.** Prioritize
  maintainability in every decision.
- **The analysis engine is the source of truth; the LLM only renders it.** Never
  let a model introduce, alter, or "fix up" a fact.
- **When something looks unsafe (an unscoped query, a destructive migration, a
  gate you'd have to weaken), STOP and report it — do not improvise.**

## 2. Stack & libraries

**Use:** FastAPI · SQLAlchemy · Pydantic · React · TypeScript · Vite.

**Do not add runtime dependencies** without an ADR. Through V1 the backend adds
nothing beyond FastAPI / SQLAlchemy / Pydantic; the frontend adds nothing beyond
React. The only sanctioned additions are the V1.2 auth libs **`argon2-cffi`** and
**`PyJWT`** (mandated by ADR-011). Anything else needs a decision entry first.

## 3. The analysis engine boundary (hard)

- `backend/app/analysis/` **must not perform I/O**: no DB driver, no web
  framework, no HTTP client, no model import. This is enforced by an
  import-parsing test — do not defeat it.
- The engine emits structured `Insight` objects with a `title_key`; it **writes
  no prose**. Rendering is a separate, replaceable step.
- All loading happens in `analysis_service.py`, outside the engine.

## 4. Money & time

- **Money is integer paise.** No floats for currency, ever. → ADR-003
- Time is explicit; use `core/clock.py`, never ad-hoc `datetime.now()` in domain
  logic.

## 5. Statistical integrity (never weaken)

- **Missing habit log = UNKNOWN, never FALSE.** No `BOOLEAN NOT NULL DEFAULT
  FALSE` on check-in habit columns; missing observations are **excluded, never
  imputed**. Three-state semantics: TRUE / FALSE / UNKNOWN. → ADR-007
- **Five gates** must all pass before an insight is shown: ≥8 weeks history, ≥6
  observations per group, ≥60% logging coverage, effect ≥₹500/wk **and** ≥15%,
  Benjamini–Hochberg FDR at q=0.10 over the **full** hypothesis family.
- **No low-confidence tier.** A failed gate suppresses the insight entirely.
- **Determinism:** the same data must produce the same insights.

## 6. LLM safety

- The **prohibited-topic / advice guard** runs **before** any classification or
  model call. Requests to direct capital (investment / tax / insurance / loan
  advice) are refused without reaching a model. → ADR-009, ADR-010
- Generated prose must pass **three validators** — provenance, tier-aware
  lexical, and an independent advice guard. **A rejected generation is discarded
  whole, never repaired.**
- The product must work **fully with the model off** (template fallback), and
  every response must say which path produced it.
- This is an **educational tool, never regulated financial advice.**

## 7. Multi-user isolation (V1.2)

- **Every** user-owned query is scoped by `user.id` at the service-method level.
  Audit every service method and every GET/PATCH/DELETE. If any user-owned query
  is unscoped, **STOP and report** — do not assume it's safe.
- Add explicit cross-user isolation tests for new user-owned resources.
- Demo data lives only under the `is_demo` user. Entering demo must never seed
  demo data into a real account; real accounts start empty.

## 8. Migrations (V1.2)

- Migrations must be **idempotent, non-destructive, explicit, and tested**.
- **Never** use `drop_all`/`create_all` as the migration mechanism. Reset only
  the disposable local dev DB.
- If a migration would become destructive or unsafe, **STOP and report** rather
  than improvising.

## 9. Auth (V1.2)

- Passwords hashed with **Argon2id**. Access token is **short-lived JWT** only
  (no refresh rotation this phase). → ADR-011
- Prefer **HttpOnly + Secure + SameSite cookie** sessions over localStorage
  (same-origin behind the nginx / Vite proxy makes cookies practical).
- Fail closed on a missing/invalid secret.

## 10. Code quality

- **Type hints** everywhere in Python; TypeScript strictness in the frontend.
- **Modular services**; follow **SOLID**; respect the Clean Architecture layering
  (dependencies point inward).
- **Tests are required** for new behavior. Do not regress the baseline suite
  (see `Memory.md`).
- Match the surrounding code's idiom, naming, and comment density.

## 11. Documentation

- Every module documented; **explain tradeoffs**; think like a startup.
- Every requirement traces to a **Product Decisions Record** entry. Content that
  can't cite a decision is removed or raised as an open decision — never left as
  an unmarked assumption.

## 12. Process

- Work in **small, verified milestones**. Stop after each, show the diff, wait.
- **Do not auto-commit** — the owner reviews each diff and commits himself.
- Do not claim work is done unless it's verified; report failures with output.
