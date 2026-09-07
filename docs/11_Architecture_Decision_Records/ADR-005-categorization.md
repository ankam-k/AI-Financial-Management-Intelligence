# ADR-005 — Layered categorization with an explicit confidence floor

**Status:** Accepted · **Date:** 2026-07-27 · **Serves:** SRS-4.1 … 4.5, PDR-001, PDR-030 · **Closes:** D-13, D-22

## Decision

Categorize in four ordered layers, first match wins: **(1) user override → (2) deterministic rules → (3) curated merchant dictionary → (4) embedding similarity**. Anything below the confidence floor resolves to `UNCATEGORIZED`. Every result persists a machine-readable reason and a confidence score.

## Context

SRS-4.2 requires a *visible reason* on every categorization — this is where PDR-001's explainability promise is first tested, on the most-viewed screen in the product. SRS-4.3 requires low-confidence results to become `UNCATEGORIZED` rather than be asserted. Indian merchant strings arrive as UPI narration (`UPI/DR/412345678901/SWIGGY/YESB/swiggy@ybl/Payment`), which is semi-structured and highly repetitive across users — a property worth exploiting.

## Alternatives

**A. Rules only.** Fully deterministic, trivially explainable ("narration contains SWIGGY"). But coverage plateaus, and the long tail stays uncategorized, degrading every downstream aggregate.

**B. Trained classifier only.** Best tail coverage. But it needs labelled training data we do not have at launch, and its explanation ("the model predicted Food, 0.83") is not an explanation a user can verify — failing PDR-001 on the highest-traffic surface.

**C. LLM categorization.** Excellent zero-shot coverage on messy Indian merchant strings. Rejected for the primary path: non-deterministic (violates SRS-4.5), expensive per transaction, and it puts the model inside the truth path, contradicting PDR-031.

**D. Layered: rules → dictionary → embeddings, with a floor.** Deterministic where it can be, statistical where it must be, honest where it cannot be.

## Tradeoffs

| Gain | Cost |
|---|---|
| Most transactions get a human-readable reason (rule/dictionary match) | Four layers to maintain and reason about |
| Deterministic — same input, same category (SRS-4.5) | Curated dictionary needs seeding and ongoing curation |
| No training data required at launch | Embedding layer needs a local model and a vector index |
| `UNCATEGORIZED` is honest rather than a confident guess | Visible uncategorized rate may look like a weakness; it is the opposite |
| User overrides win permanently and feed the dictionary | Override precedence must survive re-import (SRS-4.4) |

## Final Choice

**D — four ordered layers with a confidence floor.**

A curated Indian merchant dictionary (~500 seed entries covering the dominant UPI merchants) is included at launch, resolving D-22 affirmatively: without it, layer 3 is empty and too much traffic falls to embeddings, where explanations are weakest.

Embedding similarity produces a reason of the form *"similar to previously categorized merchant X"* — verifiable, because the user can inspect X.

## Consequences

- Each layer emits a typed `CategoryReason`, rendered directly in the UI.
- The confidence floor is externalized configuration, tuned against synthetic datasets (SRS-3.18).
- User overrides are stored separately and applied before all automated layers, permanently and across re-imports (SRS-4.4).
- An override on a merchant promotes that mapping into the user's personal dictionary, so later transactions from the same merchant resolve at layer 3.
- Categorization runs in `domain` and takes the embedding index as an injected port, keeping it unit-testable without a model.
- The uncategorized rate is a tracked quality metric (PDR-045🟠), trending down across releases.
