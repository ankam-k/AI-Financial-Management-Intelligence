# Documentation Index

| Field | Value |
|---|---|
| **Document Name** | INDEX.md |
| **Product** | AI Financial Intelligence Platform |
| **Version** | 2.8 |
| **Status** | 🟢 Living document — updated on every documentation change |
| **Owner** | Engineering |
| **Dependencies** | None (register only; carries no product authority) |
| **Traceability** | N/A — this document records status, never decisions |
| **Blocks** | Nothing |
| **Last Updated** | 2026-07-28 |

---

## Purpose

The single authoritative register of every project document: status, version, dependencies, what it blocks, and when it last changed. Read this first to learn what exists, what is trustworthy, and what is next.

## Scope

**In scope:** document status, dependency mapping, lifecycle state, phase mapping, structural deviations, outstanding actions.

**Out of scope:** product decisions (→ `00_Product_Decisions_Record.md`) and any content belonging to the documents listed here.

## Assumptions

None. Every row reflects verified filesystem state as of Last Updated.

## References

`CLAUDE.md` · `docs/00_Product_Decisions_Record.md`

## Related Documents

All documents in §3.

---

## 1. ⚠️ Outstanding action

> **16 provisional decisions await ratification.** `PDR-032` … `PDR-047` were made under delegated authority ("continue for everything", 2026-07-27), not by the product owner. Six sprints have since been built on them.
>
> **→ Decision pack ready: [`14_Ratification_Briefing.md`](14_Ratification_Briefing.md).** It restates §K's blast radius in terms of the code and tests that now exist, and carries a ruling table. Thirteen are recommended for straight confirmation.
>
> **Three need a ruling rather than a tick.** ⚠️ **PDR-046** declares budgets a V1 non-goal, but budget reporting was built in Sprint 2 on an explicit brief — the frozen text and the shipped product disagree. **PDR-036** was implemented more strictly than written. **PDR-047**'s novelty term is unimplemented and depends on insight persistence.
>
> The four highest-impact: **PDR-040** (missing-data semantics), **PDR-038** (fixed habit set), **PDR-037** (bounded Q&A), **PDR-043** (statistical gates).

## 2. Document lifecycle

```
Draft  →  Review  →  Approved  →  Frozen  →  Superseded
```

| Stage | Symbol | May downstream documents rely on it? |
|---|---|---|
| Draft | 🔴 | **No.** Not authoritative. |
| Review | 🟡 | **No.** Under active challenge. |
| Approved | 🟢 | **Yes.** |
| Frozen | 🔵 | **Yes.** Changes require a numbered amendment. |
| Superseded | ⚫ | **No.** History only. |

## 3. Document register

| # | Document | Status | Ver. | Depends on | Blocks | Updated |
|---|---|---|---|---|---|---|
| — | `INDEX.md` | 🟢 Living | 2.8 | — | — | 2026-07-28 |
| 00 | `00_Product_Decisions_Record.md` | 🔵 **Frozen** ⚠️ | 1.0 | `CLAUDE.md` | **Everything** | 2026-07-27 |
| 01 | `01_Product_Vision.md` | 🟢 Approved | 1.0 | 00 | 02 | 2026-07-27 |
| 02 | `02_PRD.md` | 🟢 Approved | 1.0 | 00, 01 | 03, 08 | 2026-07-27 |
| 03 | `03_SRS.md` | 🟢 Approved | 1.0 | 00, 02 | 04, 09 | 2026-07-27 |
| 04 | `04_System_Architecture.md` | 🟢 Approved | 1.0 | 00, 03 | 05, 06, 07, 10, 11 | 2026-07-27 |
| 05 | `05_Database_Design.md` | 🟢 Approved | 1.0 | 03, 04 | Implementation | 2026-07-27 |
| 06 | `06_API_Design.md` | 🟢 Approved | 1.0 | 03, 04, 05 | Implementation, 08 | 2026-07-27 |
| 07 | `07_AI_Architecture.md` | 🟢 Approved | 1.0 | 03, 04 | Implementation | 2026-07-27 |
| 08 | `08_UI_UX.md` | 🟢 Approved | 1.0 | 02, 06 | Implementation | 2026-07-27 |
| 09 | `09_Testing_Strategy.md` | 🟢 Approved | 1.0 | 03, 04, 07 | Impl. sign-off | 2026-07-27 |
| 10 | `10_Deployment.md` | 🟢 Approved | 1.0 | 04 | — | 2026-07-27 |
| 11 | `11_Architecture_Decision_Records/` | 🟢 19 ADRs | 1.6 | 04 | — | 2026-07-28 |
| 12 | `12_Future_Roadmap.md` | 🟢 Approved | 1.0 | 00 | — | 2026-07-27 |
| 13 | `13_Demo_And_Release.md` | 🟢 Approved | 1.0 | 07, ADR-013, ADR-019 | — | 2026-07-28 |
| 14 | `14_Ratification_Briefing.md` | 🟡 **Review** ⚠️ | 1.0 | 00 §K | **Closing V1** | 2026-07-28 |

