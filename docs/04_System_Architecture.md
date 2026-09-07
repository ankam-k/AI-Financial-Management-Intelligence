# System Architecture

| Field | Value |
|---|---|
| **Document Name** | 04_System_Architecture.md |
| **Product** | AI Financial Intelligence Platform |
| **Version** | 1.0 |
| **Status** | 🟢 **Approved** |
| **Owner** | Engineering |
| **Dependencies** | `00_Product_Decisions_Record.md` v1.0 · `03_SRS.md` v1.0 |
| **Traceability** | Every component maps to SRS requirements. See §9. |
| **Blocks** | 05_Database_Design, 06_API_Design, 07_AI_Architecture, 10_Deployment |
| **Lifecycle stage** | Draft → Review → **Approved** → Frozen → Superseded |
| **Last Updated** | 2026-07-27 |

---

> ## ⚠️ Target architecture vs. V1 implementation
>
> **This document describes the _target_ architecture.** The shipped V1 (and
> V1.1) deliberately runs a reduced stack under ADR-014 (MVP simplifications).
> Where the two differ, the code is the source of truth for what exists today:
>
> | Concern | Target (this doc) | **V1/V1.1 as built** |
> |---|---|---|
> | Database | PostgreSQL 16 | **SQLite** (single file, FK pragma on) |
> | ORM style | SQLAlchemy 2.0 **async** | **sync** SQLAlchemy 2.0 |
> | Migrations | Alembic | **`Base.metadata.create_all`** on startup |
> | Auth / multi-user | Per-user accounts | **single local profile, no auth** |
> | Ingestion adapters | Per-bank + fallback | **not built** — manual entry / demo seed only |
> | Categorization pipeline | rules → dict → embedding | **user-selected category on entry** |
> | Deduplication (ADR-006) | content-hash on import | **n/a** — no import path in V1 |
>
> None of these are accidental; each is recorded in ADR-014. The money model,
> injected clock, statistics (ADR-007), LLM safety (ADR-009), and the advice
> guard (ADR-010) are implemented as described. Migrating to the target stack
> is a URL/driver change plus a migration pass, not a rewrite — nothing outside
> `database.py` depends on SQLite specifics.

## Purpose

To define the system's structure: its layers, module boundaries, dependency rules, and the data flow that turns an uploaded statement into a verified insight.

## Scope

**In scope:** architectural style, layering, module decomposition, ports and adapters, data flow, cross-cutting concerns, technology selections (with ADR references).

**Out of scope:** table DDL (→ `05`), endpoint contracts (→ `06`), model prompting and statistical method detail (→ `07`), deployment topology detail (→ `10`).

## Assumptions

**None.** Technology choices are recorded as ADRs in `11_Architecture_Decision_Records/`, each with context, alternatives, tradeoffs and consequences.

## References

`03_SRS.md` v1.0 · `00_Product_Decisions_Record.md` v1.0 · ADR-001 … ADR-013

## Related Documents

`docs/INDEX.md` · `05_Database_Design.md` · `06_API_Design.md` · `07_AI_Architecture.md` · `10_Deployment.md`

---

## 1. Architectural drivers

The architecture is shaped by four forces, in priority order. Where they conflict, the higher one wins.

| # | Driver | Source | Consequence |
|---|---|---|---|
| 1 | **Traceability** — every displayed number reconstructible from stored records | PDR-017, SRS-9.2 | Evidence is a first-class persisted relation, not a computed convenience |
| 2 | **Determinism** — identical data yields identical claims | PDR-031, SRS-9.1 | Analysis engine is pure and model-free; the LLM sits outside the truth path |
| 3 | **Maintainability** as the deciding criterion | PDR-002 | Clean Architecture with enforced boundaries; no logic in adapters |
| 4 | **Source extensibility** — new ingestion sources without touching downstream | PDR-013, PDR-025 | Ports and adapters at the ingestion boundary specifically |

## 2. Architectural style

**Clean Architecture (Ports & Adapters), four layers, strict inward dependency.** *(ADR-001)*

