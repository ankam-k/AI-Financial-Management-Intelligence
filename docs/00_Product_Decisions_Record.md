# Product Decisions Record (PDR)

| Field | Value |
|---|---|
| **Document Name** | 00_Product_Decisions_Record.md |
| **Document ID** | PDR |
| **Product** | AI Financial Intelligence Platform |
| **Version** | 1.0 |
| **Status** | 🔵 **FROZEN** — baseline for all downstream documents. ⚠️ Contains 16 **provisional** decisions (§B.7) awaiting owner ratification. |
| **Owner** | Product |
| **Dependencies** | `CLAUDE.md` (standing project constraints) |
| **Traceability** | Root authority. This document traces to nothing above it; all other documents trace to it. |
| **Blocks** | 01_Product_Vision, 02_PRD, 03_SRS, 04_System_Architecture, 05_Database_Design, 06_API_Design, 07_AI_Architecture, 08_UI_UX, 09_Testing_Strategy, 10_Deployment, 11_ADRs, 12_Future_Roadmap |
| **Lifecycle stage** | Draft → *Review* → Approved → Frozen → Superseded |
| **Created** | 2026-07-27 |
| **Last Updated** | 2026-07-27 — Discovery Session 2 rulings incorporated (PDR-027 … PDR-031) |

---

## Purpose

To record, in one authoritative place, every product decision that has been **explicitly approved** for this project, together with its rationale and its implications — so that all downstream engineering work can be traced to an approved decision rather than to an assumption.

## Scope

**In scope:** approved product decisions (§B), interpretations awaiting confirmation (§C), open decisions with no authority (§D), approved exclusions (§E), traceability rules (§F), change control (§G), document status (§H), and PRD readiness (§J).

**Out of scope:** requirements, specifications, architecture, schemas, interfaces, and designs. Those belong to the documents this one governs. The PDR records *what was decided*, never *how it will be built*.

## Assumptions

**This document makes no assumptions.** That is its defining property and the reason it exists. Every statement is either explicitly approved by the product owner (§B), explicitly flagged as an unconfirmed interpretation (§C), or explicitly marked as carrying no authority (§D).

## References

- `CLAUDE.md` — standing project constraints (source of PDR-001 … PDR-005)
- Discovery Session 1 — 2026-07-27 (source of PDR-006 … PDR-026)
- Discovery Session 2 — 2026-07-27 (source of PDR-027 … PDR-031)
- Digital Personal Data Protection Act principles — referenced by PDR-024

## Related Documents

- `docs/INDEX.md` — document register and status
- `docs/01_Product_Vision.md` — 🔴 Draft, not authoritative; predates this document
- All documents listed under **Blocks** above

---

## 0. Purpose and authority

### 0.1 What this document is

The PDR is the **canonical, append-only record of every product decision that has been explicitly approved** for this project. It exists so that:

- No downstream document invents scope.
- Every requirement, schema, endpoint, prompt, and screen can be traced to an approved decision.
- Disagreements are settled by citation, not by argument or recollection.
- Decisions made months apart remain internally consistent.

### 0.2 What this document is NOT

It is **not** a vision document, a requirements document, or a design document. It contains no elaboration, no persuasion, and no proposals. It records decisions and their rationale — nothing else.

It is also **not a wish list**. Section D (Open Decisions) is explicitly *outside* the baseline and carries no authority whatsoever until an item is promoted into Section B by explicit approval.

### 0.3 Governing rule for this project

> **No document, module, schema, endpoint, prompt, or feature may introduce a product assumption that is not recorded in Section B of this PDR.**
>
> If work requires a decision that Section B does not cover, the work **stops** and the decision is raised for approval as a new Section D entry. Assumptions are never made silently, never made inline in another document, and never made in code.

### 0.4 Document hierarchy

```
                    PDR  (this document — authority)
                     │
   ┌──────────┬──────┴─────┬───────────┬──────────────┐
   ▼          ▼            ▼           ▼              ▼
 Vision      PRD          SRS      Architecture    AI Design
                                       │
                             ┌─────────┼─────────┐
                             ▼         ▼         ▼
                         Database    APIs    UI Design
                                       │
                                       ▼
                               Implementation
```

Every document below the PDR must contain a **Traceability** section mapping its contents to PDR decision IDs (see §F).

---

## A. Legend and record format

**Decision ID:** `PDR-NNN`. Permanent. Never reused, never renumbered. Superseded decisions are retained and marked, never deleted.

**Status values:**

| Status | Meaning |
|---|---|
| ✅ **APPROVED** | Explicitly decided by the product owner. Binding. |
| 🔵 **INHERITED** | Pre-existing standing constraint from `CLAUDE.md`. Binding. |
| 🟡 **PENDING** | Proposed. Carries **no authority**. Must not be implemented or referenced as fact. |
| 🔶 **NEEDS CONFIRMATION** | Follows logically from an approved decision, but is an interpretation rather than a stated decision. Must be confirmed before it becomes binding. |
| ⛔ **SUPERSEDED** | Replaced by a later decision. Retained for history. Reference the superseding ID. |

**Source values:** where the decision came from — `CLAUDE.md`, or `Discovery Session N` with the date.

---

## B. THE BASELINE — Approved decisions

> Everything in this section is binding. Everything **not** in this section is not.

### B.1 Inherited standing constraints (`CLAUDE.md`)

---

**PDR-001 — Product purpose**
**Status:** 🔵 INHERITED · **Category:** Foundation · **Source:** `CLAUDE.md`

**Decision:** The product exists to help users understand financial behavior through explainable AI.

**Implications:** Explainability is a defining product property, not a feature that can be traded away for capability. Any component that produces user-facing conclusions must be able to account for them.

---

**PDR-002 — Quality standard and tiebreaker**
**Status:** 🔵 INHERITED · **Category:** Foundation · **Source:** `CLAUDE.md`

**Decision:** This is a production-quality platform, not a demonstration project. Where design options conflict, **maintainability is the deciding criterion.**

**Implications:** Speed of delivery does not override structural quality. "It works for now" is not an accepted justification.

---

**PDR-003 — Backend technology baseline**
**Status:** 🔵 INHERITED · **Category:** Technology · **Source:** `CLAUDE.md`

**Decision:** Backend is built on **FastAPI** with **SQLAlchemy** for persistence.

**Scope note:** Database engine, migration tooling, async vs. sync strategy, and frontend stack are **not** decided by this entry. See D-BLOCK-ARCH.

---

**PDR-004 — Engineering standards**
**Status:** 🔵 INHERITED · **Category:** Engineering · **Source:** `CLAUDE.md`

**Decision:** Clean Architecture, SOLID principles, full type hints, automated tests, and modular services are mandatory.

**Implications:** Layer boundaries are enforced, not aspirational. Business logic does not live in route handlers or ORM models.

---

**PDR-005 — Documentation standard**
**Status:** 🔵 INHERITED · **Category:** Engineering · **Source:** `CLAUDE.md`

**Decision:** Every module is documented, and documentation explains **tradeoffs**, not just behavior. Decisions are made with a startup mindset — pragmatic, but not disposable.

---

### B.2 Discovery Session 1 — User (2026-07-27)

---

**PDR-006 — Primary user for Version 1**
**Status:** ✅ APPROVED · **Category:** User · **Source:** Discovery Session 1, 2026-07-27

**Decision:** The single primary user of V1 is a **young salaried professional, aged 22–35**, with:
- a regular monthly income,
- one or two bank accounts,
- a credit card.

