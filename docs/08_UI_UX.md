# UI / UX Design

| Field | Value |
|---|---|
| **Document Name** | 08_UI_UX.md |
| **Product** | AI Financial Intelligence Platform |
| **Version** | 1.0 |
| **Status** | 🟢 **Approved** |
| **Owner** | Product / Design |
| **Dependencies** | `02_PRD.md` v1.0 · `06_API_Design.md` v1.0 · ADR-012 |
| **Traceability** | Every screen cites its PRD requirement. See §9. |
| **Blocks** | Implementation |
| **Lifecycle stage** | Draft → Review → **Approved** → Frozen → Superseded |
| **Last Updated** | 2026-07-27 |

---

## Purpose

To define the interface: screens, flows, states, and the interaction principles that make the product's explainability promise real rather than claimed.

## Scope

**In scope:** information architecture, screen inventory, key flows, empty/error/loading states, copy principles, accessibility.

**Out of scope:** visual design system, component library selection, pixel specification.

## Assumptions

**None.** Every screen traces to a PRD requirement.

## References

`02_PRD.md` · `06_API_Design.md` · ADR-012 (React/TS/Vite)

## Related Documents

`docs/INDEX.md` · `06_API_Design.md`

---

## 1. Design principles

| # | Principle | Source |
|---|---|---|
| 1 | **Evidence is always one tap away.** Every claim expands to the records behind it. | PDR-017, FR-5.1 |
| 2 | **Honest emptiness.** "Not enough data yet" is a designed screen, not a blank state. | PDR-030, FR-4.5 |
| 3 | **Never shame.** Insights describe; they never judge. The user is an adult being informed. | PDR-023 |
| 4 | **Effort is earned.** Daily logging is one interaction, and the payoff is visible. | PDR-039🟠 |
| 5 | **Confidence is visible where it exists, absent where it doesn't.** | PDR-032🟠 |
| 6 | **Correlational language everywhere**, including static copy — not just model output. | PDR-028 |

## 2. Information architecture

```
├── Landing (unauthenticated)
│   └── Explore demo data ──────────────► Dashboard (demo mode)
├── Auth · Register / Login
└── App
    ├── Dashboard        insights + today's check-in prompt
    ├── Transactions     ledger, filters, category correction
    ├── Check-in         daily habit log + calendar
    ├── Life Events      list + add
    ├── Ask              single-turn Q&A
    └── Account          data inventory · sources · consents · export · delete
```

Six destinations. The persona (PDR-006) abandoned a previous app for demanding effort; navigation depth is itself a form of effort.

## 3. Onboarding

```
Landing ─► "Explore with sample data"  ─► Dashboard (demo)  ─► Register
        └► "Upload my statement"       ─► Register ─► Consent ─► Upload
```

**Demo-first is deliberate (PDR-012, FR-1.10).** The persona will not upload financial data to an unproven product, and evaluators will not create an account. Demo data is explorable within seconds, no account, and is labelled as demo everywhere it appears (FR-1.11).

**Consent (FR-6.6)** is captured explicitly for data upload and AI processing at registration — two checkboxes with plain-language explanations, neither pre-ticked.

**Expectation-setting is a first-class onboarding job.** Because insights require ~8 weeks of history and 60% check-in coverage (PDR-043🟠), onboarding must say so up front. A user who expects insights on day one and gets a sufficiency notice feels the product is broken; a user who was told what to expect feels it is honest.

## 4. Upload flow

```
Select file ─► Detecting format ─┬─ Recognized ────────► Preview ─► Import
                                 └─ Unrecognized ──► Map columns ─► Preview ─► Import
```

**Never silently guess a mapping (ADR-004).** An unrecognized format shows detected columns and asks the user to confirm.

**Result screen shows all four numbers (FR-1.9, SRS-3.6):**

```
  ✅ Imported             298
  ⏭  Already present       14      ← shown, never hidden
  ⚠️  Could not read         0
  ────────────────────────────
     Rows in file         312
```

Duplicates are surfaced, not suppressed — silence is what NFR-8 forbids. Rejections list row number, column, and reason. A failed import states plainly that nothing was changed (FR-1.8).

## 5. Dashboard

The product's centre of gravity. Three zones:

**1. Today's check-in** — inline, one interaction, submittable without leaving the page (FR-3.4).

**2. Insights** — at most 5 cards (FR-4.10). Each card:

```
┌────────────────────────────────────────────────────────┐
│ Food & Dining                          ● Tentative     │
│                                                        │
│ Spending on Food & Dining was higher in weeks with     │
│ no exercise logged.                                    │
│                                                        │
│ With exercise    ₹4,120/week   (7 weeks)               │
│ Without exercise ₹5,870/week   (6 weeks)               │
│ Difference       ₹1,750/week   (+42%)                  │
│                                                        │
│ Confidence ████████░░ 82%                              │
│                                                        │
│ ▸ Show evidence          👍  👎  ⚠ This isn't true      │
└────────────────────────────────────────────────────────┘
```

Note: correlational phrasing (PDR-028), visible confidence (PDR-032🟠), `Tentative` vs `Established` (PDR-043🟠), evidence expansion (PDR-017), three-way feedback (PDR-044🟠).

**3. Deterministic summary** — totals, categories, recurring commitments. **Always available regardless of habit coverage (FR-4.13).**

## 6. The three critical states

### 6.1 Insufficient data (PDR-030, FR-4.5)

Not an error. Not a spinner. Not a fake chart.

```
┌────────────────────────────────────────────────────────┐
│  Not enough data yet for behavioral insights           │
│                                                        │
│  Habit check-ins    ████░░░░░░  38%    (need 60%)      │
│  History            ████████░░  9 wks  (need 8) ✓      │
│                                                        │
│  About 18 more check-in days unlocks this.             │
│                                                        │
│  Meanwhile, your spending summary is ready below.      │
└────────────────────────────────────────────────────────┘
```