**Register health:** 1 living · 1 frozen · 12 approved · 1 in review · 19 ADRs · **0 not started** · 0 draft.

⚠️ on PDR = frozen but contains provisional decisions (§1).

## 4. Architecture Decision Records

| ADR | Title | Status | Closes |
|---|---|---|---|
| 001 | Clean Architecture with ports and adapters | Accepted | — |
| 002 | PostgreSQL 16 + SQLAlchemy 2.0 async + Alembic | Accepted | D-10 |
| 003 | Money as integer paise; injected clock; IST | Accepted | D-11, D-15 |
| 004 | Per-bank adapters + generic fallback | Accepted | D-12 |
| 005 | Layered categorization with confidence floor | Accepted | D-13, D-22 |
| 006 | Deterministic content-hash deduplication | Accepted | D-14 |
| 007 | **Non-parametric tests, BH-FDR, complete-case** ⭐ | Accepted | D-29 |
| 008 | Qwen2.5-7B-Instruct via local Ollama | Accepted | D-19 |
| 009 | Provenance + lexical validation, template fallback | Accepted | D-20, D-21 |
| 010 | Independent prohibited-topic guard | Accepted | D-28 |
| 011 | JWT + Argon2id + constructor-scoped repositories | Accepted | D-16 |
| 012 | React + TypeScript + Vite | Accepted | D-17 |
| 013 | Docker Compose, single-host V1 | Accepted | D-18 |
| 014 | **V1 MVP simplifications** — SQLite, sync ORM, no auth, no repository ports ⚠️ | Accepted | — |
| 015 | Analysis engine V1 — Insight contract, stdlib statistics, no persistence | Accepted | — |
| 016 | Narration V1 — five sections, code-rendered confidence, template-first ⚠️ | Accepted | — |
| 017 | Dashboard V1 — hand-rolled SVG charts, dev proxy, validated palette | Accepted | — |
| 018 | Chat V1 — guard-first, deterministic routing, no conversation state | Accepted | — |
| 019 | Demo V1 — planted patterns below the API, validated by the real engine ⭐ | Accepted | **OEQ-004** |

⚠️ ADR-016 **supersedes ADR-009 §4.4's output shape**; the rest of ADR-009 is implemented as written.

⚠️ ADR-014 **amends 001, 002 and 011 for V1 only**, and lists what it refuses to simplify. Read it before treating those three as descriptions of the running code.

## 5. Phase → artifact mapping

