# Software Requirements Specification (SRS)

| Field | Value |
|---|---|
| **Document Name** | 03_SRS.md |
| **Product** | AI Financial Intelligence Platform |
| **Version** | 1.0 |
| **Status** | 🟢 **Approved** |
| **Owner** | Engineering |
| **Dependencies** | `00_Product_Decisions_Record.md` v1.0 · `02_PRD.md` v1.0 |
| **Traceability** | Every SRS requirement maps to a PRD requirement and a PDR decision. See §11. |
| **Blocks** | 04_System_Architecture, 09_Testing_Strategy |
| **Lifecycle stage** | Draft → Review → **Approved** → Frozen → Superseded |
| **Last Updated** | 2026-07-27 |

---

## Purpose

To specify **precisely and testably** what the software must do — converting the PRD's capability statements into verifiable, unambiguous requirements an engineer can implement and a tester can falsify.

## Scope

**In scope:** functional specifications, data requirements, statistical specifications, external interface requirements, quality attributes, constraints, and verification criteria.

**Out of scope:** architecture and technology choices (→ `04`), schema DDL (→ `05`), endpoint contracts (→ `06`), prompts (→ `07`).

## Assumptions

**None.** Every requirement traces to the PRD, which traces to the PDR. 🟠 marks dependence on a provisional decision.

## References

`00_Product_Decisions_Record.md` v1.0 · `02_PRD.md` v1.0 · Benjamini & Hochberg (1995), FDR control

## Related Documents

`docs/INDEX.md` · `04_System_Architecture.md` · `09_Testing_Strategy.md`

---

## 1. Definitions

| Term | Definition |
|---|---|
| **Transaction** | A single money movement in the canonical internal format. |
| **Raw Record** | A source row as ingested, before normalization. Retained for provenance. |
| **Check-in** | One daily habit record for one user for one date, covering all six habits. |
| **UNKNOWN** | The state of a habit value where no check-in exists for that date. Distinct from a recorded false/zero. |
| **Recorded Negative** | An explicit false/zero value submitted within a check-in. |
| **Life Event** | A user-declared dated annotation used to segment analysis windows. |
| **Signal** | A derived, deterministic quantity computed from transactions (e.g. weekly category totals). |
| **Insight** | A claim about the user, bound to evidence, with a tier and confidence. |
| **Evidence** | The set of stored records from which an insight's numbers are reconstructible. |
| **Analysis Window** | The bounded date range over which an insight is computed. |
| **Coverage** | Proportion of dates in a window having a check-in. |
| **T1 / T2 / T3** | Insight tiers: arithmetic fact / rule-based pattern / statistical association. |

## 2. Insight tier model

This model is the mechanism by which PDR-017, PDR-028 and PDR-031 are enforced. Every user-facing claim belongs to exactly one tier.

| Tier | Basis | Determinism | Confidence | Language |
|---|---|---|---|---|
| **T1** | Arithmetic over stored rows | Exact | Omitted (PDR-032🟠) | Assertive; causal permitted where arithmetic proves it (PDR-036🟠) |
| **T2** | Rule-based detection with stated thresholds | Exact | Omitted | Assertive |
| **T3** | Statistical association | Reproducible given fixed input | **Mandatory** (PDR-032🟠) | **Correlational only** (PDR-028) |

**SRS-2.1** Every insight record SHALL carry its tier.
**SRS-2.2** T3 insights SHALL NOT be emitted unless all five gates in §6 pass.
**SRS-2.3** T3 insight text SHALL NOT contain causal connectives. *(Verified by automated lexical check — §10.)*
**SRS-2.4** Causal connectives SHALL be permitted only on T1 insights whose claim is provable by summation of stored rows alone (PDR-036🟠).
**SRS-2.5** Every insight SHALL reference ≥1 evidence record; an insight with zero evidence is a defect (PDR-017).

## 3. Ingestion requirements