```
┌─────────────────────────────────────────────────────────────┐
│  INTERFACE            FastAPI routers · schemas · DI wiring  │
├─────────────────────────────────────────────────────────────┤
│  APPLICATION          Use cases · orchestration · ports      │
├─────────────────────────────────────────────────────────────┤
│  DOMAIN               Entities · value objects · engine      │
│                       ← no framework, no I/O, no imports out │
├─────────────────────────────────────────────────────────────┤
│  INFRASTRUCTURE       SQLAlchemy · adapters · LLM client     │
└─────────────────────────────────────────────────────────────┘

Dependency rule:  Interface → Application → Domain
                  Infrastructure → Application (implements ports)
                  Domain depends on NOTHING.
```

**Enforced, not aspirational (PDR-004):** an import-linter contract in CI fails the build if `domain` imports from `infrastructure`, `interface`, `fastapi`, or `sqlalchemy`.

**Why this matters here specifically:** the analysis engine lives in `domain`. Because `domain` cannot perform I/O or call a model, the engine is *structurally incapable* of consulting the LLM. PDR-031 ("the analysis engine is the source of truth") becomes an architectural guarantee rather than a coding convention.

## 3. Module decomposition

```
backend/app/
├── domain/                          # Pure. No I/O. No framework.
│   ├── shared/                      # Money(paise), DateRange, Confidence, Result
│   ├── transactions/                # Transaction, RawRecord, Merchant, Category
│   ├── behavior/                    # CheckIn, HabitValue(UNKNOWN|Recorded), LifeEvent
│   ├── insights/                    # Insight, Tier, Evidence, DataSufficiencyNotice
│   └── analysis/                    # ⭐ THE ANALYSIS ENGINE
│       ├── signals/                 #   deterministic aggregations (T1)
│       ├── rules/                   #   recurring & pattern detection (T2)
│       ├── statistics/              #   correlation + five gates (T3)
│       └── ranking/                 #   effect × confidence × novelty
│
├── application/                     # Use cases. Depends on domain only.
│   ├── ports/                       #   StatementSourcePort, LLMPort,
│   │                                #   Repositories, ClockPort
│   ├── ingestion/                   #   ImportStatement, GenerateSyntheticData
│   ├── behavior/                    #   RecordCheckIn, RecordLifEvent
│   ├── analysis/                    #   RunAnalysis, RankInsights
│   ├── explanation/                 #   NarrateInsight, AnswerQuestion
│   └── account/                     #   Auth, Export, DeleteSource, DeleteAccount
│
├── infrastructure/                  # Implements ports.
│   ├── persistence/                 #   SQLAlchemy models, repositories, UoW
│   ├── ingestion/adapters/          #   HDFC, ICICI, SBI, Axis, Generic, Synthetic
│   ├── llm/                         #   Qwen client, validators, guard
│   └── observability/               #   logging, correlation ids
│
└── interface/                       # FastAPI.
    ├── api/v1/                      #   routers
    ├── schemas/                     #   pydantic request/response
    ├── errors/                      #   exception → HTTP mapping
    └── dependencies.py              #   DI composition root
```

**Module boundary rule:** a domain submodule may import from `domain.shared` and its own package. Cross-imports between `transactions`, `behavior`, `insights` are mediated by `analysis`, which is the only module permitted to know about all three.

## 4. The ingestion port

Implements PDR-013 and SRS-3.2 — the decision that keeps V2's Account Aggregator from becoming a rewrite.

```
                    ┌──────────────────────────┐
                    │   StatementSourcePort    │   (application/ports)
                    │  fetch() → [RawRecord]   │
                    └──────────────────────────┘
                                 ▲
        ┌──────────┬─────────────┼─────────────┬──────────────┐
   HdfcCsv    IciciCsv       SbiCsv       GenericCsv     Synthetic
   Adapter    Adapter        Adapter      Adapter        Adapter
                                                              │
                                              ┌───────────────┴────────┐
                                              │  V2 (not built):       │
                                              │  AccountAggregator     │
                                              │  Adapter               │
                                              └────────────────────────┘
```

**The contract that makes this real:** adapters emit `RawRecord` only. `RawRecord` carries no bank-specific structure — it is `(source_id, row_number, raw_payload, extracted_fields)`. Nothing downstream of the normalizer can determine which adapter produced a record. *(ADR-004)*

