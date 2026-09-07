# AI Architecture

| Field | Value |
|---|---|
| **Document Name** | 07_AI_Architecture.md |
| **Product** | AI Financial Intelligence Platform |
| **Version** | 1.0 |
| **Status** | 🟢 **Approved** |
| **Owner** | AI Engineering |
| **Dependencies** | `03_SRS.md` v1.0 · `04_System_Architecture.md` v1.0 · ADR-007, ADR-008, ADR-009, ADR-010 |
| **Traceability** | Every component cites its SRS requirement. See §10. |
| **Blocks** | Implementation |
| **Lifecycle stage** | Draft → Review → **Approved** → Frozen → Superseded |
| **Last Updated** | 2026-07-27 |

---

## Purpose

To specify how the system produces trustworthy behavioral intelligence — the analysis engine that establishes truth, the gates that decide what may be said, and the strictly-bounded role the language model plays.

## Scope

**In scope:** analysis engine design, statistical pipeline, insight construction, LLM contract, validation, refusal handling, degraded mode, evaluation.

**Out of scope:** schema (→ `05`), endpoint shapes (→ `06`), test implementation (→ `09`).

## Assumptions

**None.** Every design element traces to an SRS requirement or an ADR.

## References

`03_SRS.md` · ADR-007 (statistics) · ADR-008 (serving) · ADR-009 (validation) · ADR-010 (guard)

## Related Documents

`docs/INDEX.md` · `05_Database_Design.md` · `06_API_Design.md` · `09_Testing_Strategy.md`

---

## 1. The governing principle

> **The analysis engine is the source of truth. The LLM is a renderer of truth already established. (PDR-031, SRS-7.1)**

Everything in this document follows from that sentence, and from one architectural fact that makes it real rather than aspirational:

**The analysis engine lives in `domain/`, which cannot perform I/O (ADR-001).** It is *structurally incapable* of calling a model. PDR-031 is not a coding convention anyone can forget — it is a property of the dependency graph, enforced in CI.

```
   Transactions    Check-ins    Life Events
        └──────────────┼──────────────┘
                       ▼
        ╔══════════════════════════════════╗
        ║  ANALYSIS ENGINE  (pure domain)  ║  ← truth is established here
        ║  no I/O · no model · no network  ║
        ╚══════════════════════════════════╝
                       ▼
              Structured Insight              ← complete and displayable
                       │                         BEFORE any model runs
          ┌────────────┴────────────┐
          ▼                         ▼
    LLM narration            Template renderer
          │                         │
    [validators]                    │           ← ADR-009
     pass │ fail ──────────────────▶│
          ▼                         ▼
       Prose                Deterministic prose
```

The insight is finished before generation begins. That is what makes discarding a bad generation cost nothing but prose quality.

## 2. Analysis engine

Four stages, all pure and deterministic (SRS-9.1).

### 2.1 Signals — T1

Deterministic aggregations over the ledger: per-week and per-category totals, medians, counts; merchant frequencies; period-over-period deltas.

Signals are **exact arithmetic**. They carry no confidence (SRS-2.1, PDR-032🟠) and may use causal language where the claim is an accounting identity (PDR-036🟠) — *"Your total rose ₹40,000 because an annual premium was debited on 12 June"* is provable by summation and therefore permitted.

### 2.2 Rules — T2

Threshold-based detection with stated parameters: recurring transactions by periodicity and amount stability (SRS-4.6), subscription discovery, dormant-subscription detection, category spikes against the user's own baseline.

T2 claims are deterministic and verifiable by inspection. The detection thresholds are recorded on the insight so the claim is auditable.

### 2.3 Statistics — T3

The behavioral core. Implements ADR-007.

**Hypothesis space:** 6 habits × 15 categories, less `TRANSFERS` and `INCOME` → **≈78–90 hypotheses per run**. This number is the reason multiplicity correction is mandatory rather than optional.

**Unit of observation:** the ISO week. Weekly aggregation suits the habit/spending relationship and matches how the persona experiences routine.

**Test selection (ADR-007):**

| Habit type | Habits | Test |
|---|---|---|
| Binary | `exercise`, `alcohol` | Mann–Whitney U on weekly category spend |
| Ordinal | `stress_level`, `home_cooked_meals` | Spearman rank correlation |
| Numeric | `sleep_hours` | Spearman rank correlation |
| Categorical | `work_mode` | Kruskal–Wallis across the three levels |

Non-parametric throughout: weekly spending is right-skewed with heavy tails (one wedding, one flight), and n is small. Parametric assumptions do not hold.

### 2.4 Missing data handling ⭐

**The single most important computation in the engine (SRS-5.5, SRS-6.3, PDR-040🟠).**

```
For each week in the analysis window:
    For each habit:
        observations ← check-ins in that week with a NON-NULL value for THAT habit
        if none        → week is UNKNOWN for that habit → EXCLUDED
        else           → aggregate the recorded values

NEVER:  coalesce NULL → false / 0
NEVER:  impute (mean, mode, multiple, or otherwise)
NEVER:  treat a missing check-in as a recorded negative
```

