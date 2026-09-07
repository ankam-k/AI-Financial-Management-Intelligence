# Product Vision — Version 1

| Field | Value |
|---|---|
| **Document Name** | 01_Product_Vision.md |
| **Product** | AI Financial Intelligence Platform |
| **Version** | 1.0 |
| **Status** | 🟢 **Approved** — rewritten against frozen PDR v1.0 |
| **Owner** | Product |
| **Dependencies** | `docs/00_Product_Decisions_Record.md` v1.0 (Frozen) |
| **Traceability** | Every section cites PDR decision IDs. See §9. |
| **Blocks** | 02_PRD |
| **Lifecycle stage** | Draft → Review → **Approved** → Frozen → Superseded |
| **Last Updated** | 2026-07-27 |

> **Rewrite note.** This document replaces v0.1, which pre-dated the PDR and contained unapproved proposals presented as decisions. All content below traces to an approved or provisional PDR decision. Nothing is asserted without a citation.

---

## Purpose

To articulate what this product is, who it serves, why it should exist, and what it refuses to become — providing the narrative context that requirements documents deliberately omit.

## Scope

**In scope:** problem statement, target user, product thesis, differentiation, the explainability commitment, and V1 boundaries.

**Out of scope:** requirements (→ `02_PRD.md`), specifications (→ `03_SRS.md`), and all design (→ `04` onward).

## Assumptions

**None.** Every statement traces to a PDR decision. Where a decision is provisional (🟠 PDR-032 … PDR-047), the citation says so.

## References

- `docs/00_Product_Decisions_Record.md` v1.0 — governing authority
- `CLAUDE.md` — standing project constraints

## Related Documents

`docs/INDEX.md` · `docs/02_PRD.md`

---

## 1. The problem

A young salaried professional in India generates more data about their own financial life than any generation before them. Every UPI payment, card transaction, and auto-debit is recorded and retrievable **(PDR-022)**. They also carry more financial anxiety than that abundance of data should permit.

The gap is not a data gap. It is an **explanation gap**.

Existing tools report **what** happened:

> "You spent ₹18,400 on Food & Dining last month."

The user roughly knew that. What no tool tells them is **what that spending was connected to**:

> "Your food spending was ₹6,200 higher in weeks when you logged no exercise. This pattern held across 9 of the last 12 weeks."

The first sentence is accounting. The second is intelligence — and it is the first one that could change behavior, because it is the first that tells the user something they could not have told themselves.

**The user we are describing (PDR-006):** 22–35, salaried, regular monthly income, one or two bank accounts, a credit card. They struggle to understand where their money goes, how daily habits affect spending, and how to improve savings — without manually analysing financial data.

Their sentence is: *"I earn decently. I have no idea why I have no money."*

## 2. Why this is unsolved

Three stacked difficulties, and most products stop after the first.

**Ingestion is filthy.** Indian bank CSV exports follow no standard. Column names, date formats, debit/credit conventions and merchant strings vary by bank and change without notice. UPI narration is semi-structured text, not data. Reaching a clean, deduplicated, correctly-signed ledger **(PDR-011)** is the majority of the engineering work and none of the demo.

**Categorization is a trust surface, not a feature.** One visibly wrong category teaches the user the whole system is guessing.

**Explanation requires evidence, and evidence requires restraint.** Any system that can produce sentences about your life can produce confident, fluent, wrong sentences about your life. In finance, a fluent wrong sentence is worse than silence — which is why silence is a designed product state here **(PDR-030)**, not a failure mode.

## 3. Product thesis

> **The platform explains why your spending changed by connecting financial transactions with personal habits and life events, then provides evidence-based recommendations to improve future financial decisions. (PDR-015)**

The primary value is **explainable behavioral financial intelligence**. This is not an expense tracker **(PDR-008)** and not a forecasting tool **(PDR-015)**.

Three commitments follow.

**We connect money to life, not just to categories.** Spending changes because something in the life changed. The intelligence layer combines transaction analysis, habit tracking, user-defined life events, statistical correlation, rule-based behavioral analysis, and explainable AI **(PDR-016)**.

**The unit of value is an Insight, not a number.** An insight is a claim about the user attached to the evidence supporting it. Every recommendation carries evidence, reasoning, supporting data, and confidence where applicable **(PDR-018, PDR-032)**.

**Every claim is verifiable by the user.** The AI never invents conclusions; every insight traces back to supporting transactions, habits, or events stored in the system **(PDR-017)**. Explainable here means *auditable by a non-technical person in seconds* — not model interpretability.

## 4. What makes this defensible

**The analysis engine is the source of truth (PDR-031).** The LLM reasons over the engine's structured outputs to explain findings and answer questions. It never originates numbers or behavioral conclusions. Most AI-first products invert this and inherit non-determinism as a permanent defect. In a financial product, a claim that changes between sessions without the data changing is a caught guess, and trust does not recover.

**We refuse to over-claim.** Behavioral insights require sufficient history, and until it exists the product says so plainly **(PDR-030)**. Five gates — history length, group size, logging coverage, effect size, and multiplicity correction — stand between a computed pattern and a shown insight **(PDR-043 🟠)**. Most patterns will not survive them. That is the point.