States what is missing, what is required, what unlocks it — and points to what *is* available. This screen is a feature (PDR-030), and it is where the product's honesty is most visible to a new user.

### 6.2 Insights paused (FR-4.11, FR-4.12)

When coverage drops below the floor, behavioral insights **pause**. Previous insights remain visible, explicitly labelled with the window they described — never re-presented as current.

### 6.3 Evidence drill-down (FR-5.1, PDR-017)

Expanding an insight shows both compared groups, the exact transactions in each, and — crucially — **the excluded days** (SRS-6.4):

```
  Weeks WITH exercise (7)          Weeks WITHOUT (6)
  ├ Apr 07–13   ₹3,890             ├ May 05–11   ₹6,240
  └ ...          [tap a week to see its transactions]

  ⓘ 5 weeks excluded — no exercise logged those weeks.
    Excluded data is never counted as "did not exercise."
```

**That last line is deliberate and non-negotiable.** It is where PDR-040🟠's invariant becomes visible to the user — the product explains not only what it concluded but what it refused to assume.

## 7. Check-in screen

Six fields, one submit (PDR-039🟠, FR-3.4).

```
  How was 12 June?

  Sleep              [ 6.5 ] hours      [ Skip ]
  Exercise           ( ) Yes  (•) No    [ Skip ]
  Home-cooked meals  [  1  ] of 3       [ Skip ]
  Stress             1  2  3 (4) 5      [ Skip ]
  Alcohol            ( ) Yes  ( ) No    [ Skip ]  ← untouched = UNKNOWN
  Work mode          Office (Remote) Leave

                                        [ Save ]
```

> **The UI must make "No" and "Skip" visibly different (SRS-5.5(e), FR-3.9).**
>
> Selecting **No** asserts the behavior did not occur. **Skip** records nothing. These are different data and produce different analysis. A design where an untouched toggle silently reads as "No" would reintroduce at the interface layer exactly the corruption PDR-040🟠 eliminates at the schema layer.
>
> An unanswered field is never pre-selected to a value.

**Calendar** shows logged / partially logged / not logged days and running coverage against the 60% threshold — making the gate legible rather than mysterious.

**Backfill** is offered up to 30 days; beyond that it is refused with an explanation (FR-3.6).

## 8. Ask screen (PDR-037🟠)

Single-turn. No thread, no history, no follow-up affordance — the UI's shape communicates the constraint honestly rather than implying a chatbot that does not exist.

Suggested questions are shown, drawn from actual engine capabilities, so users learn the boundary by example rather than by rejection.

**Refusals are plain and non-apologetic (FR-5.8, ADR-010):**

> *"I can't help with investment decisions. I can explain your own spending patterns and habits — try asking what changed in your spending last month."*

It states the boundary and offers the nearest thing it can do. It does not moralize, and it does not attempt a hedged partial answer.

## 9. Account screen

| Section | Requirement |
|---|---|
| Data inventory — what is stored | FR-6.5 |
| Sources — per-source cascading delete | FR-6.3 |
| Consents — view and revoke | FR-6.6 |
| Export — full download | FR-6.2 |
| Delete account — irreversible | FR-6.4 |

Deletion requires typing `DELETE` plus password, and states plainly that it removes everything and cannot be undone (PDR-033🟠).

A short privacy statement appears here in plain language: data is never used for training, never compared across users, never shared (PDR-034🟠).

## 10. Copy principles

| Rule | Example |
|---|---|
| Correlational, never causal (PDR-028) | ✅ "associated with weeks when…" ❌ "because you skipped the gym" |
| Describe, never judge (PDR-023) | ✅ "₹9,000 on food delivery" ❌ "You wasted ₹9,000" |
| Second person, plain, no jargon | ✅ "How confident we are" ❌ "q-value 0.084" (available on expand) |
| Say what unlocks a state | ✅ "18 more check-in days" ❌ "Insufficient data" |
| Refusals state the boundary and offer an alternative | See §8 |

**These rules bind static copy, not only model output.** SRS-10.7's lexical test runs against UI strings too — the causal-language ban is a product property, not a prompt property.

## 11. Accessibility

WCAG 2.1 AA: keyboard-navigable throughout; visible focus; 4.5:1 contrast; form fields labelled; **confidence and status never conveyed by color alone** (percentage and text label accompany every bar and badge); screen-reader labels on evidence expansion.

Responsive from 360px — PDR-046🟠 excludes native mobile, so mobile browsers are a first-class target, not an afterthought.

## 12. Traceability

| Section | PRD | PDR |
|---|---|---|
| §3 Demo-first onboarding | FR-1.10, FR-1.11, FR-6.6 | PDR-012, PDR-024 |
| §4 Upload flow | FR-1.8, FR-1.9 | PDR-009 … 011, ADR-004 |
| §5 Insight cards | FR-4.10, FR-5.9 | PDR-028, 032🟠, 043🟠, 044🟠, 047🟠 |
| §6.1 Insufficient data | FR-4.5 | **PDR-030** |
| §6.2 Paused insights | FR-4.11, FR-4.12 | PDR-041🟠 |
| §6.3 Evidence + excluded days | FR-5.1, FR-4.8 | **PDR-017, PDR-040🟠** |
| §7 Check-in, No vs Skip | FR-3.4, FR-3.9 | **PDR-039🟠, PDR-040🟠** |
| §8 Ask, refusals | FR-5.4, FR-5.5, FR-5.8 | PDR-027, PDR-037🟠 |
| §9 Account | FR-6.2 … 6.6 | PDR-024, 033🟠, 034🟠 |
| §10 Copy | FR-5.2 | PDR-023, PDR-028 |