| Phase | Name | Artifact | State |
|---|---|---|---|
| 0 | Product Discovery | `00_Product_Decisions_Record.md` | ✅ Frozen v1.0 |
| 1 | Product Vision | `01_Product_Vision.md` | ✅ Approved |
| 2 | Product Requirements | `02_PRD.md` | ✅ Approved |
| 3 | Software Requirements Spec | `03_SRS.md` | ✅ Approved |
| 4 | System Architecture | `04_System_Architecture.md` + 13 ADRs | ✅ Approved |
| 5 | Database Design | `05_Database_Design.md` | ✅ Approved |
| 6 | API Design | `06_API_Design.md` | ✅ Approved |
| 7 | AI Architecture | `07_AI_Architecture.md` | ✅ Approved |
| 8 | UI / UX | `08_UI_UX.md` | ✅ Approved |
| 9 | Development Planning | ⚠️ No artifact defined — see §7 D-3 | Unresolved |
| 10 | Implementation | `backend/`, `frontend/` | 🟢 **V1 complete (Sprints 1–6)** — CRUD, the Behavior Analysis Engine, the AI Insight Generator, the React dashboard, the bounded Q&A assistant, and the deterministic demo dataset |
| 11 | Testing | `09_Testing_Strategy.md` + `tests/` | 🟢 746 backend + 109 frontend tests, including schema-invariant, gate, hallucination, guard and demo-validation tests |
| 12 | Deployment | `10_Deployment.md` + `docker/` | 🟢 Compose stack built — api + web (nginx) + optional ollama |

## 6. Repository structure — verified 2026-07-28

```
AI-Financial-Intelligence/
├── .gitattributes                        ✅ line-ending + diff policy
├── .gitignore                            ✅
├── docs/
│   ├── INDEX.md                          ✅
│   ├── 00_Product_Decisions_Record.md    ✅ Frozen v1.0
│   ├── 01_Product_Vision.md              ✅
│   ├── 02_PRD.md                         ✅
│   ├── 03_SRS.md                         ✅
│   ├── 04_System_Architecture.md         ✅
│   ├── 05_Database_Design.md             ✅
│   ├── 06_API_Design.md                  ✅
│   ├── 07_AI_Architecture.md             ✅
│   ├── 08_UI_UX.md                       ✅
│   ├── 09_Testing_Strategy.md            ✅
│   ├── 10_Deployment.md                  ✅
│   ├── 11_Architecture_Decision_Records/ ✅ README + 19 ADRs
│   └── 12_Future_Roadmap.md              ✅
├── backend/                              🟡 Sprints 1–3
│   ├── README.md                         ✅ how to run, endpoints, conventions
│   ├── requirements.txt / -dev.txt       ✅ unchanged since Sprint 1
│   └── app/
│       ├── main.py                       ✅ app, routers, create_all
│       ├── core/                         ✅ config · database · clock
│       ├── domain/                       ✅ enums · money · errors
│       ├── analysis/                     ✅ ⭐ the engine — no I/O, no framework
│       ├── narration/                    ✅ ⭐ explanations — no I/O, no adapter
│       ├── chat/                         ✅ ⭐ bounded Q&A — guard runs first
│       ├── demo/                         ✅ ⭐ deterministic dataset + CLI
│       ├── llm/                          ✅ model adapters (the only network I/O)
│       ├── models/                       ✅ user · expense · check_in · life_event
│       ├── schemas/                      ✅ Pydantic contracts
│       ├── services/                     ✅ business rules + analysis loader
│       └── api/                          ✅ deps · errors · routes/
├── tests/                                🟡 546 tests, all passing
│   ├── conftest.py                       ✅ in-memory DB + frozen clock
│   ├── test_invariants.py                ✅ ⭐ schema correctness properties
│   ├── test_insights_api.py              ✅ engine wiring, end to end
│   ├── analysis/                         ✅ 223 unit tests, no database
│   ├── narration/                        ✅ 159 unit tests, no model needed
│   ├── chat/                             ✅ guard · intents · context · pipeline
│   ├── demo/                             ✅ ⭐ planted patterns + negative controls
├── docs/screenshots/                     ✅ generated by headless Chrome
│   └── test_{profile,expenses,check_ins,life_events}.py  ✅
├── frontend/                             🟡 Sprint 4 — React + TypeScript + Vite
│   ├── README.md                         ✅ how to run, what the layer may not do
│   └── src/                              ✅ api · hooks · lib · components/charts · pages
├── datasets/.gitkeep                     ⬜ empty — the dataset is generator output, not a fixture (ADR-019)
├── docker/                               ✅ Dockerfiles · compose · nginx
├── pyproject.toml                        ✅ pytest configuration only
├── README.md                             ✅
└── CLAUDE.md                             ✅
```

