# Ratification Briefing — the 16 provisional decisions

| Field | Value |
|---|---|
| **Document Name** | 14_Ratification_Briefing.md |
| **Product** | AI Financial Intelligence Platform |
| **Version** | 1.0 |
| **Status** | 🟡 **Review** — awaiting owner ruling |
| **Owner** | Engineering (prepared for the product owner) |
| **Dependencies** | `00_Product_Decisions_Record.md` §K (frozen v1.0) |
| **Traceability** | Every row cites the code that now depends on the decision |
| **Blocks** | Closing V1 |
| **Last Updated** | 2026-07-28 |

---

## Purpose

`PDR §K` asks for one pass confirming or overturning 16 decisions made under
delegated authority. It states blast radius in terms of **documents**, because
it was written before any code existed.

Six sprints have since been built on those decisions. This document restates
the blast radius in terms of **the code and tests that now exist**, so the
ruling is made against what overturning would actually cost today rather than
against a forecast from before implementation.

**Nothing here asks you to re-derive the decisions.** Each row gives the
decision, where it now lives, the measured cost of reversing it, and a
recommendation. The expected outcome is thirteen confirmations, and three
items that need something other than a yes or no.

## How to read the cost column

"Tests" counts tests that assert the decision directly — they would fail, not
merely need updating. It is a floor, not a total: a decision can also be wrong
in ways no test covers.

---

## 1. Three items that need a ruling, not a tick ⚠️

These cannot be resolved by confirming the decision as written, because the
built product and the frozen text disagree.

### 1.1 PDR-046 excludes budgets. The product has budgets. ⚠️

**The conflict.** PDR-046 lists as a V1 non-goal:

> *Budgets, envelopes, spending limits — constraint-setting is a different
> product philosophy from explanation (PDR-008). Doing both makes us mediocre
> at each.*

Sprint 2's brief asked for "Budget utilization" and "Budget usage" as required
analytics. I built them: `user.monthly_budget_paise`, the
`BUDGET_UTILIZATION` insight with `WITHIN_BUDGET`/`NEAR_LIMIT`/`OVER_BUDGET`
status, a `BudgetProgress` card on the dashboard, and a `BUDGET_STATUS` chat
intent.

**I did not flag this at the time. I should have** — the sprint brief and a
frozen product decision contradicted each other, and I followed the brief
without saying so.

**What is actually built is narrower than what PDR-046 excludes.** The product
reports usage against a figure the user typed. It sets no limits, blocks no
spending, sends no alerts, and suppresses the insight entirely when no budget
is set. That is arguably explanation-of-a-user-supplied-reference rather than
constraint-setting — but that is a product judgement, and it is yours.

| Option | Cost |
|---|---|
| **(a) Amend PDR-046** to permit read-only budget reporting, excluding envelopes, limits and alerts | Documentation only. Code unchanged. **Recommended** |
| (b) Confirm PDR-046 as written and remove the feature | 1 schema column, 1 insight type, 1 dashboard card, 1 chat intent, ~30 tests, and the demo dataset's budget-warning demonstration |

### 1.2 PDR-036 was implemented more strictly than written

PDR-036 permits causal language "only for arithmetic decomposition". T2 period
comparisons are arithmetic, so a literal reading exempts them.

I exempted T2 initially. Running `qwen2.5:7b` against a real monthly comparison
produced *"this increase could be due to seasonal changes or specific events"* —
fluent, plausible, and entirely absent from the input. A comparison establishes
*that* spending moved, never *why*, so there was nothing for a causal clause to
be true about. **Only T1 is exempt in the shipped code** (ADR-016).

| Option | Cost |
|---|---|
| **(a) Confirm the narrowing** — amend PDR-036 to "T1 arithmetic decomposition only" | Documentation only. Matches shipped behaviour. **Recommended** |
| (b) Restore the literal reading | Re-exempts T2; the model will speculate about causes again. 26 tests |

### 1.3 PDR-047's ranking formula is two-thirds implemented

PDR-047 specifies `effect size × confidence × novelty`, capped at 5 insights.

The cap is implemented (`GateConfig.max_relationships = 5`). Ranking is by
effect size then significance. **Novelty is not implemented**, because it
requires knowing which insights the user has already seen, and V1 does not
persist insights (ADR-015).

| Option | Cost |
|---|---|
| **(a) Confirm with novelty deferred**, recorded as dependent on insight persistence | Documentation only. **Recommended** |
| (b) Require novelty in V1 | Insight persistence, an acknowledgement store, and a similarity measure — a sprint |

---

## 2. The four ⭐ high-impact decisions

### PDR-040 — an unlogged day means UNKNOWN ⭐

**Decision.** A day with no check-in is UNKNOWN, never "the habit did not
occur". Complete-case analysis; 60% per-habit coverage floor.

**Where it lives now.** Six nullable habit columns with **no `DEFAULT`**;
per-habit exclusion in every weekly aggregation; `observations.excluded_unknown`
on every insight; the denominators in habit analytics; the negative-control
design in the demo dataset.

**Cost to overturn: 25 tests, and a data migration that cannot be undone.**
This is the one decision where reversal is not symmetric. Adding
`DEFAULT FALSE` would silently convert every historical "didn't log" into
"didn't happen" — a dataset whose damage is invisible and permanent, because
every individual row stays perfectly traceable while every aggregate becomes
wrong. Three separate test classes exist solely to make this fail a build.

**Recommendation: confirm.** If any single decision here is worth the pass, it
is this one.

### PDR-043 — five statistical gates ⭐

**Decision.** ≥8 weeks history, ≥6 observations per group, ≥60% coverage,
effect ≥₹500/week **and** ≥15%, Benjamini–Hochberg FDR at q=0.10.