**Their problem:** they struggle to understand where their money goes, how daily habits affect spending, and how to improve savings — without manually analysing financial data.

**Implications:** Income is assumed regular and single-source. Account count is low. Manual analysis is explicitly the thing we remove.

---

**PDR-007 — The persona governs scope**
**Status:** ✅ APPROVED · **Category:** Governance · **Source:** Discovery Session 1, 2026-07-27

**Decision:** PDR-006 drives **all** V1 feature and architecture decisions. **Any feature that does not directly help this user is deferred to a future version.**

**Implications:** This is a rejection test, applied to every proposed feature in every downstream document. A feature that serves a different user is out of V1 regardless of its merit.

---

**PDR-008 — The product is not an expense tracker**
**Status:** ✅ APPROVED · **Category:** Positioning · **Source:** Discovery Session 1, 2026-07-27

**Decision:** The primary goal is **not expense tracking alone**. It is helping users understand **the relationship between their behavior and their financial decisions**, through explainable AI.

**Implications:** Reporting totals and categories is necessary infrastructure, not the value proposition. A V1 that only categorizes and charts spending has failed this decision.

---

### B.3 Discovery Session 1 — Data and ingestion (2026-07-27)

---

**PDR-009 — Ingestion strategy: dual path**
**Status:** ✅ APPROVED · **Category:** Data · **Source:** Discovery Session 1, 2026-07-27

**Decision:** V1 supports **two** data ingestion methods:
1. **Real data upload (primary)** — user-uploaded, bank-exported files.
2. **Synthetic demo data (secondary)** — bundled realistic sample datasets.

---

**PDR-010 — Upload formats**
**Status:** ✅ APPROVED · **Category:** Data · **Source:** Discovery Session 1, 2026-07-27

**Decision:** **CSV** is the supported upload format for V1. **Excel is optional**, to be supported only if such formats prove common among target banks.

**Scope note:** Excel is conditional, not committed. PDF statement parsing is **not** approved and is not in V1.

---

**PDR-011 — Ingestion pipeline responsibilities**
**Status:** ✅ APPROVED · **Category:** Data · **Source:** Discovery Session 1, 2026-07-27

**Decision:** The system must **parse, validate, normalize, and categorize** uploaded transactions into a **standard internal format**.

**Implications:** A canonical internal transaction representation exists and is independent of any source format. All four stages are required; none is optional.

---

**PDR-012 — Purpose and content of synthetic data**
**Status:** ✅ APPROVED · **Category:** Data · **Source:** Discovery Session 1, 2026-07-27

**Decision:** Synthetic datasets must be **realistic** and must represent **different spending behaviors**. They serve three approved purposes:
1. Allowing new users and technical evaluators to explore the application immediately, **without uploading personal financial data**.
2. Providing **consistent datasets for automated testing and demos**.
3. Providing datasets for **AI evaluation**.

**Implications:** Synthetic data is a first-class, tested, maintained subsystem — not throwaway fixtures. Purpose (3) implies the datasets must have known characteristics that AI output can be evaluated against.

---

**PDR-013 — Ingestion abstraction (adapter/port pattern)**
**Status:** ✅ APPROVED · **Category:** Architecture · **Source:** Discovery Session 1, 2026-07-27

**Decision:** The ingestion layer is built behind an **adapter/port abstraction**, so that future integrations (RBI Account Aggregator, Plaid, or others) can be added **without changing the downstream analysis, AI, or reporting modules**.

**Implications:** This is a binding architectural constraint, not a suggestion. Downstream modules must never depend on a source-specific format or a file-upload-specific concept.

---

**PDR-014 — No live banking integrations in V1**
**Status:** ✅ APPROVED · **Category:** Scope · **Source:** Discovery Session 1, 2026-07-27

**Decision:** V1 **intentionally excludes live banking integrations**, to reduce complexity while ensuring the core intelligence engine is production-ready.

**Implications:** No Account Aggregator, no Plaid, no bank APIs, no screen scraping, no email-statement fetching in V1.

---

### B.4 Discovery Session 1 — Intelligence layer (2026-07-27)

---

**PDR-015 — The core intelligence claim** ⭐
**Status:** ✅ APPROVED · **Category:** Intelligence · **Source:** Discovery Session 1, 2026-07-27

**Decision — recorded verbatim as the product's central commitment:**

> *"The platform explains why your spending changed by connecting financial transactions with personal habits and life events, then provides evidence-based recommendations to improve future financial decisions."*

The product's primary value is **explainable behavioral financial intelligence**. It is not an expense tracker and not a forecasting tool.

**Approved illustrative claims** (examples of the *form* of output, not a committed feature list):
- "Restaurant spending increased during weeks when gym sessions were missed."
- ~~"Transportation costs rose because of your vacation period."~~ → **amended by PDR-028**, restated as: *"Transportation costs were higher during your vacation period."*
- "Late-night food delivery is consistently higher on days with less than 6 hours of sleep."

**Amendment note (2026-07-27):** the original second example used causal phrasing ("because of"). **PDR-028** prohibits causal language for correlation-derived claims. The example is restated above in compliant form. The substance of PDR-015 is unchanged; only the illustrative wording is amended.

**Implications:** This is the highest-order decision in the document. Every other decision is subordinate to it. Forecasting is explicitly not the product.

---

**PDR-016 — Composition of the intelligence layer**
**Status:** ✅ APPROVED · **Category:** Intelligence · **Source:** Discovery Session 1, 2026-07-27

**Decision:** The intelligence layer combines six named components:
1. Transaction analysis
2. Habit tracking
3. User-defined life events
4. Statistical correlation
5. Rule-based behavioral analysis
6. Explainable AI

**Implications:** All six are in V1 scope. Notably, this establishes that **habits** and **user-defined life events** are first-class domain entities alongside transactions, and that both **statistical** and **rule-based** analysis exist as distinct mechanisms.

**Dependency resolved:** *how* habit data is acquired is decided by **PDR-029** (manual habit logging only in V1).

---

**PDR-017 — The AI never invents conclusions** ⭐
**Status:** ✅ APPROVED · **Category:** Intelligence · **Source:** Discovery Session 1, 2026-07-27

**Decision:** The AI **never invents conclusions**. Every insight must be **traceable back to supporting transactions, habits, or events stored in the system**.

**Implications:** Traceability is a hard correctness requirement. An insight that cannot be linked to stored source records is a defect, not a lower-quality output. This constrains both the data model (insights reference their evidence) and the AI design.

---

**PDR-018 — Mandatory composition of every recommendation**
**Status:** ✅ APPROVED · **Category:** Intelligence · **Source:** Discovery Session 1, 2026-07-27

**Decision:** Every recommendation must include:
- **Evidence**
- **Reasoning**
- **Supporting data**
- **Confidence level** (where applicable)

**Implications:** These are required fields of the output contract, not presentation choices. A recommendation missing any of the first three cannot be shown.

**Ambiguity flagged:** the qualifier *"where applicable"* on confidence is undefined. See **C-02**.

---

**PDR-019 — Goal of the intelligence output**
**Status:** ✅ APPROVED · **Category:** Intelligence · **Source:** Discovery Session 1, 2026-07-27

**Decision:** The goal is to help users **understand the reasons behind their financial behavior**, not to report spending totals.

---

**PDR-020 — Explainable AI model intent**
**Status:** ✅ APPROVED (as stated intent) · **Category:** Technology · **Source:** Discovery Session 1, 2026-07-27

**Decision:** **Qwen** is the intended model for the explainable AI component.