`.gitkeep` placeholders remain in the three directories that are still empty. Git does not track empty directories, and without them those mandated directories would be absent from a fresh clone — making the structure above documentation of something the repository does not contain. `backend/` and `tests/` no longer need one.

Two directories present on disk are **deliberately excluded** from the repository — `scripts/` and `.github/` carry no `.gitkeep` pending the D-1 and D-2 rulings in §7.

## 7. Structural deviations — still requiring rulings

| # | Deviation | Recommended action |
|---|---|---|
| **D-1** | `scripts/` exists (empty), not in the fixed structure | Ruling needed: keep or remove |
| **D-2** | `.github/` exists (empty), not in the fixed structure | Recommend keep — CI needed by Phase 12 |
| **D-3** | **Phase 9 (Development Planning) has no artifact.** `09_Testing_Strategy.md` maps to Phase 11, `10_Deployment.md` to Phase 12 | Ruling needed: (a) add `09_Development_Plan.md` and renumber, (b) fold into `12_Future_Roadmap.md`, (c) track here only |
| **V-1** | **Duplicate ADR register.** `docs/11_Architecture_Decision_Records/README.md` §Register and §4 of this document list the same 13 ADRs independently. They have already drifted in three rows (ADR-004, ADR-008, ADR-011 titles), and neither is a superset — this document carries a `Closes` column, the other a `Serves` column. A second `README.md` also duplicates a filename the fixed structure declares once, at root. | Ruling needed. Recommend **merge `Serves` into §4 and delete the ADR README**, leaving one register. |
| **V-2** | **ADR filenames use a convention no other document follows.** Every mandated document is `NN_Title_Case_Underscores.md`; the 13 ADRs are `ADR-NNN-kebab-case.md`. Two schemes coexist, and the second was introduced without being recorded as a decision. | Ruling needed. Recommend **keep the kebab-case names and record the exception here**: `ADR-NNN-kebab` is the standard ADR convention, ADR numbers must stay immutable once cited, and renaming would touch ~40 inbound links for no functional gain. |
| **D-5** | **The 13 ADRs do not carry the mandated document header block** (Document Name / Version / Owner / Dependencies / Traceability / Last Updated) or the Purpose / Scope / Assumptions / References / Related Documents sections. They instead follow the ADR format the project brief mandates specifically for them (Decision · Context · Alternatives · Tradeoffs · Final Choice · Consequences), plus Status / Date / Serves. The collection's `README.md` carries the full mandated header on behalf of the set. | Ruling needed. Recommend **keep as-is**: applying a 7-row header and five prose sections to each 3 KB ADR would roughly double their length in boilerplate and works against the ADR convention. If full compliance is preferred, all 13 need a header block added. |

## 8. Open Engineering Questions

Engineering decisions consciously deferred. Unlike PDR open decisions, these do not block product scope — they block implementation detail. Each must be closed by an ADR before the code it governs is written.

Distinct from §7: those are deviations from the mandated structure. These are decisions the project has chosen not to make yet.

| # | Question | Blocks | Raised | Status |
|---|---|---|---|---|
| **OEQ-001** | Cryptographic test material strategy | Phase 10 auth implementation; `09_Testing_Strategy.md` fixtures | 2026-07-27 | 🔶 Open |
| **OEQ-002** | Alembic migration baseline | Any data that cannot be regenerated | 2026-07-28 | 🔶 Open |
| **OEQ-003** | Future-dated expense policy | Nothing yet; will affect analysis windows | 2026-07-28 | 🔶 Open |
| **OEQ-004** | ~~Backfill window vs. gate G1/G3~~ | ~~Demoing behavioural insights~~ | 2026-07-28 | ✅ **Closed** — ADR-019 |