**We speak correlationally (PDR-028).** Insights say *associated with*, *correlated with*, *observed during*, *tended to occur alongside*. Causal phrasing is permitted only where the claim is provable by arithmetic alone **(PDR-036 🟠)**. A product that says "because" without earning it is guessing in a confident voice.

## 5. What the user does

1. **Uploads** a bank-exported CSV statement **(PDR-009, PDR-010)**, or explores bundled synthetic data without uploading anything personal **(PDR-012)**.
2. **Sees** their transactions parsed, normalized and categorized into a clean ledger **(PDR-011)**.
3. **Logs** a short daily check-in across six habits **(PDR-038 🟠, PDR-039 🟠)**, and occasionally annotates a life event — travel, illness, a job change **(PDR-042 🟠)**.
4. **Receives** up to five ranked behavioral insights per period **(PDR-047 🟠)**, each with visible evidence, or an honest statement that more data is needed **(PDR-030)**.
5. **Verifies** any insight by drilling into the transactions behind it **(PDR-017)**, and **asks** bounded single-turn questions answered from the engine's outputs **(PDR-037 🟠)**.
6. **Tells us** whether each insight was useful, or not true **(PDR-044 🟠)**.

## 6. The honest tension

**The product requires sustained user effort to deliver its core value.** Habits are captured by manual daily logging **(PDR-029)** — no derivation from transaction data in V1. Insights need ≥60% check-in coverage **(PDR-040 🟠)** and ≥8 weeks of history **(PDR-043 🟠)**.

We state this plainly rather than hiding it, because it is the central product risk and it shapes everything: onboarding must set the expectation, the daily check-in must be one interaction and not six **(PDR-039 🟠)**, and drop-off must pause insights honestly rather than degrade them silently **(PDR-041 🟠)**.

Deterministic transaction analysis remains fully available regardless of logging **(PDR-041 🟠)**, so the product is never useless — but its distinctive value is earned, not free.

## 7. Boundaries

**We describe the user's own behavior. We never direct their capital.**

| Permitted **(PDR-027)** | Prohibited **(PDR-027)** |
|---|---|
| Behavioral budgeting recommendations from the user's own spending and habits | Anything involving stocks, mutual funds, ETFs, insurance, loans, tax planning, or investment products |

The application is an educational financial intelligence and budgeting tool **(PDR-023)**. India and INR only **(PDR-021)**. No live banking integrations **(PDR-014)**.

Also excluded: budgets and spending limits, goal tracking, net worth, native mobile, peer comparison, payments, multi-turn conversation **(PDR-046 🟠)**.

**Privacy is a product commitment, not a policy page.** Data is private to the user **(PDR-024)** — never used for training, never aggregated across users, never shared **(PDR-034 🟠)**. Deletion is real and cascading **(PDR-033 🟠)**.

## 8. How we will know it worked

North Star: **Insight Trust Rate ≥ 70%** — the share of surfaced insights users mark useful or true. Hard counter-bound: **False Insight Rate < 5%** **(PDR-045 🟠)**.

Trust Rate is chosen because engagement metrics *reward* confident nonsense — a wrong but provocative insight gets clicks — while Trust Rate punishes it.

**Failure modes, named in advance:**
- Insights are believed but say nothing new → the behavioral thesis is wrong.
- Insights are interesting but disbelieved → the PDR-043 gates are too loose.
- Insights are trustworthy but too rare → manual logging (PDR-029) cannot sustain the engine.
- Users never reach an insight because ingestion breaks → most likely failure; §2's first problem was underestimated.

## 9. Traceability

| Section | Authorizing PDR IDs |
|---|---|
| 1. The problem | PDR-006, PDR-022 |
| 2. Why unsolved | PDR-011, PDR-030 |
| 3. Product thesis | PDR-008, PDR-015, PDR-016, PDR-017, PDR-018, PDR-032🟠 |
| 4. Defensibility | PDR-028, PDR-030, PDR-031, PDR-036🟠, PDR-043🟠 |
| 5. User journey | PDR-009…012, PDR-017, PDR-030, PDR-037🟠, PDR-038🟠, PDR-039🟠, PDR-042🟠, PDR-044🟠, PDR-047🟠 |
| 6. Honest tension | PDR-029, PDR-039🟠, PDR-040🟠, PDR-041🟠, PDR-043🟠 |
| 7. Boundaries | PDR-014, PDR-021, PDR-023, PDR-024, PDR-027, PDR-033🟠, PDR-034🟠, PDR-046🟠 |
| 8. Success | PDR-045🟠 |

🟠 = provisional, pending ratification (PDR §K).

## 10. Vision in one paragraph

For young salaried professionals in India who earn well and cannot explain where their money goes, this is a financial intelligence platform that connects spending to habits and life events and explains the connection in plain language, backed by evidence the user can verify in a tap. Unlike expense trackers that report totals, we state relationships — and we state them only when the data supports them, in correlational language, with the confidence visible. We are not the app that tells you what to do with your money. We are the first thing that tells you something true about yourself you did not already know.
