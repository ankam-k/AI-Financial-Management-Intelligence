# ADR-008 — Qwen2.5-Instruct served locally via Ollama

**Status:** Accepted · **Date:** 2026-07-27 · **Serves:** PDR-020, PDR-024, PDR-034🟠, NFR-7 · **Closes:** D-19

## Decision

Serve **Qwen2.5-7B-Instruct** through **Ollama** on the same host as the application, behind an `LLMPort` interface. Structured output is requested via JSON schema constraint. The model is never on the critical path for correctness.

## Context

PDR-020 approves Qwen as the model family but leaves hosting, size and runtime open. PDR-024 requires user financial data to remain private, and PDR-034🟠 forbids third-party sharing — which makes sending transaction-derived data to a hosted inference API a direct conflict, not merely a preference.

The model's job is narrow by design (PDR-031, ADR-009): render structured insight objects into prose and answer bounded questions from those same objects. It never performs analysis.

## Alternatives

**Hosted API (any third-party provider).** Highest quality, zero ops. Rejected on privacy grounds: it would send derived financial data off-infrastructure, conflicting with PDR-024 and PDR-034🟠. Also introduces per-request cost and an availability dependency for a component NFR-7 requires to be optional.

**Qwen2.5-3B local.** Faster, smaller footprint, runs on modest hardware. Weaker instruction-following, and — critically — less reliable at *not* embellishing, which is the single behavior ADR-009's validators exist to catch. More validation failures means more template fallback, degrading the experience.

**Qwen2.5-14B or larger local.** Better quality. Hardware requirements exceed what a single modest host provides, complicating ADR-013's deployment story for a V1.

**Qwen2.5-7B-Instruct local.** Adequate instruction-following for constrained rendering, runs on a single machine with 16GB, good structured-output behavior.

**Runtime — vLLM.** Higher throughput, better batching. Heavier operational setup; throughput is irrelevant at V1's single-user-at-a-time analysis cadence.

**Runtime — llama.cpp direct.** Maximum control, minimum overhead. More integration work than Ollama for no V1 benefit.

**Runtime — Ollama.** Simple model management, OpenAI-compatible API surface, trivial Docker Compose integration.

## Tradeoffs

| Gain | Cost |
|---|---|
| Financial data never leaves our infrastructure — a stateable user promise | Local inference is slower than a hosted frontier model |
| No per-request cost; no external availability dependency | Requires a host with adequate RAM/GPU |
| Model swappable behind `LLMPort` without touching application code | 7B quality is below frontier models; prose is plainer |
| Ollama makes model management and Compose integration trivial | Ollama adds a service to operate |

## Final Choice

**Qwen2.5-7B-Instruct via Ollama, local, behind `LLMPort`.**

The privacy argument is decisive and reframes the choice: local inference is not a cost compromise here, it is a **product feature** we can state to users — their financial data never leaves the system.

The quality gap is acceptable precisely because ADR-009 confines the model to rendering pre-computed truth. A 7B model writing a paragraph from a structured object, with its numbers validated afterward, is a well-matched task.

## Consequences

- Docker Compose includes an Ollama service; the model is pulled on first run (ADR-013).
- `LLMPort` is the only interface application code sees. Swapping model or runtime touches one adapter.
- All generation requests JSON-schema-constrained output, checked by ADR-009's validators.
- Generation timeouts fall back to template rendering (NFR-7) — the product never blocks on the model.
- Hardware requirement (≈16GB RAM) is documented in `10_Deployment.md` as a deployment constraint.
- If quality proves insufficient after evaluation against synthetic datasets, the escalation path is a larger local model — **not** a hosted API, which the privacy posture forecloses.