**SRS-3.1** The system SHALL accept CSV files of bank-exported statements. *(FR-1.1)*
**SRS-3.2** The system SHALL implement a **Statement Source Port**; all ingestion adapters implement it, and no module downstream of ingestion depends on any source-specific type. *(FR-1.5, PDR-013)*
**SRS-3.3** Ingestion SHALL execute the ordered pipeline: `parse → validate → normalize → deduplicate → categorize → persist`. *(FR-1.2)*
**SRS-3.4** Each ingested row SHALL be retained as a Raw Record linked to the Transaction derived from it. *(PDR-017)*
**SRS-3.5** Import SHALL be atomic — a failure at any stage SHALL leave persisted state unchanged. *(FR-1.8)*
**SRS-3.6** Import failure SHALL report source row number, field, and the reason. *(FR-1.9)*
**SRS-3.7** The system SHALL compute a deterministic deduplication key per transaction and reject a row whose key already exists for that user. *(FR-1.7)*
**SRS-3.8** Re-import of an identical file SHALL produce zero new Transactions. *(FR-1.7)*
**SRS-3.9** Import of an overlapping statement SHALL produce exactly one Transaction per real-world transaction. *(FR-1.7)*
**SRS-3.10** Monetary amounts SHALL be stored as **signed integers in paise**. Floating-point SHALL NOT be used for money at any layer. *(NFR-4, PDR-021)*
**SRS-3.11** Transactions SHALL distinguish `transaction_date` from `value_date`. Dates SHALL be stored unambiguously and interpreted in IST. *(FR-1.14)*
**SRS-3.12** The canonical Transaction SHALL record instrument type ∈ {UPI, BANK, DEBIT_CARD, CREDIT_CARD, WALLET}. *(FR-1.13, PDR-022)*
**SRS-3.13** The system SHALL extract and normalize merchant identity from narration/description fields, including UPI narration structure. *(FR-2.3)*
**SRS-3.14** Currency SHALL be a modelled field constrained to INR in V1, not a hardcoded constant. *(PDR-025, NFR-6)*
**SRS-3.15** PDF ingestion SHALL NOT be implemented. *(FR-1.4)*
**SRS-3.16** No adapter SHALL make outbound network calls to a financial institution. *(FR-1.6, PDR-014)*

### Synthetic data

**SRS-3.17** The system SHALL provide ≥3 synthetic datasets representing distinct spending behaviors. *(FR-1.10)*
**SRS-3.18** Synthetic datasets SHALL contain **documented planted patterns** usable as ground truth for AI evaluation. *(FR-1.12, PDR-012)*
**SRS-3.19** Synthetic datasets SHALL additionally contain documented **negative controls** — habit/category pairs with no planted relationship — so false-positive rate is measurable. *(FR-4.6, PDR-043🟠)*
**SRS-3.20** Records originating from synthetic data SHALL be flagged, and the flag SHALL be exposed wherever displayed. *(FR-1.11)*
**SRS-3.21** Synthetic generation SHALL be seeded and reproducible. *(NFR-5)*

## 4. Categorization requirements

**SRS-4.1** Every Transaction SHALL hold a category, or the explicit value `UNCATEGORIZED`. *(FR-2.1, FR-2.7)*
**SRS-4.2** Every categorization SHALL persist a machine-readable **reason** and a confidence score in [0,1]. *(FR-2.2)*
**SRS-4.3** A categorization whose confidence falls below the configured floor SHALL resolve to `UNCATEGORIZED` rather than be asserted. *(FR-2.7, PDR-030)*
**SRS-4.4** A user override SHALL be stored as a distinct record and SHALL take precedence over any automated result, permanently and across re-imports. *(FR-2.5)*
**SRS-4.5** Categorization SHALL be deterministic: identical input yields identical category and confidence. *(NFR-5)*
**SRS-4.6** Recurring transactions SHALL be detected by periodicity and amount stability, with the detection thresholds recorded on the resulting T2 insight. *(FR-2.6)*

## 5. Behavior capture requirements

