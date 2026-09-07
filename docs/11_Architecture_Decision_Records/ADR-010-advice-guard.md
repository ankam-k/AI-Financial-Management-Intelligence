# ADR-010 — Independent prohibited-topic guard for the Q&A surface

**Status:** Accepted · **Date:** 2026-07-27 · **Serves:** **PDR-027**, PDR-037🟠, SRS-7.9, SRS-7.10 · **Closes:** D-28

## Decision

Every user question passes an **independent, deterministic guard** before reaching the model. The guard blocks the seven PDR-027 prohibited domains and returns a fixed refusal. It is a separately testable component, not a prompt instruction.

## Context

PDR-027 prohibits any recommendation involving stocks, mutual funds, ETFs, insurance, loans, tax planning, or investment products. PDR-037🟠 permits single-turn Q&A. Together these create a runtime exposure that did not previously exist: **a user can simply ask.** *"Should I put my surplus in an ELSS fund?"* is a natural question for exactly the persona in PDR-006.

A design-time prohibition does not survive contact with an open input field. SRS-7.10 therefore requires the guard not to rely solely on model instruction.

## Alternatives

**A. System-prompt instruction only.** Cheap. Rejected by SRS-7.10 explicitly, and rightly: prompt instructions are probabilistic, bypassable by rephrasing, and untestable as a compliance control. For a regulatory boundary, that is the wrong class of mechanism.

**B. Keyword blocklist.** Deterministic, fast, trivially testable. Brittle: misses paraphrase ("where should I park my savings for growth?") and over-blocks legitimate questions ("how much did I spend on my car loan EMI last month?" — a factual T1 question about the user's own transactions that mentions a prohibited term).

**C. Intent classifier (small local model).** Handles paraphrase. Non-deterministic, needs training data, and makes a probabilistic component the regulatory gate.

**D. Layered: normalized keyword/pattern matching + intent heuristics, with an allowlist for factual questions about the user's own data.** Deterministic core, targeted handling of the over-blocking failure mode.

**E. Answer-side filtering (let the model answer, then filter).** Rejected: the prohibited output would already exist, and any logging or streaming leaks it.

## Tradeoffs

| Gain | Cost |
|---|---|
| Deterministic and fully testable as a compliance control | Cannot catch every paraphrase; sophisticated rephrasing may pass |
| Blocks before generation — prohibited content is never produced | Over-blocking risk on legitimate questions mentioning loans/insurance |
| Independent of the model; survives a model swap (ADR-008) | Pattern list needs curation and periodic review |
| Allowlist preserves factual questions about the user's own data | Two-stage logic is more complex than a flat blocklist |

## Final Choice

**D — layered deterministic guard with a factual-question allowlist.**

The allowlist resolves B's central weakness. The distinguishing test mirrors PDR-027's own boundary:

| Question | Verdict | Why |
|---|---|---|
| "How much did I pay in loan EMIs last quarter?" | **Allowed** | Factual T1 query about the user's own recorded transactions |
| "Is my insurance premium higher than last year?" | **Allowed** | Factual comparison over the user's own data |
| "Should I switch to a cheaper loan?" | **Blocked** | Recommendation involving a financial product |
| "Where should I invest my surplus?" | **Blocked** | Investment recommendation |

The rule: **describing the user's own recorded history is always permitted; directing future capital allocation is always refused.**

Residual paraphrase risk is accepted and mitigated by refusal defaulting — ambiguous questions are refused rather than answered, because a false refusal costs a session while a false answer is a regulatory event.

## Consequences

- The guard is a standalone module with no model dependency, unit-tested against a corpus of phrasings per prohibited category (SRS-10.9).
- The refusal is fixed text explaining the product's scope and does **not** attempt a partial answer or a hedged version.
- Blocked questions are logged (category only, never content) so the pattern list can be improved from real misses.
- The guard runs before the model, so prohibited content is never generated, never logged, never cached.
- Ambiguity resolves to refusal — a deliberate asymmetry.
- If PDR-037🟠 is overturned to reading (a) (no Q&A in V1), this ADR reduces to design-time review only and the runtime component is unnecessary.