### OEQ-001 — Cryptographic test material strategy

**Question.** How does the test suite obtain the cryptographic material it needs, and is any of it committed?

**Why deferred.** ADR-011 selects JWT bearer tokens with Argon2id password hashing but does not fix the token signing algorithm. HS256 needs only a shared secret, which any test can synthesise. RS256/EdDSA needs a keypair, which must either be committed as a fixture or generated at test setup. The answer is downstream of an authentication detail that is not yet final, so choosing now would be guessing.

**Interim constraint (in force).** `.gitignore` ignores `*.pem` and `*.key` absolutely, with no test-fixture exemption. No cryptographic material is committable today. This is the safe default: a broad re-include under a secrets pattern is the most common path by which real key material reaches a repository, and `tests/fixtures/` is exactly where a developer drops a working key "just to reproduce the bug."

**To close, an ADR must state:** the signing algorithm; whether test keys are generated at runtime (recommended — committed test keys drift, expire, and get copy-pasted into staging) or committed as fixtures; and if the latter, the narrow negation permitted in `.gitignore`.

**Related.** ADR-011 · `09_Testing_Strategy.md` · `.gitignore` §Secrets

### OEQ-002 — Alembic migration baseline

**Question.** When does the schema stop being recreated by `create_all` and start being migrated?

**Why deferred.** ADR-014 accepts `create_all` for V1 because the schema changes with every sprint and a migration history written against a moving schema is churn that gets squashed anyway. That reasoning expires the moment the database holds something a developer would be upset to lose.

**Interim constraint (in force).** The local SQLite file is disposable. Any schema change is applied by deleting `financial_intelligence.db` and restarting. Nothing in the repository depends on its contents.

**To close, an ADR must state:** the sprint at which the baseline migration is generated, and whether SQLite or PostgreSQL is the target at that point — generating a baseline against SQLite and then switching engines means writing it twice.

**Related.** ADR-002 · ADR-014

### OEQ-003 — Future-dated expense policy

**Question.** May an expense be recorded for a date in the future?

**Why deferred.** Check-ins reject future dates because SRS-5.7 says so — a habit cannot be reported before it happens. No requirement covers expenses, and the two honest readings disagree: a scheduled rent debit is a real thing a user may want to record, while a typo'd year silently pollutes every window the analysis engine computes over. Choosing now would be inventing a requirement rather than implementing one.

**Interim constraint (in force).** Expense dates are unvalidated beyond being well-formed dates. This is the permissive option, chosen because it is the one that can be tightened later without discarding data.

**To close, a decision must state:** whether future dates are accepted, and if so how the analysis engine treats an expense dated after the window it is analysing.

**Related.** `03_SRS.md` §3 · `backend/app/services/expense_service.py`

### OEQ-004 — The backfill window makes gate G3 unreachable for weeks ✅ CLOSED

**Closed 2026-07-28 by ADR-019, option 1.** A deterministic synthetic dataset is written **below the API** by `app/demo/`, where the backfill cap does not apply because no check-in endpoint is involved. The rule stays intact for real user input; the demo bypasses the transport, not the schema. Five T3 correlational insights are now reachable through `GET /api/insights` after `python -m app.demo seed`, where before there were none.

The question and its options are kept below because the conflict itself is unresolved: a **real** user still cannot reach a behavioural insight inside their first month. That is the design working (PDR-030) rather than a defect, but if it is ever judged unacceptable, options 2 and 3 are still the alternatives.

**Question.** How does a user — or a demo — ever reach a T3 behavioural insight, given that two approved requirements work against each other?