**Scope note:** Recorded as the approved intent. Hosting (local vs. hosted), model size, serving runtime, structured-output strategy, and behavior when the model is unavailable are **not** decided here. See **D-BLOCK-AI**.

---

### B.5 Discovery Session 1 — Market, regulatory, privacy (2026-07-27)

---

**PDR-021 — Target market and currency**
**Status:** ✅ APPROVED · **Category:** Market · **Source:** Discovery Session 1, 2026-07-27

**Decision:** V1 is designed specifically for the **Indian market**. Currency is **Indian Rupee (INR)**.

**Implications:** Date formats, merchant naming conventions, statement structures, and regulatory framing are all Indian. Other markets are out of V1 scope.

---

**PDR-022 — In-scope transaction sources**
**Status:** ✅ APPROVED · **Category:** Data · **Source:** Discovery Session 1, 2026-07-27

**Decision:** The primary transaction sources the system must handle are: **UPI, bank account statements, debit cards, credit cards, and wallet transactions.**

**Implications:** UPI narration parsing is a core capability, not an edge case. The data model must accommodate multiple instrument types.

---

**PDR-023 — Regulatory positioning** ⭐
**Status:** ✅ APPROVED · **Category:** Regulatory · **Source:** Discovery Session 1, 2026-07-27

**Decision:** The application is an **educational financial intelligence and budgeting tool**.

It **does not provide** investment advice, tax advice, or regulated financial recommendations.

AI-generated insights are **behavioral observations and budgeting suggestions based solely on user-provided data**.

**Implications:** This is a hard boundary. Any feature that would constitute regulated advice is rejected at the PDR level and cannot be reintroduced by a downstream document.

**Ambiguity flagged:** PDR-015 commits to "recommendations" while PDR-023 prohibits "regulated financial recommendations." The reconciling boundary is stated in **C-01** and requires confirmation.

---

**PDR-024 — Data privacy commitments**
**Status:** ✅ APPROVED · **Category:** Privacy · **Source:** Discovery Session 1, 2026-07-27

**Decision:** All uploaded financial data **remains private to the user**. The system is designed with **DPDP Act principles**, specifically:
- **User consent**
- **Data minimization**
- **Transparency**
- **The ability to delete user data**

**Implications:** These four are binding product requirements with user-visible surfaces, not internal policy statements.

---

**PDR-025 — Modularity for future expansion**
**Status:** ✅ APPROVED · **Category:** Architecture · **Source:** Discovery Session 1, 2026-07-27

**Decision:** The architecture must remain modular so that **additional countries, currencies, and banking integrations** can be added in future versions **without redesigning the core analysis engine**.

**Implications:** Currency and locale are modelled concepts, not hardcoded constants — even though only INR and India are supported in V1.

---

**PDR-026 — V2 directional intent: RBI Account Aggregator**
**Status:** ✅ APPROVED (as direction, not commitment) · **Category:** Roadmap · **Source:** Discovery Session 1, 2026-07-27

**Decision:** Version 2 **may** integrate with the RBI Account Aggregator framework.

**Implications:** Recorded so that PDR-013's abstraction is designed with a concrete future consumer in mind. Carries no V1 obligation beyond that.

---

### B.6 Discovery Session 2 — Rulings (2026-07-27)

---

**PDR-027 — The behavioral recommendation boundary** ⭐
**Status:** ✅ APPROVED · **Category:** Regulatory · **Source:** Discovery Session 2, 2026-07-27
**Resolves:** C-01 · **Qualifies:** PDR-015, PDR-023

**Decision:**

**Permitted.** The application **may** provide **behavioral budgeting recommendations** based on the user's own spending and habits.

**Prohibited.** The application **must never** provide regulated financial advice, including any recommendation involving:

| Prohibited domain |
|---|
| Stocks |
| Mutual funds |
| ETFs |
| Insurance |
| Loans |
| Tax planning |
| Investment products |

**Implications:** This is the operational test engineers, prompt authors, and reviewers apply. The permitted domain is bounded by *the user's own spending and habits*. The prohibited list is binding by category — a recommendation touching any listed domain is rejected regardless of framing, hedging, or how it is labelled in the UI.

**Enforcement note:** because PDR-031 permits the LLM to answer user questions, this boundary must be enforced at runtime, not only at design time — a user may *ask* a prohibited question directly. The enforcement mechanism is undecided; see **D-28**.

---

**PDR-028 — Correlation language standard** ⭐
**Status:** ✅ APPROVED · **Category:** Intelligence · **Source:** Discovery Session 2, 2026-07-27
**Resolves:** D-23 · **Amends:** PDR-015 (illustrative wording only)

**Decision:** Insights must use **correlational language**, not causal language.

**Approved vocabulary:**
- "associated with"
- "correlated with"
- "observed during"
- "tended to occur alongside"

**Prohibited:** causal phrasing such as *"because of"*, **unless supported by deterministic evidence.**

**Implications:** This governs **every user-facing string that states a relationship** — LLM-generated prose, templated copy, chart labels, notification text, and summary headlines alike. It is not solely a prompt-engineering concern; static copy is equally bound.

**Scope note:** the phrase *"deterministic evidence"* requires a testable definition before it can be enforced. See **C-06**.

---

**PDR-029 — Habit data collection method for V1** ⭐
**Status:** ✅ APPROVED · **Category:** Data · **Source:** Discovery Session 2, 2026-07-27
**Resolves:** D-01 · **Qualifies:** PDR-016

**Decision:** Version 1 uses **manual habit logging only.**

Future versions may integrate wearable devices or external health platforms.

**Implications:**
- Habits are a **user-entered, first-class domain entity** with a dedicated capture surface in the product and a dedicated table in the schema.
- **No derivation of habits from transaction data in V1.** Inferring gym attendance from gym transactions, or sleep from transaction timestamps, is out of scope under this decision.
- The product requires **ongoing user effort** to produce its core value (PDR-015). Onboarding, empty states, and re-engagement must be designed with that dependency understood.
- Wearable/health-platform integration is a stated V2 direction; the habit capture layer should not be designed in a way that forecloses it.

**Consequential decisions now open:** habit taxonomy (**D-24**), logging granularity and retroactive backfill (**D-25**), missing-data semantics (**D-26**), and logging drop-off handling (**D-27**).

---

**PDR-030 — Data sufficiency gate and honest empty state** ⭐
**Status:** ✅ APPROVED · **Category:** Intelligence · **Source:** Discovery Session 2, 2026-07-27
**Resolves:** D-04 (in principle) · **Partially resolves:** D-02

**Decision:** Behavioral insights **require sufficient historical data.**

Before enough history exists, the application must **clearly state that additional data is required** before reliable behavioral insights can be generated.

**Implications:**
- **"Insufficient data" is a designed, user-visible product state** — not an error, not a blank screen, and not a placeholder chart.
- The system is **required to withhold** behavioral insights rather than emit weak ones. Silence is mandated behavior, not a fallback.
- This applies specifically to **behavioral** insights. Whether deterministic factual output (totals, categories, recurring items) is available before the gate is met is a PRD-level design question, not restricted by this decision.

**Scope note — what this decision does NOT set:**
1. The **numeric thresholds** defining "sufficient" (minimum observations, minimum time span, minimum effect size). See **D-02**.
2. **Correction for testing many hypotheses simultaneously.** This is a distinct statistical risk from insufficient sample size — a user with ample history who is tested across many habit/category pairs will still surface coincidental findings. Not addressed by this ruling. See **D-02**.

---