**SRS-5.1** The system SHALL support exactly six habits with these types: `sleep_hours` (decimal, 0.0–24.0), `exercise` (boolean), `home_cooked_meals` (integer, 0–3), `stress_level` (integer, 1–5), `alcohol` (boolean), `work_mode` (enum: OFFICE | REMOTE | LEAVE). *(FR-3.2, PDR-038🟠)*
**SRS-5.2** The system SHALL NOT support user-defined habits. *(FR-3.3)*
**SRS-5.3** Habit data SHALL be stored as **one Check-in per (user, date)**, uniquely constrained. *(FR-3.4)*
**SRS-5.4** Every habit field within a Check-in SHALL be **nullable**. *(FR-3.5)*

> ### ⭐ SRS-5.5 — The missing-data invariant *(FR-3.8, FR-3.9, PDR-040🟠)*
>
> **(a)** Absence of a Check-in row for a date SHALL mean UNKNOWN for all six habits on that date.
> **(b)** A NULL field within an existing Check-in SHALL mean UNKNOWN for that habit only.
> **(c)** A non-NULL `false`/`0` value SHALL mean **Recorded Negative** — a positive assertion that the behavior did not occur.
> **(d)** No schema column SHALL declare a DEFAULT value for any habit field. No code path SHALL coalesce NULL to `false`, `0`, or any other value for analytical purposes.
> **(e)** UNKNOWN and Recorded Negative SHALL be distinguishable at every layer: storage, domain model, API response, and analysis input.
>
> *This is the single most consequential invariant in the specification. Violating it manufactures correlations that do not exist while leaving every individual number technically traceable — satisfying PDR-017 in letter while destroying it in substance.*

**SRS-5.6** Check-ins SHALL be creatable for dates up to 30 days in the past; earlier dates SHALL be rejected. *(FR-3.6)*
**SRS-5.7** Check-ins SHALL NOT be creatable for future dates.
**SRS-5.8** Editing a Check-in SHALL invalidate every Insight whose analysis window contains that date, marking them stale for recomputation. *(FR-3.7)*
**SRS-5.9** Life Events SHALL record: `event_type` ∈ {TRAVEL, ILLNESS, JOB_CHANGE, RELOCATION, FESTIVAL, FAMILY_EVENT, OTHER}, `title`, `start_date`, nullable `end_date`, nullable `notes`. *(FR-3.10)*
**SRS-5.10** A NULL `end_date` SHALL denote a point-in-time event; a non-NULL `end_date` SHALL denote an inclusive range and SHALL be ≥ `start_date`. *(FR-3.10)*
**SRS-5.11** Life Events SHALL be used only to segment analysis windows and SHALL NOT be assigned causal status. *(FR-3.11)*
**SRS-5.12** No code path SHALL infer a habit value from Transaction data. *(FR-3.1, PDR-029)*

## 6. Statistical requirements

> Governs every T3 insight. Implements PDR-030 and PDR-043🟠.

### 6.1 The five gates

**SRS-6.1** A T3 insight SHALL be emitted only if **all five** gates pass. Failure of any gate SHALL suppress the insight entirely — not downgrade it.

| Gate | Requirement | Threshold |
|---|---|---|
| **G1** History | Transaction history spanning the window | ≥ 8 weeks |
| **G2** Group size | Observations in **each** compared group | ≥ 6 |
| **G3** Coverage | Dates in window with a Check-in | ≥ 60% |
| **G4** Effect size | Absolute **and** relative difference | ≥ ₹500/week **and** ≥ 15% |
| **G5** Multiplicity | Benjamini–Hochberg FDR across all hypotheses in the run | q = 0.10 |

**SRS-6.2** G3 SHALL be computed over dates having a Check-in containing a **non-NULL value for the specific habit under test** — not merely a Check-in row. *(Consequence of SRS-5.5(b).)*
**SRS-6.3** UNKNOWN observations SHALL be excluded from the analysis (complete-case). Imputation of any kind SHALL NOT be performed. *(FR-4.7, SRS-5.5)*
**SRS-6.4** Excluded-observation counts SHALL be recorded on the insight and exposed in its evidence. *(FR-4.8)*
**SRS-6.5** G5 SHALL be applied across **all** hypotheses tested in a single analysis run, not per hypothesis.
**SRS-6.6** The number of hypotheses tested SHALL be recorded on each emitted insight, for audit.
**SRS-6.7** A newly detected T3 insight SHALL be labelled `TENTATIVE`, and promoted to `ESTABLISHED` only after passing all gates again in a subsequent, non-identical analysis window. *(FR-4.9)*
**SRS-6.8** Threshold values SHALL be externalized configuration, not literals, so they can be tuned against SRS-3.18/3.19 datasets.
**SRS-6.9** All statistical computation SHALL be deterministic. Any randomized procedure SHALL use a fixed seed. *(NFR-5)*

