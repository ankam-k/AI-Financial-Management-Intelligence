# Product Requirements Document (PRD)

| Field | Value |
|---|---|
| **Document Name** | 02_PRD.md |
| **Product** | AI Financial Intelligence Platform |
| **Version** | 1.0 |
| **Status** | 🟢 **Approved** |
| **Owner** | Product |
| **Dependencies** | `00_Product_Decisions_Record.md` v1.0 (Frozen) · `01_Product_Vision.md` v1.0 |
| **Traceability** | Every requirement cites a PDR decision ID. See §10. |
| **Blocks** | 03_SRS, 08_UI_UX |
| **Lifecycle stage** | Draft → Review → **Approved** → Frozen → Superseded |
| **Last Updated** | 2026-07-27 |

---

## Purpose

To define **what** the product must do for its user, at the level of capabilities and acceptance criteria — the bridge between the Vision's narrative and the SRS's formal specification.

## Scope

**In scope:** personas, epics, user stories, functional capability requirements, non-functional requirements, acceptance criteria, release scope, out-of-scope declarations.

**Out of scope:** implementation, schema, endpoints, algorithms, prompts, screens. Those belong to `03_SRS` and `04`–`08`.

## Assumptions

**None.** Every requirement cites a PDR decision. Requirements citing 🟠 provisional decisions are marked; if a provisional decision is overturned, §10 identifies exactly which requirements fall.

## References

`00_Product_Decisions_Record.md` v1.0 · `01_Product_Vision.md` v1.0 · `CLAUDE.md`

## Related Documents

`docs/INDEX.md` · `03_SRS.md` · `08_UI_UX.md`

---

## 1. Persona

**Arjun, 27 — the only user V1 serves (PDR-006).**

| Attribute | Value |
|---|---|
| Age | 22–35 |
| Income | Regular, monthly, single source |
| Accounts | 1–2 bank accounts, 1 credit card |
| Payment behavior | UPI-dominant; debit, credit, wallet **(PDR-022)** |
| Core frustration | Cannot explain where money goes or how habits affect spending |
| Constraint | Will not manually analyse financial data |

**Scope rule (PDR-007):** any feature that does not directly help this user is deferred to a future version. This is a rejection test applied to every requirement below.

## 2. Epics

| ID | Epic | Outcome |
|---|---|---|
| **E1** | Get data in | User's financial history exists as a clean, verified ledger |
| **E2** | Understand the ledger | Every transaction is categorized with a visible reason |
| **E3** | Capture behavior | Daily habits and life events are recorded |
| **E4** | Generate insight | Trustworthy behavioral relationships are surfaced — or honest silence |
| **E5** | Explain and verify | Every claim is auditable; bounded questions are answerable |
| **E6** | Trust and control | Account, privacy, export, deletion |

## 3. E1 — Data ingestion

### Stories

**US-1.1** As Arjun, I upload my bank's CSV export so my transactions are in the system.
**US-1.2** As a first-time visitor, I explore realistic demo data without uploading anything personal.
**US-1.3** As Arjun, I re-upload an overlapping statement without corrupting my ledger.
**US-1.4** As Arjun, when my file fails to import I am told exactly what was wrong.

### Requirements

| ID | Requirement | PDR |
|---|---|---|
| **FR-1.1** | System accepts CSV upload of bank-exported statements. | PDR-009, PDR-010 |
| **FR-1.2** | System parses, validates, normalizes and categorizes uploaded transactions into a standard internal format. | PDR-011 |
| **FR-1.3** | Excel upload is supported **only if** target-bank formats prove common. Conditional, not committed. | PDR-010 |
| **FR-1.4** | PDF statement parsing is **not** supported. | PDR-010 (§E) |
| **FR-1.5** | Ingestion sits behind an adapter/port abstraction; adding a future source must not change analysis, AI or reporting modules. | PDR-013 |
| **FR-1.6** | No live banking integration exists in V1. | PDR-014 |
| **FR-1.7** | Re-uploading overlapping data must not duplicate transactions. Ledger converges to the same state. | PDR-011, PDR-045🟠 |
| **FR-1.8** | Import is atomic: it fully succeeds or fully fails. No silent partial imports. | PDR-002, PDR-045🟠 |
| **FR-1.9** | Import failures produce a specific, actionable message identifying row and reason. | PDR-006 |
| **FR-1.10** | System ships synthetic datasets representing **different spending behaviors**, usable without an account upload. | PDR-012 |
| **FR-1.11** | Synthetic data is labelled as demo data wherever it is displayed. | PDR-012, PDR-002 |
| **FR-1.12** | Synthetic datasets serve automated testing and AI evaluation, with known planted patterns as ground truth. | PDR-012 |
| **FR-1.13** | Supported instruments: UPI, bank account, debit card, credit card, wallet. | PDR-022 |
| **FR-1.14** | Currency is INR. Amounts are stored so no rounding error is user-visible. | PDR-021, PDR-002 |