**The conflict, found by running the finished engine against the running API.** SRS-5.6/5.7 limit check-in backfill to **30 days**. Gate G1 requires **≥ 8 complete weeks** of history and gate G3 requires **≥ 60% per-habit coverage** across them. A new user can therefore log at most ~4.3 weeks retroactively, which caps per-habit coverage over an 8-week window at roughly **54% — below the 60% floor**, before any question of data quality arises.

Measured, not predicted: seeding 16 weeks of data through the public API and calling `GET /api/insights` yields 11 descriptive insights, **zero** correlational ones, and six `DATA_SUFFICIENCY` notices reporting `exercise` coverage at 0.4167 against a required 0.60. The engine is behaving exactly as specified. The specification is what disagrees with itself.

**Why this is not a bug.** You cannot have behavioural history you did not record, and the honest consequence is that behavioural insight takes ~4–8 weeks of real use to earn. That is the product working as designed (PDR-030). The problem is narrower: **there is currently no path to seeing a T3 insight at all** — not for a new user in their first month, and not for anyone demonstrating the product.

**Options, none yet chosen:**

1. **A synthetic dataset seeded below the API**, writing directly to the database and bypassing the backfill rule. Already in V1 scope — `datasets/` exists, `data_source.is_synthetic` is in the schema (05 §3.2), and PDR-012 mandates demo data. Costs nothing in correctness because the rows are labelled synthetic. **Recommended.**
2. **Relax the backfill window** for the initial import only. Cheapest, but weakens a rule that exists because week-old self-reports are unreliable.
3. **Lower G3 for a first window.** Rejected on sight — a gate that relaxes when it fails is not a gate.

**To close, a decision must state:** which option, and if (1), whether the synthetic dataset is a committed fixture or generator output — the question `.gitignore` already declines to answer for `datasets/`.

**Related.** SRS-5.6, SRS-5.7 · `07_AI_Architecture.md` §2.5 · PDR-012, PDR-030 · ADR-015

## 9. Traceability compliance

Every document 01–12 carries a traceability table mapping its sections to PDR decision IDs.

**Compliance: 12 of 12 (100%).** Verified 2026-07-27.

The `01_Product_Vision.md` traceability defect recorded in INDEX v1.0 is resolved — the document was rewritten against the frozen PDR.

## 10. Critical path

```
    ✅ Documentation complete (Phases 0–8, 11, 12)
                    │
                    ▼
    ⚠️  Ratify 16 provisional decisions (PDR §K)      ← still open
                    │
                    ▼
    ✅ Sprint 1 · Profile, Expense, Check-in, Life Event CRUD
                    │
                    ▼
    ✅ Sprint 2 · Behavior Analysis Engine (pure, no model)
                    │
                    ▼
    ✅ Sprint 3 · AI Insight Generator (validated narration)
                    │
                    ▼
    ✅ Sprint 4 · React dashboard (presentation only)
                    │
                    ▼
    ✅ Sprint 5 · Bounded Q&A assistant (single-turn)
                    │
                    ▼
    ✅ Sprint 6 · Demo dataset & release   ◄── V1 COMPLETE
```

**Nothing in the documentation set blocks implementation**, which is why Sprints 1–6 proceeded ahead of ratification. PDR §K states the blast radius for each provisional decision, so overturning any of them has a bounded, known cost.

That blast radius has now grown. Sprint 1 made **PDR-040** (missing-data semantics) and **PDR-039** (one check-in per date) load-bearing in the `check_in` schema. Sprint 2 built the analysis engine on top of both, plus **PDR-043** (statistical gates) and **PDR-032** (confidence on T3 only) — the latter is enforced in `Insight.__post_init__`, so overturning it is a constructor change that fails ~20 tests. None of this makes ratification harder; it makes the cost of each decision concrete rather than estimated.

## 11. Change log