### 6.2 Insight emission

**SRS-6.10** At most **5** insights SHALL be surfaced per analysis period, ranked by `effect_size × confidence × novelty`. *(FR-4.10)*
**SRS-6.11** When G1 or G3 fails, the system SHALL emit a **Data Sufficiency Notice** stating what is missing and what would unlock insights. *(FR-4.5, PDR-030)*
**SRS-6.12** When coverage falls below G3 for the current window, behavioral insights SHALL pause; prior insights SHALL remain retrievable, labelled with their original window. *(FR-4.11, FR-4.12)*
**SRS-6.13** T1 and T2 output SHALL remain available irrespective of habit coverage. *(FR-4.13)*

## 7. AI layer requirements

**SRS-7.1** The analysis engine SHALL be the sole originator of numerical results and behavioral conclusions. *(FR-4.14, PDR-031)*
**SRS-7.2** The LLM SHALL receive **only** structured analysis-engine output. It SHALL NOT receive raw Transaction rows as a substitute for analysis. *(PDR-031)*
**SRS-7.3** Generated output SHALL be validated before display by a **provenance check**: every numeric literal in the output must appear in the input payload. Output failing validation SHALL NOT be displayed. *(FR-4.2, PDR-017)*
**SRS-7.4** Generated output SHALL be validated by a **lexical check** rejecting causal connectives on T3 content. *(SRS-2.3, PDR-028)*
**SRS-7.5** On validation failure, the system SHALL fall back to deterministic template rendering of the same structured insight. *(NFR-7)*
**SRS-7.6** The system SHALL remain functional when the model is unavailable; insights SHALL render via template. *(NFR-7)*
**SRS-7.7** Q&A SHALL be **single-turn**; no conversational state SHALL be persisted between questions. *(FR-5.4, PDR-037🟠)*
**SRS-7.8** Q&A SHALL be answerable only from analysis-engine outputs. Questions not answerable from them SHALL receive an explicit refusal. *(FR-5.5)*
**SRS-7.9** Every question SHALL pass a **prohibited-topic guard** before reaching the model, covering stocks, mutual funds, ETFs, insurance, loans, tax planning, and investment products. A blocked question SHALL receive a refusal that does not attempt a partial answer. *(FR-5.6, FR-5.8, PDR-027)*
**SRS-7.10** The guard SHALL NOT rely solely on model instruction; it SHALL be an independently testable component. *(PDR-027)*

## 8. Trust, privacy and access requirements

**SRS-8.1** Every data-access operation SHALL be scoped to the authenticated user. No query SHALL be executable without a user scope. *(FR-6.1, PDR-035🟠)*
**SRS-8.2** No computation SHALL aggregate across users. *(FR-6.8, PDR-034🟠)*
**SRS-8.3** User data SHALL NOT be used for model training or fine-tuning. *(FR-6.8)*
**SRS-8.4** The system SHALL support export of all user data in a machine-readable format. *(FR-6.2)*
**SRS-8.5** Source deletion SHALL cascade to Raw Records, Transactions, Signals, Insights, Evidence links and cached AI output derived from it. *(FR-6.3, PDR-033🟠)*
**SRS-8.6** Account deletion SHALL remove all user-attributable rows. Soft-delete SHALL NOT satisfy this requirement. *(FR-6.4)*
**SRS-8.7** Consent SHALL be captured and recorded for data upload and for AI processing. *(FR-6.6)*
**SRS-8.8** The system SHALL present the user an inventory of data stored about them. *(FR-6.5)*
**SRS-8.9** Credentials SHALL never be logged. Financial amounts and merchant identities SHALL NOT appear in logs at INFO level or below.