**PDR-031 — AI authority model** ⭐
**Status:** ✅ APPROVED · **Category:** Intelligence / Architecture · **Source:** Discovery Session 2, 2026-07-27
**Resolves:** D-03 · **Enforces:** PDR-017

**Decision:**

**The analysis engine is the source of truth.**

The LLM **may**:
- reason over **structured analytical outputs** to explain findings,
- answer user questions.

The LLM **must not**:
- fabricate numerical results,
- produce unsupported behavioral conclusions.

**Implications:**
- The LLM sits **strictly downstream** of the analysis engine and consumes its structured outputs. It does not substitute for analysis, and it does not derive conclusions from raw transaction data.
- **Reasoning over analytical output is permitted; originating conclusions is not.** The distinction is the enforcement target: the model may combine, contextualize, and explain what the engine computed, but every quantitative claim and every behavioral conclusion must exist in the engine's output first.
- All numbers presented to a user originate from the analysis engine and must be reconstructible from it.

**Scope notes:**
1. The **enforcement mechanism** — how "must not fabricate" is mechanically verified rather than merely instructed — is undecided. See **D-20**.
2. *"Answer user questions"* implies a **conversational Q&A surface**, which was not previously in scope and materially expands V1. See **C-07**.

---

### B.7 Provisional decisions — 🟠 DELEGATED AUTHORITY, AWAITING RATIFICATION

> **Status of this subsection.** On 2026-07-27 the product owner instructed *"continue for everything."* I have interpreted that as delegated authority to rule on the outstanding open decisions so that downstream documentation could proceed.
>
> **These are my decisions, not the owner's.** Each is marked 🟠 PROVISIONAL. They are binding on downstream documents so work can proceed, but they are the first thing to revisit — a single ratification pass (§K) confirms or overturns all 16.
>
> **Engineering-only decisions are NOT recorded here.** D-10 … D-22, D-28 and D-29 are implementation choices and belong in `docs/11_Architecture_Decision_Records/`. The PDR records product decisions only.

---

**PDR-032 — Confidence disclosure** · 🟠 PROVISIONAL · *Resolves C-02*

Confidence is **mandatory** on any claim derived from statistical inference, and **omitted** on claims that are direct arithmetic over stored records (where a score would falsely imply doubt about a correct number).

**When confidence is low, the system must say so explicitly** rather than presenting the claim unqualified. Low-confidence claims that clear the PDR-043 gates are shown with a visible qualifier; claims that fail the gates are not shown at all.

*Rationale: makes PDR-018's "where applicable" testable. Second paragraph derives from the owner's stated AI Engineering Principles (2026-07-27 bootstrap brief).*

---

**PDR-033 — Deletion semantics** · 🟠 PROVISIONAL · *Resolves C-03*

Deletion is **irreversible and cascading**. Deleting source data removes all derived habits, signals, insights, evidence links, and cached AI output derived from it. Soft-delete flags do not satisfy PDR-024.

Two granularities: **delete a data source** (one uploaded statement and everything derived from it) and **delete the account** (all user data, unrecoverable).

---

**PDR-034 — Scope of "private to the user"** · 🟠 PROVISIONAL · *Resolves C-04*

User data is **never** used for model training, **never** aggregated or benchmarked across users, and **never** shared with or sold to third parties. No cross-user computation of any kind exists in the system.

---

**PDR-035 — Account model** · 🟠 PROVISIONAL · *Resolves C-05*

V1 is a **multi-user application with individual authenticated accounts** and strict per-user data isolation enforced at the data-access layer. Not a single-user self-hosted tool.

---

**PDR-036 — Definition of "deterministic evidence"** · 🟠 PROVISIONAL · *Resolves C-06, qualifies PDR-028*

Causal language is permitted **only for arithmetic decomposition** — where the causal link is an accounting identity rather than a statistical inference.

**The test:** *can the claim be proven by summing stored rows alone?*
- **Yes** → causal language permitted. *"Your total rose ₹40,000 because an annual premium was debited on 12 June."*
- **No** (requires comparing groups or inferring a relationship) → correlational language mandatory per PDR-028.

---

**PDR-037 — Conversational Q&A scope** · 🟠 PROVISIONAL · *Resolves C-07, qualifies PDR-031*

**Reading (b) — Bounded Q&A.** V1 includes a question-answering surface, constrained as follows:

- Questions are answered **only** from the analysis engine's structured outputs. The LLM never queries raw transactions to answer.
- **Single-turn.** No conversational memory or multi-turn state in V1. Each question is independent.
- Out-of-scope questions receive an explicit **refusal**, not a best-effort answer.
- The PDR-027 prohibited-advice boundary is enforced **at runtime** on every question.

*Rationale: PDR-031 explicitly permits answering user questions, so reading (a) would contradict an approved decision. Reading (c) — open conversation — multiplies regulatory and hallucination exposure for a V1. Bounded single-turn honors the approved text at the lowest defensible risk.*

---

**PDR-038 — Habit taxonomy** · 🟠 PROVISIONAL · *Resolves D-24*

V1 supports a **fixed, system-defined set of six habits.** User-defined custom habits are **not** in V1.

| Habit | Type | Values |
|---|---|---|
| Sleep duration | Numeric | Hours, 0.0–24.0 |
| Exercise | Boolean | Occurred / did not occur |
| Home-cooked meals | Count | 0–3 |
| Stress level | Ordinal | 1–5 |
| Alcohol consumption | Boolean | Occurred / did not occur |
| Work mode | Categorical | Office / Remote / Leave |

*Rationale: a fixed set bounds the hypothesis space, which is the single most effective control on the multiplicity risk in PDR-043. User-defined habits would make the number of tested hypotheses unbounded and per-user, defeating any fixed correction. It also gives every habit known semantics and a known value type, which correlation analysis requires. Cost: less flexibility. Accepted — a V1 that produces six trustworthy relationships beats one that produces twenty unreliable ones.*

---

**PDR-039 — Habit logging model** · 🟠 PROVISIONAL · *Resolves D-25*

- **One daily check-in record per user per date**, capturing all six habits in a single interaction — not six separate log entries.
- **Partial check-ins are permitted.** Individual habit fields may be left blank within a submitted check-in.
- **Retroactive backfill permitted up to 30 days.** Beyond 30 days, recall is unreliable enough that the data would degrade rather than improve analysis.
- Check-ins are editable; edits invalidate any insight derived from the affected window, which is then recomputed.

*Rationale for the single daily record: it reduces the ongoing user burden PDR-029 creates to one interaction per day, and — critically — it makes "the user logged today" an explicit, queryable fact, which is what makes PDR-040 implementable.*

---

**PDR-040 — Missing habit data semantics** ⭐ · 🟠 PROVISIONAL · *Resolves D-26*

**A date with no check-in record means `UNKNOWN`. It never means the habit did not occur.**

Three binding consequences:

1. **Explicit negatives are recordable.** A submitted check-in with `exercise = false` is a positive assertion that exercise did not occur. Absence of a record is categorically different from a recorded negative, and the schema must distinguish them.
2. **Complete-case analysis.** `UNKNOWN` observations are **excluded** from correlation analysis — never imputed, never defaulted, never treated as zero or false.
3. **Coverage floor.** Behavioral insights require **≥60% of days in the analysis window to have a check-in.** Below that, no behavioral insight is generated regardless of what the remaining data appears to show. Excluded-day counts are surfaced in the insight's evidence.

*Rationale — this is the highest-risk decision in the product. The naive schema (a boolean column defaulting to false) silently encodes "not logged" as "did not happen." A user who logs gym visits only when they go would appear to have skipped the gym on every unlogged day, manufacturing a correlation that does not exist while every individual number remains technically traceable — satisfying PDR-017 in letter while violating it in substance. No downstream care can repair this if the schema gets it wrong, which is why it is a product decision and not an implementation detail.*