### Acceptance criteria

- ✅ A valid CSV from each supported bank imports with 100% of rows accounted for — imported or explicitly rejected with a reason.
- ✅ Uploading the same file twice produces an identical ledger and zero new transactions.
- ✅ Uploading two statements with a 10-day overlap produces exactly one copy of each overlapping transaction.
- ✅ A malformed file leaves the ledger byte-identical to its pre-upload state.
- ✅ Demo data is explorable within 10 seconds of landing, with no account required and no upload.

## 4. E2 — Transaction understanding

### Stories

**US-2.1** As Arjun, every transaction is categorized so I can see spending by area.
**US-2.2** As Arjun, I see *why* a transaction got its category.
**US-2.3** As Arjun, I correct a wrong category once and it stays corrected.

### Requirements

| ID | Requirement | PDR |
|---|---|---|
| **FR-2.1** | Every transaction is assigned a category. | PDR-011 |
| **FR-2.2** | Every categorization exposes a **visible reason** and a confidence indicator. | PDR-001, PDR-018, PDR-032🟠 |
| **FR-2.3** | Merchant names are extracted and normalized from UPI narration and bank description fields. | PDR-022 |
| **FR-2.4** | User may override any category. | PDR-006 |
| **FR-2.5** | User overrides persist and take precedence over automated categorization permanently, including on re-import. | PDR-006, PDR-011 |
| **FR-2.6** | Recurring transactions and subscriptions are detected. | PDR-016 |
| **FR-2.7** | Transactions the system cannot confidently categorize are marked Uncategorized rather than guessed. | PDR-017, PDR-030 |

### Acceptance criteria

- ✅ Every transaction has a category or the explicit Uncategorized state — never blank.
- ✅ Every category displays a reason a non-technical user can read.
- ✅ A corrected category survives re-import of the same statement.

## 5. E3 — Behavior capture

### Stories

**US-3.1** As Arjun, I log my day in one short interaction, not six.
**US-3.2** As Arjun, I backfill yesterday when I forget.
**US-3.3** As Arjun, I record that I travelled last week so it can be accounted for.

### Requirements

| ID | Requirement | PDR |
|---|---|---|
| **FR-3.1** | Habits are captured by **manual logging only**. No derivation from transaction data in V1. | PDR-029 |
| **FR-3.2** | Exactly six habits are supported: sleep duration (numeric hours), exercise (boolean), home-cooked meals (count 0–3), stress level (ordinal 1–5), alcohol (boolean), work mode (Office/Remote/Leave). | PDR-038🟠 |
| **FR-3.3** | User-defined custom habits are **not** supported in V1. | PDR-038🟠 |
| **FR-3.4** | Habit capture is **one daily check-in record per user per date**, covering all six habits in a single interaction. | PDR-039🟠 |
| **FR-3.5** | Partial check-ins are permitted; individual fields may be left blank. | PDR-039🟠 |
| **FR-3.6** | Retroactive backfill is permitted up to **30 days**; beyond that it is refused. | PDR-039🟠 |
| **FR-3.7** | Check-ins are editable. An edit invalidates insights derived from the affected window, which are recomputed. | PDR-039🟠, PDR-017 |
| **FR-3.8** | A date with **no check-in record** means UNKNOWN. It must never be interpreted as "the habit did not occur". | **PDR-040🟠** ⭐ |
| **FR-3.9** | A submitted check-in with a false/zero value is an explicit **recorded negative**, distinct from UNKNOWN. | **PDR-040🟠** ⭐ |
| **FR-3.10** | User may record life events with: type (Travel, Illness, Job change, Relocation, Festival/Celebration, Family event, Other), title, start date, optional end date, optional notes. | PDR-042🟠 |
| **FR-3.11** | Life events segment analysis windows. They are never presented as causes. | PDR-042🟠, PDR-028 |
| **FR-3.12** | Wearable and external health-platform integration is out of V1 scope. | PDR-029 |

### Acceptance criteria

- ✅ A complete daily check-in is submittable in one interaction.
- ✅ A day with no check-in is distinguishable in the data from a day where the user recorded "no exercise" — verified by a test that asserts the two are not conflated.
- ✅ Backfill beyond 30 days is refused with an explanation.
- ✅ Editing a past check-in triggers recomputation of affected insights.

## 6. E4 — Insight generation

### Stories

**US-4.1** As Arjun, I am shown a few relationships between my habits and spending that I did not know.
**US-4.2** As a new user, I am told plainly that I do not yet have enough data — not shown a fabricated insight.
**US-4.3** As Arjun, when I stop logging, the product does not pretend it still knows things.

### Requirements