## 9. Quality attributes

| ID | Attribute | Requirement |
|---|---|---|
| **SRS-9.1** | Determinism | Given fixed data, insight generation SHALL produce identical claims across runs. *(NFR-5)* |
| **SRS-9.2** | Traceability | Every displayed number SHALL be reconstructible from stored records. *(PDR-017)* |
| **SRS-9.3** | Maintainability | Layer boundaries SHALL be enforced; business logic SHALL NOT reside in route handlers or ORM models. *(NFR-2)* |
| **SRS-9.4** | Testability | Analysis engine SHALL be unit-testable without a model, a database fixture, or a network. |
| **SRS-9.5** | Extensibility | Adding an ingestion source SHALL require implementing the port and nothing else. *(NFR-6)* |
| **SRS-9.6** | Observability | Every ingestion and analysis run SHALL emit structured logs with a correlation id. *(NFR-9)* |
| **SRS-9.7** | Error handling | No unhandled exception SHALL reach the user; errors SHALL be typed and mapped to responses. *(NFR-9)* |
| **SRS-9.8** | Documentation | Every module SHALL document its purpose and its tradeoffs. *(NFR-3)* |

## 10. Verification requirements

Requirements the test suite must satisfy. Elaborated in `09_Testing_Strategy.md`.

**SRS-10.1** A test SHALL assert UNKNOWN is never conflated with Recorded Negative, at each of: storage, domain model, API response, analysis input. *(SRS-5.5)*
**SRS-10.2** A test SHALL assert no float type is used for money on any path. *(SRS-3.10)*
**SRS-10.3** A test SHALL assert identical-file re-import creates zero Transactions. *(SRS-3.8)*
**SRS-10.4** A test SHALL assert overlapping-statement import creates exactly one Transaction per real transaction. *(SRS-3.9)*
**SRS-10.5** A test SHALL run the engine against synthetic negative controls and assert **zero** T3 insights are emitted. *(SRS-3.19)*
**SRS-10.6** A test SHALL run the engine against planted patterns and assert they are detected. *(SRS-3.18)*
**SRS-10.7** A lexical test SHALL assert no T3 user-facing string contains a causal connective. *(SRS-2.3)*
**SRS-10.8** A test SHALL assert every number in generated prose exists in the structured input. *(SRS-7.3)*
**SRS-10.9** A test suite SHALL assert the prohibited-topic guard blocks each of the seven PDR-027 categories across multiple phrasings. *(SRS-7.9)*
**SRS-10.10** A test SHALL assert User A cannot read User B's data on every data-access path. *(SRS-8.1)*
**SRS-10.11** A test SHALL assert account deletion leaves zero user-attributable rows. *(SRS-8.6)*
**SRS-10.12** A test SHALL assert the system produces insights with the model unavailable. *(SRS-7.6)*

## 11. Traceability

| SRS section | PRD | PDR |
|---|---|---|
| §2 Tier model | FR-4.2, FR-5.2 | PDR-017, 028, 031, 032🟠, 036🟠 |
| §3 Ingestion | FR-1.1 … 1.14 | PDR-009 … 014, 021, 022, 025 |
| §4 Categorization | FR-2.1 … 2.7 | PDR-001, 011, 016, 018, 030 |
| §5 Behavior capture | FR-3.1 … 3.12 | PDR-029, 038🟠, 039🟠, **040🟠**, 042🟠 |
| §6 Statistics | FR-4.5 … 4.13 | PDR-030, **043🟠**, 040🟠, 041🟠, 047🟠 |
| §7 AI layer | FR-4.14, FR-5.3 … 5.8 | PDR-017, 027, 028, 031, 037🟠 |
| §8 Trust | FR-6.1 … 6.9 | PDR-023, 024, 033🟠, 034🟠, 035🟠 |
| §9 Quality | NFR-1 … NFR-9 | PDR-002, 004, 005, 025, 031 |
| §10 Verification | All acceptance criteria | PDR-002, 012, 017 |