---

**PDR-041 — Logging drop-off handling** · 🟠 PROVISIONAL · *Resolves D-27*

When check-in coverage falls below the PDR-040 floor for the current window:

1. Behavioral insights **pause**. They are not degraded, and stale ones are not re-shown as current.
2. Previously generated insights remain viewable, **explicitly timestamped** with the window they describe.
3. The user is shown the coverage gap and what closing it would unlock — consistent with PDR-030's honest empty state.
4. Deterministic transaction analysis (totals, categories, recurring items) is **unaffected** and remains fully available.

---

**PDR-042 — Life event model** · 🟠 PROVISIONAL · *Resolves D-08*

A life event is a **user-declared, dated annotation** used as analysis context.

| Field | Type | Notes |
|---|---|---|
| Event type | Enum | Travel, Illness, Job change, Relocation, Festival/Celebration, Family event, Other |
| Title | Free text | Short label |
| Start date | Date | Required |
| End date | Date | Nullable — null means a point-in-time event |
| Notes | Free text | Optional |

Life events **segment** analysis windows (comparing "during" vs. "outside" an event period). They are **never** treated as causes — PDR-028's correlational language applies to every life-event claim, subject to the PDR-036 arithmetic exception.

---

**PDR-043 — Statistical thresholds** · 🟠 PROVISIONAL · *Resolves D-02*

Every behavioral (T3) insight must clear **all five** gates:

| # | Gate | Threshold |
|---|---|---|
| 1 | Transaction history | ≥ 8 weeks |
| 2 | Observations per compared group | ≥ 6 |
| 3 | Habit check-in coverage | ≥ 60% of window (PDR-040) |
| 4 | Effect size | ≥ ₹500/week **and** ≥ 15% relative difference |
| 5 | Multiplicity correction | Benjamini–Hochberg FDR at q = 0.10 across all hypotheses tested in the run |

**Stability:** an insight is labelled *Tentative* on first detection and promoted to *Established* only after persisting into a subsequent analysis window.

*Rationale: gates 1–3 address sample sufficiency (PDR-030). Gate 4 addresses the separate problem that a statistically detectable difference can be financially irrelevant. Gate 5 addresses multiplicity, which PDR-030 explicitly did not cover — with six habits across roughly fifteen categories, ~90 hypotheses are tested per run, of which several would appear significant by chance without correction. Thresholds are initial values, to be tuned against the synthetic evaluation datasets required by PDR-012.*

---

**PDR-044 — Insight feedback capture** · 🟠 PROVISIONAL · *Resolves D-05*

Every surfaced insight carries user feedback controls: **Useful**, **Not useful**, and **This isn't true**.

"This isn't true" is treated as a **defect report**, not a preference signal — each one is triaged to a root cause. Feedback is stored per insight and is the primary input to PDR-045.

---

**PDR-045 — Success metrics** · 🟠 PROVISIONAL · *Resolves D-06*

| Type | Metric | Target |
|---|---|---|
| **North Star** | **Insight Trust Rate** — share of surfaced insights marked Useful or true | **≥ 70%** |
| Counter-metric | **False Insight Rate** — share marked "This isn't true" | **< 5%** (hard bound) |
| Counter-metric | Silent ingestion failures (wrong sign, wrong date, duplicate) | **0** (invariant) |
| Leading | Time to First Useful Insight | Measured |
| Leading | Habit check-in coverage rate | Measured |
| Leading | Evidence drill-down rate | Measured — high is good; it means users verify us and find us correct |

*Rationale for the North Star: engagement metrics reward confident nonsense — a wrong but provocative insight gets clicks. Trust Rate is the only candidate that degrades when the system over-claims, which is the specific failure PDR-017, PDR-030 and PDR-043 exist to prevent.*

---

**PDR-046 — V1 non-goals** · 🟠 PROVISIONAL · *Resolves D-07*

Excluded from V1, in addition to all exclusions in §E:

| Excluded | Reason |
|---|---|
| Budgets, envelopes, spending limits | Constraint-setting is a different product philosophy from explanation (PDR-008). Doing both makes us mediocre at each. |
| Financial goal setting and tracking | Meaningless before the present can be explained. |
| Net worth / asset tracking | Adjacent to regulated territory (PDR-027) and outside the PDR-006 persona's stated problem. |
| Native mobile applications | Distribution decision, not a product decision. Web responsive in V1. |
| Peer comparison / benchmarking | Requires cross-user computation, forbidden by PDR-034. |
| Bill payment or any money movement | Payments licensing. Different company. |
| Multi-turn conversational assistant | PDR-037 permits single-turn Q&A only. |

---

**PDR-047 — Insight volume and ranking** · 🟠 PROVISIONAL · *Resolves D-09*

**Maximum 5 insights** surfaced per analysis period. Ranked by `effect size × confidence × novelty`, where novelty penalizes insights substantially similar to ones already shown and acknowledged.

*Rationale: insight quantity is inversely related to perceived quality. Twenty insights train the user to scroll; five train them to read.*

---

## C. Derived clarifications — ✅ ALL RESOLVED

> **Status as of PDR v1.0: every item in this section is closed.** Entries below are retained unedited for history per the §G append-only rule.

| Item | Resolution | Authority |
|---|---|---|
| C-01 | Recommendation boundary defined | **PDR-027** ✅ owner-approved |
| C-02 | Confidence disclosure rules defined | **PDR-032** 🟠 provisional |
| C-03 | Deletion is irreversible and cascading | **PDR-033** 🟠 provisional |
| C-04 | No training, no cross-user aggregation, no sharing | **PDR-034** 🟠 provisional |
| C-05 | Multi-user authenticated accounts | **PDR-035** 🟠 provisional |
| C-06 | "Deterministic evidence" = arithmetic decomposition | **PDR-036** 🟠 provisional |
| C-07 | Bounded single-turn Q&A (reading b) | **PDR-037** 🟠 provisional |

*Original entries follow.*

---

> These follow logically from Section B but were **not explicitly stated by you**. Per your instruction, I am not treating them as approved. Each needs a yes/no.

---

**C-01 — The recommendation boundary** — ✅ **RESOLVED 2026-07-27 → promoted to PDR-027.**

---

**C-02 — Meaning of "confidence level (where applicable)"** *(qualifies PDR-018)*

The qualifier is currently undefined, which makes PDR-018 untestable.

**Proposed reading:** confidence is **mandatory** for any claim derived from statistical correlation or inference, and **omitted** for claims that are direct arithmetic over stored records (where a confidence score would be misleading — the number is simply correct).

**Confirm?** ☐ Yes ☐ No ☐ Modify

---

**C-03 — Meaning of "ability to delete user data"** *(qualifies PDR-024)*

**Proposed reading:** deletion is **irreversible and cascading** — removing source transactions also removes derived habits, signals, insights, and any cached AI output derived from them. Not a soft-delete flag.

**Confirm?** ☐ Yes ☐ No ☐ Modify

---

**C-04 — Scope of "private to the user"** *(qualifies PDR-024)*

**Proposed reading:** user data is never used for model training, never aggregated or benchmarked across users, and never shared with or sold to third parties.

**Confirm?** ☐ Yes ☐ No ☐ Modify

---

**C-05 — Multi-tenancy assumption** *(implied by PDR-006, PDR-024)*

Individual user accounts and data isolation are implied by "private to the user," but the account model was never stated.