**Where it lives now.** `app/analysis/gates.py` as a frozen config; the whole
of `relationships.py`; the demo dataset is built to survive them and asserts
zero false positives on negative controls.

**Cost to overturn: 41 tests.** Thresholds are parameters, so *tuning* them is
a config change. Removing a gate is not: 84 hypotheses run per analysis, of
which roughly four clear α=0.05 by chance alone. Without G5 the product ships
false findings by construction.

**Recommendation: confirm.** Tune thresholds freely; keep all five gates.

### PDR-037 — bounded, single-turn Q&A ⭐

**Decision.** Single-turn only. Not open conversation, not zero Q&A.

**Where it lives now.** Enforced by *absence*: no `conversation_id`, no history
field, no server-side memory. The request schema rejects both as unknown
fields.

**Cost to overturn: 135 tests** — but the direction matters. Reducing to zero
Q&A deletes a working subsystem. Expanding to multi-turn is additive and
mostly new work, not rework: conversation state, a context window strategy,
and re-validating the guard against pronoun-laden follow-ups (*"and that
one?"* after a refused question is a real bypass risk).

**Recommendation: confirm for V1.** The visible cost is that *"what about
groceries?"* cannot work, and the UI says so rather than letting a user
discover it.

### PDR-038 — six fixed habits ⭐

**Decision.** A fixed set of six habits; no user-defined habits in V1.

**Where it lives now.** `CheckIn.HABIT_FIELDS`, six schema columns, the
hypothesis space, the test-selection map, the coverage table.

**Cost to overturn: 25 tests, plus the thing the rationale names.** A
user-defined habit set makes the hypothesis count unbounded and per-user,
which defeats any fixed multiplicity correction — so PDR-038 is load-bearing
for PDR-043 rather than merely adjacent to it. Overturning one requires
re-opening the other.

**Recommendation: confirm.**

---

## 3. The remaining nine

| PDR | Decision | Where it lives now | Cost | Recommend |
|---|---|---|---|---|
| **PDR-039** | Daily check-in, partial allowed, 30-day backfill | `uq_checkin_user_date`; backfill check against the injected clock | 18 tests | **Confirm** — but see the note below |
| **PDR-042** | Life events: 7 types, date range, notes | `life_event` table, event analytics, timeline | 37 tests | **Confirm** |
| **PDR-041** | Insights pause below the coverage floor; deterministic analysis unaffected | Gate G3 + `DATA_SUFFICIENCY` notices | 4 tests | **Confirm** |
| **PDR-032** | Confidence mandatory on inference, omitted on arithmetic | `Insight.__post_init__` rejects both violations | 9 tests | **Confirm** |
| **PDR-033** | Hard cascading deletion | `ON DELETE CASCADE` + SQLite pragma; asserted table by table | 3 tests | **Confirm** |
| **PDR-034** | No training, no cross-user aggregation, no sharing | Nothing built that could violate it; local inference only | 0 | **Confirm** — free |
| **PDR-035** | Multi-user authenticated accounts | **Not implemented.** ADR-014 deferred it; V1 is one local profile | 0 | **Confirm as a V2 target**, or restate as V1 single-user |
| **PDR-044** | Three-way insight feedback; "isn't true" = defect report | **Not implemented.** Needs insight persistence | 0 | **Confirm as deferred** |
| **PDR-045** | North Star: Trust Rate ≥70%, False Insight Rate <5% | **Not implemented.** No instrumentation exists | 0 | **Confirm, noting it is currently unmeasurable** |

### Note on PDR-039 — the 30-day backfill is the OEQ-004 conflict

Confirming PDR-039 keeps a known tension: the 30-day cap means a **real** user
cannot reach a behavioural insight inside their first month, because gates G1
and G3 need more history than they are allowed to backfill. Sprint 6 closed
this for demonstration purposes by writing synthetic data below the API; it did
not, and could not, close it for real users.

That is PDR-030 working as designed — insight is earned, not assumed. It is
worth confirming deliberately rather than by omission.

---

## 4. What ratification does not settle

Four decisions above (PDR-035, 044, 045, and the novelty half of 047) describe
behaviour **no code implements**. Ratifying them confirms an intention, not a
tested design. Each will need its own review when built — PDR-045 in
particular, since a North Star metric that nothing measures cannot yet be shown
to be the right one.

---

## 5. Ruling

| PDR | Ratify | Overturn | Amend |
|---|---|---|---|
| PDR-040 ⭐ | ☐ | ☐ | ☐ |
| PDR-043 ⭐ | ☐ | ☐ | ☐ |
| PDR-037 ⭐ | ☐ | ☐ | ☐ |
| PDR-038 ⭐ | ☐ | ☐ | ☐ |
| PDR-039 | ☐ | ☐ | ☐ |
| PDR-042 | ☐ | ☐ | ☐ |
| PDR-041 | ☐ | ☐ | ☐ |
| PDR-032 | ☐ | ☐ | ☐ |
| PDR-033 | ☐ | ☐ | ☐ |
| PDR-034 | ☐ | ☐ | ☐ |
| PDR-035 | ☐ | ☐ | ☐ |
| PDR-044 | ☐ | ☐ | ☐ |
| PDR-045 | ☐ | ☐ | ☐ |
| **PDR-046** ⚠️ | ☐ | ☐ | ☐ §1.1 |
| **PDR-036** ⚠️ | ☐ | ☐ | ☐ §1.2 |
| **PDR-047** ⚠️ | ☐ | ☐ | ☐ §1.3 |

**Ruled by:** ______________________  **Date:** ______________________

On ruling, `00_Product_Decisions_Record.md` is amended per its §G append-only
rule — the frozen v1.0 text is not edited, and a numbered amendment records the
outcome. The 🟠 markers throughout the documentation set are then cleared for
every confirmed decision.