| ID | Requirement | PDR |
|---|---|---|
| **FR-4.1** | Intelligence layer combines transaction analysis, habit tracking, life events, statistical correlation, rule-based behavioral analysis and explainable AI. | PDR-016 |
| **FR-4.2** | Every insight traces to supporting transactions, habits or events stored in the system. Untraceable output is a defect. | **PDR-017** ⭐ |
| **FR-4.3** | Every recommendation includes evidence, reasoning, supporting data, and confidence where applicable. | PDR-018 |
| **FR-4.4** | Confidence is **mandatory** for statistically inferred claims and **omitted** for direct arithmetic. When confidence is low, the system says so explicitly. | PDR-032🟠 |
| **FR-4.5** | Behavioral insights require sufficient history. Before it exists, the system states clearly that more data is needed. | **PDR-030** ⭐ |
| **FR-4.6** | A behavioral insight is shown only if it clears **all five** gates: ≥8 weeks history; ≥6 observations per compared group; ≥60% check-in coverage; effect ≥₹500/week **and** ≥15% relative; Benjamini–Hochberg FDR at q=0.10. | **PDR-043🟠** ⭐ |
| **FR-4.7** | UNKNOWN habit observations are **excluded** from correlation analysis — never imputed, never defaulted. | **PDR-040🟠** ⭐ |
| **FR-4.8** | Excluded-day counts are surfaced in an insight's evidence. | PDR-040🟠, PDR-017 |
| **FR-4.9** | Insights are labelled *Tentative* on first detection, promoted to *Established* only after persisting into a subsequent window. | PDR-043🟠 |
| **FR-4.10** | At most **5** insights are surfaced per analysis period, ranked by effect size × confidence × novelty. | PDR-047🟠 |
| **FR-4.11** | When check-in coverage falls below the floor, behavioral insights **pause**. They are not degraded. | PDR-041🟠 |
| **FR-4.12** | Previously generated insights remain viewable, explicitly timestamped with the window they describe. | PDR-041🟠 |
| **FR-4.13** | Deterministic transaction analysis remains fully available regardless of habit coverage. | PDR-041🟠 |
| **FR-4.14** | The analysis engine is the source of truth. The LLM must not fabricate numerical results or unsupported behavioral conclusions. | **PDR-031** ⭐ |

### Acceptance criteria

- ✅ A user with 4 weeks of data receives zero behavioral insights and a clear statement of what is needed.
- ✅ A user with 12 weeks of data and 30% check-in coverage receives zero behavioral insights and a coverage explanation.
- ✅ Against a synthetic dataset with planted patterns, the engine surfaces the planted patterns and surfaces **no** unplanted ones.
- ✅ No insight ever displays a number absent from the analysis engine's output.
- ✅ Never more than 5 insights per period.

## 7. E5 — Explanation and verification

### Stories

**US-5.1** As Arjun, I tap an insight and see the exact transactions behind it.
**US-5.2** As Arjun, I ask a question about my spending and get an answer grounded in my data.
**US-5.3** As Arjun, I tell the product when an insight is wrong.

### Requirements

| ID | Requirement | PDR |
|---|---|---|
| **FR-5.1** | Every insight offers drill-down to its supporting records. | PDR-017 |
| **FR-5.2** | Insights use correlational language: *associated with, correlated with, observed during, tended to occur alongside*. | **PDR-028** ⭐ |
| **FR-5.3** | Causal phrasing is permitted **only** where the claim is provable by summing stored rows alone (arithmetic decomposition). | PDR-036🟠 |
| **FR-5.4** | System provides **single-turn** Q&A answered only from analysis-engine structured outputs. No conversational memory in V1. | PDR-037🟠 |
| **FR-5.5** | Out-of-scope questions receive an explicit refusal, not a best-effort answer. | PDR-037🟠 |
| **FR-5.6** | The prohibited-advice boundary is enforced **at runtime** on every question. | PDR-027, PDR-037🟠 |
| **FR-5.7** | System may give behavioral budgeting recommendations from the user's own spending and habits. | PDR-027 |
| **FR-5.8** | System must **never** recommend anything involving stocks, mutual funds, ETFs, insurance, loans, tax planning, or investment products. | **PDR-027** ⭐ |
| **FR-5.9** | Every insight carries feedback controls: Useful / Not useful / This isn't true. | PDR-044🟠 |
| **FR-5.10** | "This isn't true" is recorded as a defect report and is triageable to a root cause. | PDR-044🟠 |

### Acceptance criteria

- ✅ Every insight drills to its supporting transactions in one interaction.
- ✅ No user-facing string states a correlational relationship in causal language — verified by an automated language check.
- ✅ "Should I invest in mutual funds?" is refused, in every phrasing tested.
- ✅ Feedback is recorded per insight and retrievable for analysis.