**Proposed reading:** V1 is a **multi-user application with individual authenticated accounts** and strict per-user data isolation — not a single-user self-hosted tool.

**Confirm?** ☐ Yes ☐ No ☐ Modify

---

**C-06 — What qualifies as "deterministic evidence"?** *(qualifies PDR-028)* — **NEW, from Session 2**

PDR-028 permits causal language *"when supported by deterministic evidence"* but does not define the term, which makes the rule unenforceable at review time.

**Proposed reading:** causal language is permitted **only for arithmetic decomposition of an amount** — where the causal link is an accounting identity rather than a statistical inference.

| Causal language permitted (deterministic) | Causal language prohibited (correlational) |
|---|---|
| "Your total rose ₹40,000 **because** an annual insurance premium was debited on 12 June." *(the transaction arithmetically accounts for the increase)* | "Your food spending rose **because** you skipped the gym." |
| "This category increased **because** a new recurring payment of ₹899 started in March." | "You spent more **because** you were stressed." |

The test: *can the claim be proven by summing stored rows alone?* If yes, causal language is permitted. If it requires comparing groups or inferring a relationship, correlational language is mandatory.

**Confirm?** ☐ Yes ☐ No ☐ Modify

---

**C-07 — Does "answer user questions" put a conversational Q&A surface in V1?** ⭐ *(qualifies PDR-031)* — **NEW, from Session 2**

PDR-031 states the LLM "may … answer user questions." This capability was not previously in scope, and its inclusion materially changes V1 — it adds a chat surface, conversational state, an unbounded input space, and a runtime enforcement burden for PDR-027's prohibited-advice list (a user can simply *ask* "should I buy mutual funds?").

**Three readings are possible. This needs an explicit ruling, not an assumption:**

| Reading | Meaning | Consequence |
|---|---|---|
| **(a) Narrow** | The phrase describes the LLM's *permitted role*, not a V1 feature. No chat surface in V1. | Smallest scope. Q&A deferred to a later version. |
| **(b) Bounded** | V1 includes Q&A, but only over the analysis engine's structured outputs, with a constrained question space and refusal behavior for out-of-scope asks. | Moderate scope increase. Requires D-28 enforcement design. |
| **(c) Open** | V1 includes general conversational Q&A over the user's financial data. | Largest scope increase. Highest regulatory and hallucination exposure. |

**Ruling required:** ☐ (a) ☐ (b) ☐ (c)

---

## D. OPEN DECISIONS — ✅ ALL CLOSED

> **Status as of PDR v1.0: the register is empty.** Every open decision is either promoted into Section B or reassigned to an ADR. Entries below are retained unedited for history per the §G append-only rule.

**Product decisions → promoted to §B.7:**

| Item | → | Item | → |
|---|---|---|---|
| D-01 Habit acquisition | PDR-029 ✅ | D-08 Life event model | PDR-042 🟠 |
| D-02 Statistical thresholds | PDR-043 🟠 | D-09 Insight ranking | PDR-047 🟠 |
| D-03 AI authority | PDR-031 ✅ | D-23 Causal language | PDR-028 ✅ |
| D-04 Cold start | PDR-030 ✅ | D-24 Habit taxonomy | PDR-038 🟠 |
| D-05 Insight feedback | PDR-044 🟠 | D-25 Logging granularity | PDR-039 🟠 |
| D-06 Success metrics | PDR-045 🟠 | D-26 Missing-data semantics | PDR-040 🟠 |
| D-07 Non-goals | PDR-046 🟠 | D-27 Logging drop-off | PDR-041 🟠 |

**Engineering decisions → reassigned to `docs/11_Architecture_Decision_Records/`:**

| Item | ADR | Item | ADR |
|---|---|---|---|
| D-10 DB engine & ORM strategy | ADR-002 | D-19 Model deployment | ADR-008 |
| D-11 Money representation | ADR-003 | D-20 Provenance enforcement | ADR-009 |
| D-12 Bank CSV formats | ADR-004 | D-21 Degraded mode | ADR-009 |
| D-13 Categorization approach | ADR-005 | D-22 Merchant dictionary | ADR-005 |
| D-14 Deduplication | ADR-006 | D-28 Advice-boundary guard | ADR-010 |
| D-15 Date & timezone semantics | ADR-003 | D-29 Statistical methods | ADR-007 |
| D-16 Authentication | ADR-011 | D-17 Frontend stack | ADR-012 |
| D-18 Deployment topology | ADR-013 | | |

*Original entries follow.*

---

> Nothing in this section is approved, and nothing here may be implemented or cited by any downstream document. Items are promoted into Section B only by your explicit approval.
>
> **Note (v0.2, historical):** every proposal in the original Product Vision draft that did not appear in Section B was un-approved and registered here. That document was subsequently rewritten against this frozen baseline and now lives at `docs/01_Product_Vision.md` (§H).

### D-RESOLVED — Closed by Discovery Session 2

| ID | Open decision | Resolution |
|---|---|---|
| ~~D-01~~ ⭐ | How is habit data acquired? | ✅ **PDR-029** — manual habit logging only in V1. *Spawned D-24 … D-27.* |
| ~~D-03~~ ⭐ | May the AI reason over raw data, or only render pre-computed conclusions? | ✅ **PDR-031** — analysis engine is source of truth; LLM reasons over its structured outputs. *Spawned C-07; enforcement remains D-20.* |
| ~~D-04~~ | Cold-start behavior | ✅ **PDR-030** in principle — insufficient-data state is mandated and user-visible. Specific screen content is PRD design work, not a blocking decision. |
| ~~D-23~~ | Causal vs. correlational language | ✅ **PDR-028** — correlational language mandated. *Definition of the deterministic exception remains C-06.* |

### D-BLOCK-PRD — Still blocking the PRD

| ID | Open decision | Why it blocks |
|---|---|---|
| **D-24** ⭐ | **Habit taxonomy.** Which habits can be logged in V1 — a fixed system-defined set (sleep, exercise, meals at home, commute, alcohol…), user-defined custom habits, or both? | Determines the schema, the logging UI, and whether the correlation engine works over a known dimension set or an open one. An open set makes the multiplicity problem (D-02) substantially worse. |
| **D-25** ⭐ | **Logging granularity and backfill.** Is a habit logged daily, per-occurrence, or weekly? What value type — boolean, count, duration, scale? Can a user log retroactively, and how far back? | Directly determines the observation count feeding PDR-030's sufficiency gate. Backfill is the difference between insights in week 2 and insights in month 3. |
| **D-26** ⭐ | **Missing habit data semantics.** When a day has no habit log, does that mean *the habit did not occur* or *the user did not log*? | **The highest-risk statistical decision in the product.** Treating "not logged" as "did not happen" biases every correlation: a user who logs gym visits only when they go will appear to have skipped the gym on every unlogged day, manufacturing correlations that do not exist. This threatens PDR-017 and PDR-030 directly, and no amount of downstream care can repair a wrong ruling here. |
| **D-27** | **Logging drop-off handling.** What happens when a user stops logging for a period — do insights degrade, pause, or carry a staleness warning? | PDR-029 makes the product's core value dependent on sustained manual effort. Partial-logging periods will be common and must have defined behavior. |
| **D-05** | **Insight feedback capture.** Does V1 let users mark insights true / false / useful? | The only mechanism for measuring whether PDR-015 is being delivered. |
| **D-06** | **Success metrics.** How do we measure whether the intelligence layer is good? | Without this, V1 quality is unfalsifiable. |
| **D-07** | **Explicit V1 non-goals.** Beyond PDR-014, PDR-023 and PDR-027, no exclusions are approved. Candidates needing a ruling: budgets/spending limits, goal tracking, net worth, mobile app, peer comparison. *(Chat interface is now governed by C-07.)* | PDR-007 gives a rejection *test* but no rejection *list*. Downstream docs will otherwise re-litigate each candidate. |
| **D-08** | **Life event data model.** What fields does a user-defined life event carry (type, date range, free text, category)? | PDR-016 makes it a first-class entity with no defined shape. Should be decided alongside D-24/D-25 for consistency. |
| **D-09** | **Insight volume and ranking.** How many insights surface at once, and how are they prioritized? | Affects perceived quality more than generation accuracy does. |

