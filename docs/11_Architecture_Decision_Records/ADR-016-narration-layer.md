# ADR-016 — Narration V1: five sections, code-rendered confidence, template-first

**Status:** Accepted · **Date:** 2026-07-28 · **Serves:** PDR-031, SRS-7.1 … 7.6 · **Implements:** ADR-008, ADR-009, ADR-010

## Decision

Six decisions taken while building the AI Insight Generator (Sprint 3):

| # | Decision |
|---|---|
| 1 | Output is **five sections** — Observation, Evidence, Interpretation, Confidence, Suggestion — not ADR-009's `{headline, body}`. |
| 2 | **Confidence is rendered by code, never by the model.** The output schema has no confidence field. |
| 3 | **Template-first.** The deterministic renderer runs for every insight; generation is an upgrade that must pass validation to be used. |
| 4 | **Three validators, all run, all failures collected.** Provenance, tier-aware lexical, and an independent advice guard. |
| 5 | The lexical causal ban applies to **T2 and T3**. Only T1 is exempt. |
| 6 | Ollama over **`urllib`**, not `httpx`. No runtime dependency is added. |

## Context

`07_AI_Architecture.md` §4–5 fixes the contract: the model receives only the structured insight, output is JSON-schema-constrained, two deterministic validators check the result, and failure falls back to a hand-written template. What it does not fix is the shape of the explanation or where the confidence figure comes from — and Sprint 3's brief specified a five-section explainable format that ADR-009's `{headline, body}` cannot express.

## Alternatives

**1. `{headline, body}` versus five sections.** The two-field shape is smaller and easier to validate. But the product's claim is that a user can check a finding, and "Observation / Evidence / Interpretation / Confidence / Suggestion" makes the evidence and the hedge structurally present rather than buried mid-paragraph. It also gives the validators named fields to reason about: the causal rule applies to interpretation, the hedging rule to suggestion. This **supersedes ADR-009 §4.4's output shape**; every other part of ADR-009 stands.

**2. Model-authored confidence versus code-rendered.** The brief says the model must not fabricate confidence values. A validator could check any figure it produced against the insight — but the stronger control is to never ask. The output schema has no confidence property, so there is no field for a fabricated number to occupy, and the sentence a user reads is derived from the insight's own tier and q-value. Not asking beats checking.

**3. Generation-first with template fallback, versus template-first.** Functionally similar; the ordering matters for failure. Rendering the template first means the fallback value already exists when a generation is rejected, so no path produces a partial object or a 500. It also makes the template the thing under test rather than an emergency route nobody exercises.

**4. Two validators versus three.** ADR-009 specifies provenance and lexical. ADR-010 specifies an independent prohibited-topic guard, which in the Q&A subsystem runs *before* the model. There is no user question to screen here, so the guard runs on output instead — and independently, so a generation that already failed provenance is still checked and the recorded reason is complete. A fourth shape check rejects stub sections.

**5. Which tiers may use causal language.** ADR-009 §5.2 exempts T1 per PDR-036🟠 and constrains T3. T2 is unspecified, and it was initially exempted by analogy — both are arithmetic. **Running qwen2.5:7b against a real monthly comparison refuted that**: it produced *"this increase could be due to seasonal changes or specific events"* — fluent, plausible, and entirely absent from the input. A T1 signal carries its largest contributing expenses as evidence, so *"your total rose because a ₹40,000 premium was debited"* is provable by summation. A T2 comparison establishes *that* spending moved and never *why*, so there is nothing for a causal clause to be true about. **Only T1 is exempt.**

**6. `httpx` versus `urllib`.** The request is one blocking POST to loopback from a sync route. An async client would add a dependency and a thread-pool bridge to buy nothing.

## Tradeoffs

| Gain | Cost |
|---|---|
| Evidence and hedging are structurally present, not buried in prose | Diverges from ADR-009's documented output shape |
| No field exists for a fabricated confidence figure | Confidence prose is uniform across insights of a tier — a template, not writing |
| No failure path produces a partial object or a 500 | Every insight costs a template render even when generation succeeds |
| A rejection reason is complete, not first-hit | Three validators run on every generation |
| T2 speculation is caught | Lower acceptance rate; more narrations are templates |
| Zero new runtime dependencies | Blocking I/O; concurrent generation would need revisiting |

## Final Choice

**Template-first, generation as a reviewable upgrade.**

`app/narration/` performs no I/O and imports no adapter — the model client arrives through the `LLMClient` protocol, so the prompt builder, the validators and the templates are all testable without a model. `tests/analysis/test_purity.py` parses the package and fails the build if that changes, which is the structural form of *"the AI must never read directly from the database"*: there is no handle here to read one through.

Templates are held to the same standard as the model. `test_templates` runs the full validator suite over template output — and caught four real defects in the hand-written prose during Sprint 3, including two places where a template computed a number (`days_in_month - days_elapsed`) rather than reading one.

## Consequences

- **ADR-009 §4.4's `{headline, body}` is superseded** for narration output. Its provenance validator, lexical validator and fallback doctrine are implemented as written.
- **Acceptance is partial and that is expected.** Against qwen2.5:7b, 3 of 4 attempted generations passed; the rejection was a fabricated figure. A rejected generation costs fluency and nothing else.
- **The validators catch fabricated numbers and causal claims, not hedged elaboration.** *"The trip may have involved travel and accommodation costs"* passes: it invents no number, claims no cause, and hedges. Narrowing that would need a claim-level entailment check, which is out of scope for V1.
- **`stability_status` and Q&A remain unbuilt.** The bounded single-turn Q&A subsystem of `07_AI_Architecture.md` §6 is not in this sprint; the prohibited-topic guard it needs already exists here and is reusable as-is.
- **Narration is sequential and slow** — roughly 18s per insight on a local 7B model. `llm_max_generated` (default 5) caps generation per request and spends the budget on the highest tier; the rest are templates. The budget changes the prose, never the coverage.
- **The default provider is `none`.** A fresh clone serves template narration and passes its full test suite with no model installed.
