# ADR-009 — Provenance and lexical validation with deterministic template fallback

**Status:** Accepted · **Date:** 2026-07-27 · **Serves:** SRS-7.3 … 7.6, PDR-017, PDR-028, PDR-031, NFR-7 · **Closes:** D-20, D-21

## Decision

Every generated string passes two independent validators before display:

1. **Provenance validator** — every numeric literal in the output must appear in the structured input payload.
2. **Lexical validator** — no causal connective may appear in T3 content.

Output failing either validator is **discarded, not repaired**. The system falls back to deterministic template rendering of the same structured insight.

## Context

PDR-031 states the LLM "must not fabricate numerical results or unsupported behavioral conclusions," and PDR-017 requires every insight to trace to stored records. **Both state a rule; neither states a mechanism.** A prompt instruction is not an enforcement mechanism — it is a request. D-20 exists precisely because stating the rule is not enforcing it.

PDR-028 mandates correlational language. A 7B model (ADR-008) will occasionally write "because" when handed a correlation, no matter how the prompt is worded.

## Alternatives

**A. Prompt instruction only.** Zero infrastructure. Rejected: unenforceable and untestable. It converts a correctness requirement into a hope, and PDR-002's production-quality bar excludes that.

**B. Human review.** Impossible at runtime.

**C. LLM-as-judge validating the generation.** Catches semantic drift a regex cannot. But it is itself non-deterministic, doubles latency and cost, and makes a fallible component the guardian of another fallible component. Rejected as the primary gate; viable later as an *additional* layer.

**D. Deterministic post-generation validators + fallback.** Mechanical, fast, fully testable. Catches fabricated numbers and prohibited phrasing exactly. Cannot catch subtle semantic misrepresentation that invents no number and uses no banned word.

**E. Constrained decoding / template-only, no free generation.** Maximum safety, zero fabrication risk. But it discards the quality-of-language benefit that motivated including a model at all.

## Tradeoffs

| Gain | Cost |
|---|---|
| Fabricated numbers are mechanically impossible to display | Validators cannot catch semantic drift with no number and no banned word |
| Causal-language violations caught deterministically (SRS-7.4) | Lexical list needs curation; false positives discard valid prose |
| System functions with the model absent or failing (NFR-7) | Two rendering paths to maintain and test |
| Both validators are unit-testable without a model | Occasional fallback means inconsistent prose quality |
| Rejecting rather than repairing keeps failure modes simple | Discards work; no partial-credit recovery |

## Final Choice

**D — deterministic validators with template fallback**, layering **E** as the fallback path.

The design principle: **the model is a renderer whose output is disposable.** Because the structured insight is complete and displayable before generation begins, discarding a bad generation costs nothing but prose quality. This is what makes "reject, never repair" affordable — and repair loops are where subtle corruption creeps in.

C (LLM-as-judge) is explicitly deferred rather than dismissed: it is the right next layer once the deterministic gates are in place and measured.

## Consequences

- Every insight has a hand-written template rendering. Template quality is a real deliverable, not a stub — it is what users see whenever validation fails.
- The provenance validator extracts numerals from generated text and asserts set-membership against the input payload, with tolerance rules for formatting (₹1,200 vs 1200) defined once and tested.
- The lexical validator holds a curated connective list ("because", "caused", "due to", "led to", "resulted in", "made you") applied to T3 content only — T1 arithmetic claims may legitimately use causal phrasing per PDR-036🟠.
- Validation failures are logged with the generation, and the failure rate is a tracked quality metric.
- SRS-10.8 asserts every number in prose exists in structured input; SRS-10.7 asserts no T3 string contains a causal connective; SRS-10.12 asserts the product works with the model unavailable.
- If the failure rate is high, the response is improving prompts or templates — **never** relaxing a validator.
