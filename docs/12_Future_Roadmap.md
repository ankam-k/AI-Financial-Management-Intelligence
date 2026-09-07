# Future Roadmap

| Field | Value |
|---|---|
| **Document Name** | 12_Future_Roadmap.md |
| **Product** | AI Financial Intelligence Platform |
| **Version** | 1.0 |
| **Status** | 🟢 **Approved** — directional, not committed |
| **Owner** | Product |
| **Dependencies** | `00_Product_Decisions_Record.md` v1.0 |
| **Traceability** | V2 items seeded by PDR-026 and PDR-029. See §6. |
| **Blocks** | — |
| **Lifecycle stage** | Draft → Review → **Approved** → Frozen → Superseded |
| **Last Updated** | 2026-07-27 |

---

## Purpose

To record where the product could go after V1, and — more usefully — **what each future version must earn the right to build.**

## Scope

**In scope:** directional post-V1 versions, deferred decisions, the conditions that gate each stage.

**Out of scope:** commitments, dates, resourcing. Nothing here is approved for build.

## Assumptions

**None.** Only PDR-026 (V2 Account Aggregator) and PDR-029 (V2 wearables) are recorded product direction. Everything else is a candidate.

## References

`00_Product_Decisions_Record.md` v1.0 · `01_Product_Vision.md` v1.0

## Related Documents

`docs/INDEX.md`

---

## 1. The sequencing rule

> **Each version earns the right to the next by proving the prior thesis.**

We do not build V3 features to compensate for a V1 that did not land. If V1's behavioral insights are not trusted, adding forecasting adds a second untrusted claim on top of the first.

**Gate for anything beyond V1:** Insight Trust Rate ≥70% and False Insight Rate <5% sustained (PDR-045🟠). Until that holds, the correct roadmap is *improving V1*.

## 2. V2 — Remove the friction

**Thesis:** V1's core constraint is that value requires sustained manual effort — both uploading statements and logging habits daily. V2 removes as much of that as possible without weakening the trust model.

| Item | Source | Notes |
|---|---|---|
| **RBI Account Aggregator integration** | **PDR-026** (recorded direction) | Automatic transaction data. `StatementSourcePort` (PDR-013, ADR-004) exists precisely so this is an adapter, not a rewrite. Requires entity registration and consent-artifact handling — the reason it was excluded from V1 (PDR-014). |
| **Wearable / health platform integration** | **PDR-029** (recorded direction) | Automatic sleep and exercise data. **The most valuable single item on this roadmap**: it directly attacks the coverage floor (PDR-040🟠) that limits how often V1 can say anything. |
| Email statement ingestion | Candidate | Another port adapter; lower value than AA. |
| PDF statement parsing | Candidate — excluded from V1 by PDR-010 | Broad bank coverage without AA onboarding. |

**Open question V2 must answer:** wearable data arrives continuously, which changes missing-data semantics. A device that was not worn is still UNKNOWN — PDR-040🟠's invariant must be re-derived for device data, not assumed to carry over. Device gaps are *differently* missing from unlogged days, and treating them identically would be a new instance of the same failure.

## 3. V3 — Look forward

**Thesis:** once the present is explained and believed, the future becomes addressable.

| Item | Notes |
|---|---|
| Commitment-aware cashflow forecasting | Builds on V1's recurring detection. Explicitly not V1 (PDR-015). |
| "Safe to spend" | Requires forecasting plus trusted commitment detection. |
| Goal setting and tracking | Excluded from V1 by PDR-046🟠. Meaningful once the present is explained. |
| Budgets and spending limits | Excluded by PDR-046🟠 as a different product philosophy. Revisit only if users ask for constraint-setting *after* explanation works. |

**Precondition:** a wrong forecast from an untrusted system ends the relationship. V3 requires V1's trust metrics sustained, not merely achieved once.

## 4. V4+ — Deeper behavior

| Item | Notes |
|---|---|
| User-defined custom habits | Excluded from V1 by PDR-038🟠 to bound the hypothesis space. Requires solving per-user multiplicity correction first — the reason it was excluded is a statistical problem, not a scope preference. |
| Richer habit types (mood, social, screen time) | Same constraint. |
| Multi-turn conversational assistant | Excluded by PDR-037🟠/PDR-046🟠. Requires a constrained tool-calling design where the model may invoke only audited computations — never free reasoning over raw data (PDR-031). |
| Household / shared accounts | Requires shared-ledger semantics and multi-party consent. |
| Additional markets and currencies | PDR-025 requires the architecture to accommodate this without redesigning the analysis engine. |

## 5. Explicitly not on the roadmap

Some exclusions are permanent, not deferred.

| Never | Why |
|---|---|
| Investment, tax, insurance, or loan advice | PDR-023, PDR-027. A regulatory identity, not a feature gap. |
| Bill payment or money movement | Payments licensing — a different company. |
| Selling, sharing, or aggregating user data | PDR-034🟠. Structural: no cross-user computation exists in the system. |
| Training models on user financial data | PDR-034🟠. |
| Peer comparison / benchmarking | Requires cross-user computation (forbidden), and peer comparison on personal finance is an anxiety machine. |
| Engagement-optimized insight selection | Would invert PDR-045🟠. Engagement rewards confident nonsense; the North Star exists to punish it. |

**The last row is the most important.** The most likely way this product degrades is not a bad feature — it is optimizing insights for clicks instead of truth. That pressure arrives with growth, and the roadmap names it now so it is recognizable later.

## 6. Traceability

| Roadmap item | Authority |
|---|---|
| V2 Account Aggregator | **PDR-026** (recorded direction), PDR-013, PDR-014 |
| V2 Wearables | **PDR-029** (recorded direction) |
| V2 PDF parsing | PDR-010 (excluded from V1) |
| V3 Forecasting | PDR-015 (excluded from V1) |
| V3 Goals, budgets | PDR-046🟠 |
| V4 Custom habits | PDR-038🟠 |
| V4 Multi-turn assistant | PDR-037🟠, PDR-046🟠, PDR-031 |
| V4 Other markets | PDR-025 |
| Permanent exclusions | PDR-023, PDR-027, PDR-034🟠, PDR-045🟠 |