**Verification:** SRS-9.5 is tested by asserting no module outside `infrastructure/ingestion/adapters` references any bank name.

## 5. Data flow

### 5.1 Ingestion — statement to ledger

```
CSV upload
    │
    ▼
[Adapter]         parse → RawRecord[]              SRS-3.1, 3.4
    │
    ▼
[Validator]       schema, ranges, date sanity      SRS-3.6
    │
    ▼
[Normalizer]      → Money(paise), IST dates,       SRS-3.10, 3.11
    │               instrument type, sign           SRS-3.12
    ▼
[Deduplicator]    content hash vs existing         SRS-3.7, 3.8, 3.9
    │
    ▼
[Merchant]        extract + normalize identity     SRS-3.13
    │
    ▼
[Categorizer]     rules → dictionary → embedding   SRS-4.1 … 4.5
    │               → UNCATEGORIZED if below floor
    ▼
[Persist]         atomic transaction               SRS-3.5
                  Transaction ←linked→ RawRecord
```

Any stage raising an error aborts the whole unit of work. Partial state is impossible by construction. *(SRS-3.5)*

### 5.2 Analysis — ledger + behavior to insight

```
   Transactions          Check-ins            Life Events
        │                    │                     │
        ▼                    ▼                     ▼
 ┌──────────────────────────────────────────────────────┐
 │              ANALYSIS ENGINE (domain, pure)          │
 │                                                      │
 │  Signals   → weekly/category aggregations       T1   │
 │  Rules     → recurring, subscriptions, spikes   T2   │
 │  Statistics→ habit × category association       T3   │
 │              │                                       │
 │              ▼                                       │
 │       ┌─────────────────────────────────┐            │
 │       │   THE FIVE GATES  (SRS-6.1)     │            │
 │       │  G1 history ≥ 8w                │            │
 │       │  G2 group size ≥ 6              │            │
 │       │  G3 coverage ≥ 60%              │            │
 │       │  G4 effect ≥ ₹500/wk & ≥15%     │            │
 │       │  G5 BH-FDR q = 0.10             │            │
 │       └─────────────────────────────────┘            │
 │           │ pass                  │ fail             │
 │           ▼                       ▼                  │
 │      Insight + Evidence    (suppressed entirely)     │
 │                            or DataSufficiencyNotice  │
 └──────────────────────────────────────────────────────┘
                     │
                     ▼
              [Ranking] top 5              SRS-6.10
                     │
                     ▼
              Structured Insight  ◄── the source of truth
                     │
        ┌────────────┴────────────┐
        ▼                         ▼
  [LLM Narrator]           [Template Renderer]
        │                         │  (fallback, always available)
        ▼                         │
  [Provenance validator]          │      SRS-7.3
  [Lexical validator]             │      SRS-7.4
        │ pass          │ fail    │
        ▼               └─────────┤
    Prose output                  ▼
                            Deterministic prose
```

**The critical property:** the insight exists, complete and displayable, *before* the LLM is invoked. The model adds language, never content. If it is unavailable, malfunctioning, or produces output failing validation, the product degrades to template prose and loses nothing factual. *(SRS-7.5, 7.6, NFR-7)*

## 6. Component responsibilities

| Component | Layer | Responsibility | SRS |
|---|---|---|---|
| `analysis.signals` | Domain | Deterministic aggregations → T1 | §2, §6 |
| `analysis.rules` | Domain | Recurring/subscription/spike detection → T2 | SRS-4.6 |
| `analysis.statistics` | Domain | Association tests, five gates → T3 | SRS-6.1 … 6.9 |
| `analysis.ranking` | Domain | effect × confidence × novelty, cap 5 | SRS-6.10 |
| `behavior.HabitValue` | Domain | ⭐ UNKNOWN vs Recorded Negative as a **type** | SRS-5.5 |
| `insights.Evidence` | Domain | Binds insight to source records | SRS-2.5 |
| `ImportStatement` | Application | Orchestrates the §5.1 pipeline | SRS-3.3 |
| `RunAnalysis` | Application | Assembles inputs, invokes engine, persists | SRS-6.* |
| `NarrateInsight` | Application | Structured → prose, with validation + fallback | SRS-7.3 … 7.6 |
| `AnswerQuestion` | Application | Guard → engine outputs → bounded answer | SRS-7.7 … 7.10 |
| `ProhibitedTopicGuard` | Infrastructure | Independent pre-model check | SRS-7.9, 7.10 |
| `ProvenanceValidator` | Infrastructure | Every number in output ∈ input | SRS-7.3 |
| `Repositories` | Infrastructure | User-scoped data access, no unscoped query | SRS-8.1 |