`HabitValue` is a sum type — `Unknown | Recorded(T)` — so analysis code **cannot read a habit value without handling `Unknown`**; the type system refuses the alternative (ADR-007). This is why the invariant survives future contributors.

**Coverage is per-habit, not per-row (SRS-6.2).** A user may log sleep daily and exercise rarely; a single `check_in` row containing only `sleep_hours` provides zero coverage for `exercise`.

**Excluded counts are recorded and surfaced** on every insight (SRS-6.4) — the user sees how much data was set aside.

### 2.5 The five gates

```
   candidate association
          │
    ┌─────▼─────┐  G1  history ≥ 8 weeks
    ├───────────┤  G2  n ≥ 6 in EACH compared group
    ├───────────┤  G3  per-habit coverage ≥ 60%
    ├───────────┤  G4  |Δ| ≥ ₹500/week AND ≥ 15% relative
    ├───────────┤  G5  BH-FDR q = 0.10 across ALL hypotheses in the run
    └─────┬─────┘
     pass │ fail → SUPPRESSED ENTIRELY (never downgraded)
          ▼
      Insight + Evidence
```

**Gate order is deliberate.** G4 (effect size) precedes G5 (significance), so a statistically detectable but financially trivial difference is discarded before it consumes an FDR slot. Significance is necessary, never sufficient.

**Failure suppresses; it never downgrades.** There is no "low-confidence insight" tier — a claim that fails a gate is not shown at all (SRS-6.1). When G1 or G3 fails, a Data Sufficiency Notice is emitted instead (SRS-6.11).

### 2.6 Stability and ranking

New T3 insights are `TENTATIVE`; promotion to `ESTABLISHED` requires passing all gates again in a subsequent, non-identical window (SRS-6.7).

Ranking: `effect_size × confidence × novelty`, capped at **5** per period (SRS-6.10). Novelty penalizes insights substantially similar to ones already shown and acknowledged.

## 3. Insight structure

The structured object is the truth. Prose is a view of it.

```json
{
  "tier": "T3",
  "claim": {
    "habit": "exercise", "category": "FOOD_DINING",
    "group_a": { "label": "weeks with exercise", "n": 7, "median_paise": 412000 },
    "group_b": { "label": "weeks without exercise", "n": 6, "median_paise": 587000 },
    "difference_paise": 175000, "relative_difference": 0.4247
  },
  "statistics": { "test": "mann_whitney_u", "p_value": 0.0231,
                  "q_value": 0.0840, "hypotheses_tested": 90 },
  "observations": { "included": 13, "excluded_unknown": 5, "coverage_ratio": 0.72 },
  "confidence": 0.82,
  "evidence_refs": ["txn:...", "checkin:...", "..."]
}
```

**Every number the user will ever see exists here before the model runs.** This is what makes ADR-009's provenance validator possible: the validator has an authoritative set to check against.

## 4. LLM contract

### 4.1 What the model receives

**Only the structured insight object.** Never raw transactions, never the ledger, never the database (SRS-7.2).

### 4.2 What the model may do

Convert the object into clear, warm, second-person English. Nothing else.

### 4.3 Instruction constraints

The system prompt states: use only supplied numbers; invent nothing; use correlational language (*associated with, correlated with, observed during, tended to occur alongside*); never write *because*, *caused*, *due to*, *led to* for a T3 claim; never recommend any financial product; never state a number absent from the input.

**These instructions are not the enforcement mechanism.** They improve first-pass quality. Enforcement is §5 — because a prompt is a request, and PDR-002's production bar does not accept a request as a control.

### 4.4 Output constraint

JSON-schema-constrained generation (ADR-008) into `{ "headline": string, "body": string }` — bounding the surface the validators must check.

## 5. Validation

Two independent, deterministic validators. Failure **discards**; it never repairs (ADR-009).

### 5.1 Provenance validator (SRS-7.3)

Extracts every numeric literal from generated text and asserts set-membership against the input payload, with normalization for formatting (₹4,120.00 ≡ 412000 paise ≡ "4,120"). **Any number not in the input fails the generation.**

This is the mechanism that makes PDR-031's "must not fabricate numerical results" enforceable rather than merely stated.

### 5.2 Lexical validator (SRS-7.4)

Rejects causal connectives — *because, caused, due to, led to, resulted in, made you, drove* — in **T3** content. T1 arithmetic claims are exempt per PDR-036🟠, so the validator is tier-aware rather than global.

### 5.3 Fallback (SRS-7.5, SRS-7.6, NFR-7)

On failure of either validator, on timeout, or on model unavailability, the system renders the same structured insight through a **hand-written template**.

**Template quality is a real deliverable, not a stub.** It is what users see whenever validation fails, and the product must be fully usable with the model absent. Nothing factual is lost — only fluency.

## 6. Q&A subsystem

Bounded, single-turn (PDR-037🟠, SRS-7.7).