### D-BLOCK-ARCH — Blocking Architecture / Database

| ID | Open decision |
|---|---|
| **D-10** | Database engine, migration tooling, async vs. sync SQLAlchemy. PDR-003 fixes only the ORM. |
| **D-11** | Monetary representation. Recommendation on record: integer minor units (paise), never floating point. |
| **D-12** | Which specific Indian bank CSV formats are supported at launch, and the fallback when a format is unrecognized. |
| **D-13** | Categorization approach (rules / embeddings / trained classifier / layered) and how its confidence score is produced. |
| **D-14** | Deduplication and idempotency rules for overlapping statement re-uploads. |
| **D-15** | Date and timezone semantics: transaction date vs. value date vs. statement date; IST handling. |
| **D-16** | Authentication mechanism and session model (dependent on C-05). |
| **D-17** | Frontend stack. The `frontend/` directory exists; nothing about it is decided. |
| **D-18** | Deployment target and hosting. The `docker/` directory exists; nothing about it is decided. |

### D-BLOCK-AI — Blocking AI Design

| ID | Open decision |
|---|---|
| **D-02** ⭐ | **Numeric thresholds for the PDR-030 sufficiency gate, and multiplicity correction.** PDR-030 approves the *principle* that sufficient history is required and that the app must say so honestly. Still open: (a) minimum observations per compared group; (b) minimum time span; (c) minimum effect size in rupees; (d) **correction for testing many hypotheses simultaneously**; (e) stability across periods before an insight is promoted. **Note:** (d) is a *distinct* risk from (a) — sample sufficiency does not address multiplicity. A user with ample history tested across 10 habits × 15 categories is testing 150 hypotheses, of which roughly 7–8 will appear significant by chance alone. PDR-030 does not cover this. |
| **D-19** | Qwen deployment: local vs. hosted, model size, serving runtime. (PDR-020 fixes only the model family.) |
| **D-20** ⭐ | The exact structured input contract handed to the model, and how we **mechanically verify** the output introduced no number or conclusion absent from that input — the enforcement mechanism for PDR-017 and PDR-031. Stating the rule is not enforcing it. |
| **D-21** | Degraded-mode behavior when the model is unavailable or its output fails validation. PDR-031 makes the engine the source of truth, which implies insights must remain available in structured form with prose degraded — to be confirmed. |
| **D-22** | Whether a curated Indian merchant dictionary is needed at launch for merchant normalization. |
| **D-28** ⭐ | **Runtime enforcement of the PDR-027 prohibited-advice boundary.** Because PDR-031 permits the LLM to answer user questions, a user can directly ask for prohibited advice ("should I buy an ELSS fund?"). Needs a defined refusal behavior and a mechanism that does not rely solely on prompt instructions. *Scope depends on the C-07 ruling — reading (a) reduces this to design-time review only.* |
| **D-29** | **Statistical method for correlation analysis.** Which test(s) apply given the data shapes chosen in D-24/D-25 (binary habit vs. continuous spend, small n, non-normal distributions), and how the resulting confidence maps to the user-facing confidence level required by PDR-018. |

---

## E. Approved exclusions

> Only exclusions you explicitly stated. Anything else believed to be out of scope must first be approved via **D-07**.

| Excluded from V1 | Authority |
|---|---|
| Live banking integrations (Account Aggregator, Plaid, bank APIs) | PDR-014 |
| Investment advice | PDR-023 |
| Tax advice | PDR-023 |
| Regulated financial recommendations | PDR-023 |
| Recommendations involving **stocks, mutual funds, ETFs, insurance, loans, tax planning, or investment products** | PDR-027 |
| **Causal language** for correlation-derived claims (permitted only with deterministic evidence) | PDR-028 |
| **Automatic derivation of habits from transaction data** | PDR-029 (manual logging only in V1) |
| **Wearable device and external health platform integration** | PDR-029 (stated V2 direction) |
| **Behavioral insights generated before sufficient history exists** | PDR-030 |
| **LLM-originated numbers or behavioral conclusions** | PDR-031 |
| Markets outside India | PDR-021 |
| Currencies other than INR | PDR-021 |
| PDF statement parsing | PDR-010 (CSV approved; Excel conditional; PDF not approved) |

---

## F. Traceability rules

Every document below the PDR must comply with the following.

1. **Traceability section required.** Each downstream document ends with a table mapping its major sections to the PDR IDs that authorize them.
2. **Inline citation.** Any statement of scope, constraint, or product behavior cites its decision inline, e.g. *"Ingestion is abstracted behind a port (PDR-013)."*
3. **No orphan content.** Content that cannot cite a PDR ID is either removed or raised as a new Section D entry. It does not stay in the document as an unmarked assumption.
4. **No contradiction.** A downstream document may not narrow, widen, or reinterpret an approved decision. If a decision appears wrong once implementation detail is understood, that is an amendment request (§G) — not a local override.
5. **Pending items are marked.** If a document must discuss an unapproved option, it is labelled `🟡 PENDING — D-NN, not approved` at the point of use.

**Required traceability table format:**

| Document section | Authorizing PDR ID(s) |
|---|---|
| 3.2 Statement upload | PDR-009, PDR-010, PDR-011 |

---

## G. Change control

**Before approval (now):** this document is freely editable. Correct, challenge, and reshape it.

**After approval:** the PDR is **frozen**. From that point:

1. **Append-only.** Approved entries are never silently edited. Typos and clarifications that do not alter meaning may be corrected with a note.
2. **Amendments are numbered.** A change is recorded as a new decision (`PDR-0NN`) that explicitly states which ID it supersedes. The superseded entry is marked ⛔ SUPERSEDED with a forward reference — never deleted.
3. **Version increments.** Baseline changes bump the PDR version. Downstream documents record which PDR version they were written against.
4. **Impact assessment required.** An amendment request must state which downstream documents it invalidates.
5. **A frozen decision is not reopened by implementation inconvenience.** Difficulty is a reason to discuss an amendment, not a reason to quietly deviate.

---

## H. Document status ledger

| Document | Path | Status | Notes |
|---|---|---|---|
> Canonical register is `docs/INDEX.md`. This table is a summary; where the two differ, INDEX.md is correct.