| Date | Version | Change |
|---|---|---|
| 2026-07-27 | 1.0 | INDEX created. PDR and Vision migrated to mandated filenames. `datasets/` and ADR directory created. Deviations D-1 … D-4 recorded. |
| 2026-07-27 | 2.0 | PDR frozen at v1.0 with 16 provisional decisions. Vision rewritten. Documents 02–12 and 13 ADRs created. README populated (D-4 closed). Traceability compliance 100%. |
| 2026-07-27 | 2.1 | Repository placed under version control. `.gitignore` corrected (four defects) and `.gitattributes` added. §6 updated for `.gitkeep` placeholders and the two dotfiles. Naming violations V-1 and V-2 recorded in §7. New §8 Open Engineering Questions opened with OEQ-001; former §8–§10 renumbered to §9–§11. |
| 2026-07-28 | 2.8 | **Ratification pack prepared.** `14_Ratification_Briefing.md` restates PDR §K's blast radius against the code that now exists, with measured test counts per decision. Surfaces a conflict nobody had recorded: **PDR-046 excludes budgets, and Sprint 2 built budget reporting on an explicit brief** — flagged with two options and a recommendation. Also records that PDR-036 shipped stricter than written, and that PDR-035/044/045 plus PDR-047's novelty term describe behaviour no code implements. |
| 2026-07-28 | 2.7 | **Sprint 6 shipped: demo dataset and release. V1 complete.** `app/demo/` — a deterministic generator with three planted patterns and two negative controls, written below the API to close **OEQ-004**: five T3 correlational insights are now reachable through `GET /api/insights`, where before there were none. `docker/` — Compose stack (api + nginx + optional ollama). `13_Demo_And_Release.md` added with the dataset design, architecture diagram and release checklist. ADR-019 added. 65 new backend + 4 new frontend tests (746 + 109). |
| 2026-07-28 | 2.6 | **Sprint 5 shipped: the bounded Q&A assistant.** `app/chat/` — a prohibited-topic guard that runs before anything else, deterministic intent routing, a per-intent context builder, and template answers assembled from Sprint 3's already-validated prose. `frontend/src/pages/Chat.tsx` with a dependency-free Markdown renderer. 135 new backend + 29 new frontend tests. ADR-018 added. No conversation state exists anywhere in the stack — the absence is the enforcement of SRS-7.7. |
| 2026-07-28 | 2.5 | **Sprint 4 shipped: the dashboard.** `frontend/` — React + TypeScript + Vite, 76 tests, a 176 KB bundle with no charting library. Four hand-written SVG charts on a palette validated for colourblind separation in both modes; every chart carries a table view. A Vite dev proxy means the backend needed no CORS change, and no backend file was modified in this sprint. ADR-017 added. |
| 2026-07-28 | 2.4 | **Sprint 3 shipped: the AI Insight Generator.** `app/narration/` — five-section explanations, code-rendered confidence, three validators, and a hand-written template for every insight type. `app/llm/` — Ollama adapter on the standard library, with `none` as the default provider. 201 new tests (546 total). ADR-016 added, superseding ADR-009 §4.4's output shape. Running qwen2.5:7b against real insights refuted the T2 causal exemption and exposed four defects in the templates; both are recorded in ADR-016. |
| 2026-07-28 | 2.3 | **Sprint 2 shipped: the Behavior Analysis Engine.** `app/analysis/` — Insight contract, ISO-week bucketing, the five gates, four non-parametric tests on the standard library, and expense/habit/event/relationship analytics. 246 new tests (345 total). ADR-015 added. `user.monthly_budget_paise` added, the one Sprint 1 change budget utilisation required. §5, §6 and §10 updated. |
| 2026-07-28 | 2.2 | **Implementation began.** Sprint 1 shipped: local profile, expense, check-in and life-event CRUD on FastAPI + SQLite, with 99 passing tests. ADR-014 added, recording the V1 simplifications to ADR-001/002/011 and the invariants they may not touch. §5, §6 and §10 updated to reflect running code. OEQ-002 (migration baseline) and OEQ-003 (future-dated expenses) opened. |
