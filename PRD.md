# PRD — AI Financial Intelligence Platform

> Concise product requirements for AI-assisted development. The authoritative,
> traceable version lives in [`docs/02_PRD.md`](docs/02_PRD.md); this file is the
> working summary that pairs with `Architecture.md`, `Rules.md`, `Phases.md`,
> `Design.md`, and `Memory.md`.

## 1. What we're building

An **explainable behavioral financial intelligence platform** for young salaried
professionals in India (INR, UPI-first).

Most personal-finance tools tell you *what* you spent. This one tells you what
your spending was **connected to** — and proves it with evidence you can check in
a tap.

> "Food & Dining spending was higher in weeks with no exercise logged."
> `With exercise ₹4,120/wk (7 weeks) · Without ₹5,870/wk (6 weeks) · +42%`
> `Confidence 82% · 5 weeks excluded — no exercise logged those weeks`

This is **not a CRUD app** and **not regulated financial advice**. It is an
educational intelligence tool. It never directs capital.

## 2. Target user

A 24–32 year old salaried professional in an Indian metro who:
- transacts primarily over UPI,
- wants to understand their own financial *behavior*, not just track balances,
- distrusts black-box "AI advice" and wants to see the evidence,
- values privacy (financial data must not leave the deployment).

## 3. Core value proposition

**The analysis engine is the source of truth. The LLM is only a renderer of
truth already established.** Every number a user sees exists in a structured
`Insight` object *before* any model runs. The product works fully with the model
switched off — narration falls back to hand-written templates, and every response
says which one you got.

## 4. Feature scope

### In V1 / V1.1 (built — full loop usable from the UI)
- CSV bank-statement upload with per-bank adapters + synthetic demo data
- Merchant normalization and **explainable** categorization
- Daily habit **check-ins** with three-state semantics (TRUE / FALSE / UNKNOWN)
- **Life event** annotation (job change, move, etc.)
- Statistically **gated** behavioral insights with **evidence drill-down**
- **Data Health** readiness panel (what's missing, what unlocks insights)
- Bounded, single-turn **Q&A assistant** with a prohibited-topic guard
- First-class **AI-unavailable** state
- Full **export** and **cascading deletion**
- Seven-section navigation: Overview · Insights · Expenses · Check-in · Life Events · Assistant · Settings

### In progress (V1.2 — multi-user / auth)
- Real authentication (register / login / me), Argon2id + short-lived JWT
- Per-user data isolation (service-method scoping, cross-user isolation tests)
- Idempotent startup migration (no Alembic yet)
- Dedicated `is_demo` demo account + "Explore Demo" entry
- Profile / onboarding preferences (drive UI prominence only — never thresholds)
- See [`Memory.md`](Memory.md) and the memory index for live milestone status.

### Not in V1 (deliberate)
Live bank integrations · investment / tax / insurance / loan advice (a
**regulatory boundary**, not a feature gap) · goal setting · net worth · native
mobile · peer comparison · multi-turn chat.

**Budgets are an unresolved exception:** PDR-046 excludes them, but read-only
budget reporting was built. See [`docs/14_Ratification_Briefing.md`](docs/14_Ratification_Briefing.md).

## 5. Product principles (non-negotiable)

1. **A day with no habit log means UNKNOWN, never "didn't happen."** Missing
   observations are excluded, never imputed. → ADR-007
2. **Five statistical gates** stand between a detected pattern and a shown insight
   (≥8 weeks history, ≥6 obs/group, ≥60% coverage, effect ≥₹500/wk **and** ≥15%,
   Benjamini–Hochberg FDR at q=0.10). Failure suppresses the insight — **there is
   no low-confidence tier.**
3. **Saying nothing is a designed feature.** Under-claiming costs a session;
   over-claiming costs the user's trust. → PDR-030
4. **Money is integer paise.** Time is explicit. → ADR-003
5. **The LLM can never introduce a fact.** Generated prose passes three
   validators (provenance, tier-aware lexical, advice guard); a rejected
   generation is discarded whole, never repaired.

## 6. Success criteria

- Every shown insight is backed by checkable evidence and survives all five gates.
- The full product loop is usable from the UI with the model **off**.
- No user can read, modify, or delete another user's data (proven by tests).
- Financial data never leaves the deployment; deletion is real and cascading.

## 7. Constraints

- India / INR / UPI-first market framing.
- Local model inference only (privacy). No data used for training or aggregation.
- Backend adds no runtime dependency beyond FastAPI / SQLAlchemy / Pydantic
  except the two auth libs (`argon2-cffi`, `PyJWT`). Frontend adds none beyond React.
- Every requirement must trace to a Product Decisions Record (PDR) entry.