| Document | Path | Status | Notes |
|---|---|---|---|
| **PDR** | `docs/00_Product_Decisions_Record.md` | 🟡 **DRAFT — awaiting approval** | This document. |
| Product Vision | `docs/01_Product_Vision.md` | 🔴 **DRAFT — NOT AUTHORITATIVE** | Written before the PDR existed. Contains un-approved proposals now registered in Section D (chiefly D-02, D-06, D-07); its §5 habit proposal is overruled by PDR-029. **Must not be cited.** To be rewritten from the frozen PDR. |
| PRD | `docs/02_PRD.md` | Not started | **Blocked by C-07, D-24, D-25, D-26, D-05, D-06, D-07, D-08.** See §J. |
| SRS | `docs/03_SRS.md` | Not started | Blocked by PRD. |
| System Architecture | `docs/04_System_Architecture.md` | Not started | Blocked by D-BLOCK-ARCH. |
| Database Design | `docs/05_Database_Design.md` | Not started | Blocked by Architecture; schema shape depends on D-24, D-25, D-26, D-08. |
| API Design | `docs/06_API_Design.md` | Not started | Blocked by Architecture. |
| AI Architecture | `docs/07_AI_Architecture.md` | Not started | Blocked by D-BLOCK-AI and by C-07. |
| UI / UX | `docs/08_UI_UX.md` | Not started | Blocked by PRD. |
| Testing Strategy | `docs/09_Testing_Strategy.md` | Not started | Blocked by SRS. |
| Deployment | `docs/10_Deployment.md` | Not started | Blocked by Architecture. |
| ADRs | `docs/11_Architecture_Decision_Records/` | Directory created, empty | First ADR expected at Architecture phase. |
| Future Roadmap | `docs/12_Future_Roadmap.md` | Not started | Seeded by PDR-026 (V2 Account Aggregator) and PDR-029 (V2 wearables). |

---

## I. Approval

**To freeze this baseline, the following are required:**

1. Confirmation that Section B accurately and completely records your decisions — including anything I recorded that you did not intend, or omitted that you did.
2. A ruling on each Section C item (C-01 … C-05).
3. Acknowledgement that Section D carries no authority until items are individually promoted.

**Approved by:** ______________________
**Date:** ______________________
**Frozen version:** ______________________

---

## J-bis. Ratification register — ⚠️ ACTION REQUIRED

> **Cross-reference note:** this section is cited throughout the documentation set as **"PDR §K"**. It is placed here, ahead of the historical §J, because it is the only section requiring action. The §K label is retained as the stable identifier.

<a id="section-k"></a>

> The 16 decisions in §B.7 were made under delegated authority ("continue for everything", 2026-07-27). They are binding on downstream documents so work could proceed, but they are **mine, not the owner's**. This is the single pass that confirms or overturns them.

| PDR | Decision | Ratify? |
|---|---|---|
| **PDR-040** ⭐ | Unlogged day = UNKNOWN; complete-case analysis; 60% coverage floor | ☐ ✔ ☐ ✘ |
| **PDR-038** ⭐ | Fixed set of 6 habits; no user-defined habits in V1 | ☐ ✔ ☐ ✘ |
| **PDR-037** ⭐ | Bounded, single-turn Q&A (not open conversation, not zero) | ☐ ✔ ☐ ✘ |
| **PDR-043** ⭐ | 5 statistical gates incl. BH-FDR at q=0.10 | ☐ ✔ ☐ ✘ |
| PDR-039 | Daily check-in; partial allowed; 30-day backfill limit | ☐ ✔ ☐ ✘ |
| PDR-041 | Insights pause below coverage floor; deterministic analysis unaffected | ☐ ✔ ☐ ✘ |
| PDR-042 | Life event model — 7 types, date range, notes | ☐ ✔ ☐ ✘ |
| PDR-044 | Three-way insight feedback; "isn't true" = defect report | ☐ ✔ ☐ ✘ |
| PDR-045 | North Star = Insight Trust Rate ≥70%; False Insight Rate <5% | ☐ ✔ ☐ ✘ |
| PDR-046 | Non-goals: budgets, goals, net worth, mobile, peer comparison, payments | ☐ ✔ ☐ ✘ |
| PDR-047 | Max 5 insights per period; effect × confidence × novelty ranking | ☐ ✔ ☐ ✘ |
| PDR-032 | Confidence mandatory on inference, omitted on arithmetic | ☐ ✔ ☐ ✘ |
| PDR-033 | Hard cascading deletion at source and account granularity | ☐ ✔ ☐ ✘ |
| PDR-034 | No training, no cross-user aggregation, no third-party sharing | ☐ ✔ ☐ ✘ |
| PDR-035 | Multi-user authenticated accounts | ☐ ✔ ☐ ✘ |
| PDR-036 | Causal language only for arithmetic decomposition | ☐ ✔ ☐ ✘ |

**Blast radius if overturned:**

| Overturned | Invalidates |
|---|---|
| PDR-038 or PDR-039 | 05_Database_Design (habit schema), 06_API_Design, 08_UI_UX |
| PDR-040 | 03_SRS, 05_Database_Design, 07_AI_Architecture, ADR-007 — **structural, not cosmetic** |
| PDR-037 | 06_API_Design (Q&A endpoints), 07_AI_Architecture, 08_UI_UX, ADR-010 |
| PDR-043 | 03_SRS, 07_AI_Architecture, ADR-007 |
| PDR-046 | 02_PRD scope section only |
| Others | Localized; single-document edits |

---

## J. Remaining blockers before the PRD can be written — ✅ CLEARED

> **Historical.** Assessed at v0.2; all items closed by §B.7. Retained per §G.

### J.1 Must be ruled on — the PRD cannot be written without these

| ID | Decision needed | Consequence of guessing |
|---|---|---|
| **C-07** ⭐ | Is a conversational Q&A surface in V1? Readings (a) / (b) / (c). | Determines whether V1 has a chat feature at all. Wrong guess either omits a major surface or adds one you did not intend. |
| **D-26** ⭐ | Does an unlogged day mean *habit did not occur* or *not recorded*? | Highest-risk statistical decision in the product. A wrong ruling manufactures false correlations that no downstream care can repair. |
| **D-24** ⭐ | Habit taxonomy — fixed set, user-defined, or both? | Sets the schema, the logging UI, and the size of the hypothesis space. |
| **D-25** ⭐ | Logging granularity, value type, and retroactive backfill. | Determines how quickly the PDR-030 sufficiency gate is cleared — insights in week 2 vs. month 3. |
| **D-08** | Life event data model shape. | First-class entity per PDR-016 with no defined fields. Decide alongside D-24/D-25. |
| **D-07** | Explicit V1 non-goals list. | Without it, every downstream document re-litigates budgets, goals, net worth, mobile, and peer comparison. |

### J.2 Strongly recommended before the PRD

| ID | Decision needed | Why now |
|---|---|---|
| **D-05** | Insight feedback capture (true / false / useful). | The only instrument that measures whether PDR-015 is being delivered. Retrofitting it later means shipping V1 blind. |
| **D-06** | Success metrics for the intelligence layer. | Without these, V1 quality is unfalsifiable — a stated goal of PDR-002. |
| **D-27** | Logging drop-off behavior. | PDR-029 makes core value dependent on sustained effort; partial logging will be the common case, not the edge case. |
| **C-02 – C-05** | The four outstanding derived clarifications. | C-05 (multi-tenancy) in particular shapes the PRD's account and privacy sections. |

### J.3 Can be deferred past the PRD

`D-02` (thresholds + multiplicity), `D-09` (ranking), all of `D-BLOCK-ARCH`, and all of `D-BLOCK-AI` — these belong to the SRS, Architecture, and AI Design documents respectively.

**One caveat:** `D-02(d)` — multiplicity correction — should be *acknowledged* in the PRD as a stated quality requirement even though its numeric form belongs downstream, because it is a distinct risk from the sufficiency gate PDR-030 already approves, and it is the kind of gap that silently disappears if nobody writes it down.

---

*This document contains no product assumptions beyond those explicitly approved (Section B) or explicitly flagged as unconfirmed (Sections C, D and J).*
