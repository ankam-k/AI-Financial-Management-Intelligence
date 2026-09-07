# ADR-018 — Chat V1: guard-first, deterministic routing, no conversation state

**Status:** Accepted · **Date:** 2026-07-28 · **Serves:** PDR-027, PDR-037🟠, SRS-7.7 … 7.10 · **Implements:** ADR-010, `07_AI_Architecture.md` §6

## Decision

Five decisions taken while building the conversational assistant (Sprint 5):

| # | Decision |
|---|---|
| 1 | **The guard runs first** — before intent detection, before context building, before anything is loaded. |
| 2 | **Intent routing is deterministic pattern matching**, not a model and not embeddings. |
| 3 | **No conversation state exists** anywhere: no id, no history field, no server memory. |
| 4 | **Context is the minimum the matched intent needs**, and that selection is a security control. |
| 5 | **A refusal is a 200**, with a reason, not an error status. |

## Context

`07_AI_Architecture.md` §6 already specifies the pipeline and the boundary. What it does not fix is how intents are detected, how much context travels, or what a refusal looks like over HTTP. The brief for this sprint adds the requirement that the assistant consume existing analytics rather than duplicate them — which it does literally: the chat layer computes nothing, and its template answers are assembled from narration Sprint 3 already wrote and validated.

## Alternatives

**1. Guard placement.** Screening the *output* would be simpler — one validator beside the three that already exist. But ADR-010's claim is that prohibited content is "never generated, never logged, never cached", and that is only true if nothing downstream of the guard receives the question. Screening output means the question reached a model and a prompt existed. The guard therefore runs before routing, and a refused question is never even classified — `intent` is `null` on a prohibited refusal, and a test asserts the model was not called.

**2. What the guard actually matches.** A keyword ban on financial products is the obvious implementation and it breaks PDR-027's own worked example: *"How much did I pay in loan EMIs last quarter?"* is a factual query about recorded history and must be answered. So a refusal requires **a product topic and a directive frame** — with a short list of asks (*"which stock should I buy"*) that have no descriptive reading and are refused however phrased. Capital itself is a topic, not just the products it goes into: *"where should I put my savings"* names no product and is plainly an allocation question.

**3. Intent detection: rules versus a model or embeddings.** Embeddings were excluded by the brief, but they would have been wrong here anyway. **An embedding matcher always returns a nearest neighbour**, so "the analysis engine has no output that answers this" stops being expressible — and that refusal is the honest answer to most questions. Rules also make every routing decision a testable assertion, and they run before the expensive step decides what it may see.

**4. Context size.** Sending the whole analysis run would be simpler and would look harmless. It is not: the provenance validator builds its permitted-number set from exactly the payload the model received, so a context carrying every insight **licenses the answer to quote any figure from any of them** — including ones irrelevant to the question, where a plausible mix-up would pass every check. Selecting per intent is what makes that set meaningful, and a test asserts a figure from an unselected insight is still treated as a fabrication.

**5. Refusal as an error status.** A 4xx for "I won't recommend a fund" would make the product's most important behaviour something clients catch as an exception. Both refusals are correct outcomes of well-formed requests, so both are 200 with a `refusal_reason`, and the UI renders them as answers rather than failures.

## Tradeoffs

| Gain | Cost |
|---|---|
| Prohibited questions never reach a model, a log or a cache | The guard cannot use intent, so it must be conservative on its own |
| "No capability covers this" stays expressible | Phrasing outside the rules is refused; the rule list needs upkeep |
| Single-turn is structurally true, not merely intended | *"What about groceries?"* cannot work — there is no antecedent to resolve |
| A number from an unselected insight is still a fabrication | Context selection has to be right, or a valid question loses its evidence |
| Clients treat refusals as content | Callers must read `status`, not just the HTTP code |

## Final Choice

**A consumer, not a second engine.**

`app/chat/` performs no I/O and computes nothing. Its template answers quote observations and evidence that already passed the provenance, lexical and advice validators in Sprint 3 — prose that has been validated once cannot fail by being quoted. Generated answers are re-checked against the same three validators, with the **strictest tier in the context** deciding the language rules, because a reader cannot tell which sentence came from which finding.

`app/services/chat_service.py` is the only file in the chat path that touches a database. There is no handle below it, which is the structural form of "the LLM never queries the database directly".

## Consequences

- **A follow-up question does not work, by design.** *"What about groceries?"* has no antecedent and routes nowhere. The UI says so in its empty state rather than letting a user discover it. Revisiting means revisiting PDR-037🟠, not adding a parameter.
- **The transcript is a browser artefact.** Clearing it is a local `setState`; the server was never told a conversation existed.
- **Data-sufficiency notices are capped at two** in a context. One per habit all read the same — six of them is the same sentence six times, which buries the point rather than making it.
- **The assistant works with no model configured**, as everything else does. Template answers are the default and the fallback.
- **The rule list is the capability list.** An intent with no insight types would be a question the system claimed to support and cannot ground; a test asserts every intent has one, and the starter questions in the UI are served from the same map so they cannot drift into suggesting a refusal.