```
question
   │
   ▼
[ProhibitedTopicGuard]  ────▶ REFUSED (PROHIBITED_TOPIC)
   │ pass                      ← never reaches the model (ADR-010)
   ▼
[Intent → capability map] ───▶ REFUSED (NOT_ANSWERABLE_FROM_ANALYSIS)
   │ matched
   ▼
[Fetch structured outputs from the engine]
   │
   ▼
[LLM renders answer]  →  [validators]  →  answer | template fallback
```

**The guard runs first**, so prohibited content is never generated, never logged, never cached (ADR-010). It is an independently testable component with no model dependency (SRS-7.10).

The permitted/prohibited boundary is PDR-027's: **describing the user's own recorded history is always permitted; directing future capital allocation is always refused.** *"How much did I pay in loan EMIs last quarter?"* is a factual query about the user's own data and is answered; *"Should I switch to a cheaper loan?"* is refused.

**No conversation state exists** — no `conversation_id`, no history, no server-side turn memory. The absence is the enforcement of single-turn (SRS-7.7).

Ambiguity resolves to refusal. A false refusal costs a session; a false answer is a regulatory event.

## 7. Determinism

| Source of non-determinism | Control |
|---|---|
| Wall-clock time | Injected `ClockPort`; the run's timestamp is persisted (ADR-003) |
| Model sampling | Model output affects prose only, never claims or numbers |
| Any randomized procedure | Fixed seed (SRS-6.9) |
| Categorization | Deterministic layered resolution (ADR-005, SRS-4.5) |
| Floating point in money | Integer paise throughout (ADR-003) |

**Given fixed data and a fixed clock, the engine produces byte-identical claims across runs (SRS-9.1).** Prose may vary; truth may not.

## 8. Evaluation

Insight quality is measured, not asserted.

**Ground truth (SRS-3.18, SRS-3.19):** synthetic datasets carry both **planted patterns** and **negative controls** — habit/category pairs with no relationship.

| Metric | Target | Why |
|---|---|---|
| **False positive rate on negative controls** | **0 T3 insights** | The primary defense. More important than recall. |
| Recall on planted patterns | High | Detects patterns that genuinely exist |
| Provenance validation failure rate | Tracked | Rising = prompt or model regression |
| Lexical validation failure rate | Tracked | Rising = causal-language drift |
| Guard block accuracy | Tracked | Both false negatives and over-blocking |
| Template fallback rate | Tracked | High = model or prompt problem |

**In production**, PDR-045🟠's Insight Trust Rate (≥70%) and False Insight Rate (<5%) are computed from `insight_feedback` (SRS-10.5, SRS-10.6).

**If gates prove too strict and insights too rare, the correct response is lengthening the analysis window — not loosening the gates (ADR-007).** Under-claiming costs a session; over-claiming costs the user.

## 9. Failure modes

| Failure | Behavior | Requirement |
|---|---|---|
| Model unavailable | Template rendering; product fully usable | SRS-7.6, NFR-7 |
| Generation timeout | Template rendering | ADR-009 |
| Provenance validation fails | Discard; template rendering; log | SRS-7.3 |
| Lexical validation fails | Discard; template rendering; log | SRS-7.4 |
| Insufficient data | Data Sufficiency Notice, HTTP 200 | SRS-6.11, PDR-030 |
| Coverage drops below floor | Behavioral insights pause; T1/T2 unaffected | SRS-6.12, SRS-6.13 |
| Prohibited question | Refusal before the model | SRS-7.9 |
| Question outside capability | Refusal; no best-effort answer | SRS-7.8 |

**No failure mode produces a wrong number.** Every path degrades toward silence or toward plainer language — never toward a confident guess.

## 10. Traceability

| Section | SRS | PDR / ADR |
|---|---|---|
| §1 Engine as source of truth | SRS-7.1, 7.2 | **PDR-031**, ADR-001 |
| §2.1–2.2 T1/T2 | SRS-2.1, 4.6 | PDR-032🟠, PDR-036🟠 |
| §2.3 Test selection | SRS-6.1 | ADR-007 |
| **§2.4 Missing data** | **SRS-5.5, 6.2, 6.3, 6.4** | **PDR-040🟠, ADR-007** |
| §2.5 Five gates | SRS-6.1, 6.5, 6.11 | PDR-030, **PDR-043🟠** |
| §2.6 Stability, ranking | SRS-6.7, 6.10 | PDR-043🟠, PDR-047🟠 |
| §3 Insight structure | SRS-2.5 | **PDR-017** |
| §4 LLM contract | SRS-7.2, 7.4 | PDR-028, PDR-031, ADR-008 |
| §5 Validation | SRS-7.3 … 7.6 | **PDR-017**, ADR-009 |
| §6 Q&A + guard | SRS-7.7 … 7.10 | **PDR-027**, PDR-037🟠, ADR-010 |
| §7 Determinism | SRS-9.1, 6.9 | ADR-003 |
| §8 Evaluation | SRS-3.18, 3.19, 10.5, 10.6 | PDR-012, PDR-045🟠 |
| §9 Failure modes | SRS-6.11 … 6.13, 7.6 | PDR-030, NFR-7 |