## 8. E6 — Trust and control

| ID | Requirement | PDR |
|---|---|---|
| **FR-6.1** | Multi-user application with individual authenticated accounts and strict per-user data isolation. | PDR-035🟠 |
| **FR-6.2** | User can export all their data. | PDR-024 |
| **FR-6.3** | User can delete a data source (one statement and everything derived from it). | PDR-033🟠 |
| **FR-6.4** | User can delete their account and all data, irreversibly and cascading to derived habits, signals, insights, evidence links and cached AI output. | PDR-033🟠 |
| **FR-6.5** | User is shown what data is stored about them. | PDR-024 |
| **FR-6.6** | Explicit consent is captured for data upload and for AI processing. | PDR-024 |
| **FR-6.7** | Only data required for insight generation is collected. | PDR-024 |
| **FR-6.8** | User data is never used for training, never aggregated across users, never shared with third parties. No cross-user computation exists. | PDR-034🟠 |
| **FR-6.9** | The application is positioned as an educational financial intelligence and budgeting tool. | PDR-023 |

### Acceptance criteria

- ✅ User A can never retrieve any record belonging to User B — verified by isolation tests on every data-access path.
- ✅ Account deletion leaves no user-attributable row in any table.
- ✅ No code path computes across users.

## 9. Non-functional requirements

| ID | Requirement | PDR |
|---|---|---|
| **NFR-1** | Maintainability is the deciding criterion where design options conflict. | PDR-002 |
| **NFR-2** | Clean Architecture, SOLID, full type hints, automated tests, modular services. | PDR-004 |
| **NFR-3** | Every module documented; documentation explains tradeoffs. | PDR-005 |
| **NFR-4** | Money is represented so no rounding artifact is ever user-visible. | PDR-002, PDR-021 |
| **NFR-5** | Insight generation is deterministic: identical data yields identical claims across runs. | PDR-031, PDR-017 |
| **NFR-6** | Architecture supports adding countries, currencies and banking integrations without redesigning the core analysis engine. | PDR-025 |
| **NFR-7** | Product remains usable when the language model is unavailable — insights are structured data first, prose second. | PDR-031 |
| **NFR-8** | Success measured by Insight Trust Rate ≥70%; False Insight Rate <5%; zero silent ingestion failures. | PDR-045🟠 |
| **NFR-9** | Comprehensive error handling and structured logging throughout. | PDR-002, PDR-004 |

## 10. Traceability and blast radius

| Epic | Authorizing PDR IDs |
|---|---|
| E1 Ingestion | PDR-009, 010, 011, 012, 013, 014, 021, 022 |
| E2 Understanding | PDR-001, 011, 016, 018, 022, 030, 032🟠 |
| E3 Behavior capture | PDR-029, 038🟠, 039🟠, 040🟠, 042🟠 |
| E4 Insight | PDR-016, 017, 018, 030, 031, 032🟠, 040🟠, 041🟠, 043🟠, 047🟠 |
| E5 Explanation | PDR-017, 027, 028, 036🟠, 037🟠, 044🟠 |
| E6 Trust | PDR-023, 024, 033🟠, 034🟠, 035🟠 |
| NFRs | PDR-002, 004, 005, 021, 025, 031, 045🟠 |

**If a provisional decision is overturned, these requirements fall:**

| Overturned | Requirements invalidated |
|---|---|
| PDR-038🟠 / PDR-039🟠 | FR-3.2 … FR-3.7 |
| **PDR-040🟠** | FR-3.8, FR-3.9, FR-4.7, FR-4.8 — **structural** |
| PDR-043🟠 | FR-4.6, FR-4.9 |
| PDR-037🟠 | FR-5.4, FR-5.5, FR-5.6 |
| PDR-046🟠 | §11 exclusions only |
| PDR-047🟠 | FR-4.10 |

## 11. Out of scope for V1

| Excluded | Authority |
|---|---|
| Live banking integrations (Account Aggregator, Plaid, bank APIs) | PDR-014 |
| Investment, tax, insurance, loan advice; any regulated recommendation | PDR-023, PDR-027 |
| PDF statement parsing | PDR-010 |
| Markets outside India; currencies other than INR | PDR-021 |
| Automatic habit derivation from transactions | PDR-029 |
| Wearable / health-platform integration | PDR-029 |
| User-defined custom habits | PDR-038🟠 |
| Budgets, envelopes, spending limits | PDR-046🟠 |
| Financial goal setting and tracking | PDR-046🟠 |
| Net worth / asset tracking | PDR-046🟠 |
| Native mobile applications | PDR-046🟠 |
| Peer comparison / benchmarking | PDR-046🟠, PDR-034🟠 |
| Bill payment / money movement | PDR-046🟠 |
| Multi-turn conversational assistant | PDR-037🟠, PDR-046🟠 |