## 7. Cross-cutting concerns

**Money.** A `Money` value object wrapping `int` paise, with no float constructor and no float arithmetic. The type makes SRS-3.10 unviolatable rather than merely required. *(ADR-003)*

**Habit values.** `HabitValue` is a sum type — `Unknown | Recorded(T)` — not a nullable primitive. Analysis code cannot read a habit without handling `Unknown` explicitly, because the type system will not permit it. This is how SRS-5.5 is enforced structurally instead of by review discipline. *(ADR-007)*

**Time.** A `ClockPort` supplies current time; no module calls `datetime.now()` directly. All dates stored with explicit IST semantics. Determinism (SRS-9.1) requires that time be injected. *(ADR-003)*

**User scoping.** Repositories require a `user_id` in their constructor. There is no method to query without a scope, so SRS-8.1 cannot be violated by forgetting a filter. *(ADR-011)*

**Errors.** Typed domain errors bubble to `interface/errors`, which maps them to HTTP responses. No exception reaches the user unmapped. *(SRS-9.7)*

**Logging.** Structured, correlation-id tagged, with a redaction filter that strips amounts and merchant identities below WARNING. *(SRS-8.9, SRS-9.6)*

**Transactions & UoW.** One unit of work per use case. Ingestion and analysis runs are atomic. *(SRS-3.5)*

## 8. Technology selections

Each carries a full ADR with context, alternatives, tradeoffs and consequences.

| Area | Selection | ADR |
|---|---|---|
| Architectural style | Clean Architecture, ports & adapters | ADR-001 |
| Database & ORM | PostgreSQL 16, SQLAlchemy 2.0 async, Alembic **(target; V1 ships SQLite + sync + create_all — see the callout above and ADR-014)** | ADR-002 |
| Money & time | Integer paise; injected clock; IST | ADR-003 |
| Ingestion | Per-bank adapters + generic column-mapping fallback | ADR-004 |
| Categorization | Layered: rules → dictionary → embedding → UNCATEGORIZED | ADR-005 |
| Deduplication | Deterministic content hash | ADR-006 |
| Statistics | Mann–Whitney U / Spearman; BH-FDR; complete-case | ADR-007 |
| LLM serving | Qwen2.5-Instruct via local Ollama | ADR-008 |
| LLM safety | Provenance + lexical validators; template fallback | ADR-009 |
| Advice guard | Independent pre-model classifier + refusal | ADR-010 |
| Auth | JWT bearer; Argon2id hashing; scoped repositories | ADR-011 |
| Frontend | React + TypeScript + Vite | ADR-012 |
| Deployment | Docker Compose; single-host V1 | ADR-013 |

## 9. Traceability

| Architecture section | SRS | PDR |
|---|---|---|
| §2 Style & layering | SRS-9.3, 9.4 | PDR-002, 004 |
| §2 Engine in pure domain | SRS-7.1, 7.2, 9.1 | **PDR-031** |
| §4 Ingestion port | SRS-3.2, 9.5 | **PDR-013**, PDR-025 |
| §5.1 Ingestion flow | SRS-3.3 … 3.13 | PDR-009 … 011, 021, 022 |
| §5.2 Analysis flow | SRS-6.1 … 6.13 | PDR-030, 043🟠, 047🟠 |
| §5.2 LLM after truth | SRS-7.3 … 7.6 | PDR-017, **031** |
| §6 Evidence relation | SRS-2.5, 9.2 | **PDR-017** |
| §7 Money type | SRS-3.10 | PDR-002, 021 |
| §7 HabitValue sum type | **SRS-5.5** | **PDR-040🟠** |
| §7 Scoped repositories | SRS-8.1, 8.2 | PDR-034🟠, 035🟠 |
| §7 Clock injection | SRS-9.1, 6.9 | PDR-031 |
