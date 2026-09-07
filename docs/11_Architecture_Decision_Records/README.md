# Architecture Decision Records

| Field | Value |
|---|---|
| **Document Name** | 11_Architecture_Decision_Records/README.md |
| **Version** | 1.5 |
| **Status** | 🟢 Living index |
| **Owner** | Engineering |
| **Dependencies** | `04_System_Architecture.md` v1.0 |
| **Traceability** | Each ADR cites the SRS/PDR requirement it serves |
| **Last Updated** | 2026-07-28 |

## Purpose

To record every significant engineering decision with its context, the alternatives considered, the tradeoffs accepted, and the consequences — so future engineers can tell *why* a choice was made and whether its reasoning still holds.

## Scope

**In scope:** engineering and technology decisions. **Out of scope:** product decisions, which belong to `00_Product_Decisions_Record.md`. The boundary: if it changes what the user gets, it is a PDR decision; if it changes how we build it, it is an ADR.

## Format

Every ADR contains: **Decision · Context · Alternatives · Tradeoffs · Final Choice · Consequences**.

## Status values

`Proposed` → `Accepted` → `Superseded by ADR-NNN` → `Deprecated`

## Register

| ADR | Title | Status | Serves |
|---|---|---|---|
| [001](ADR-001-clean-architecture.md) | Clean Architecture with ports and adapters | Accepted | PDR-002, PDR-004 |
| [002](ADR-002-database-and-orm.md) | PostgreSQL 16 + SQLAlchemy 2.0 async + Alembic | Accepted | PDR-003, SRS-9.3 |
| [003](ADR-003-money-and-time.md) | Money as integer paise; injected clock; IST | Accepted | SRS-3.10, SRS-3.11 |
| [004](ADR-004-ingestion-adapters.md) | Per-bank adapters + generic column-mapping fallback | Accepted | PDR-013, SRS-3.2 |
| [005](ADR-005-categorization.md) | Layered categorization with confidence floor | Accepted | SRS-4.1 … 4.5 |
| [006](ADR-006-deduplication.md) | Deterministic content-hash deduplication | Accepted | SRS-3.7 … 3.9 |
| [007](ADR-007-statistical-method.md) | Non-parametric tests, BH-FDR, complete-case analysis | Accepted | **SRS-5.5**, SRS-6.* |
| [008](ADR-008-llm-serving.md) | Qwen2.5-Instruct via local Ollama | Accepted | PDR-020, PDR-024 |
| [009](ADR-009-llm-safety.md) | Provenance + lexical validation, template fallback | Accepted | SRS-7.3 … 7.6 |
| [010](ADR-010-advice-guard.md) | Independent prohibited-topic guard | Accepted | **PDR-027**, SRS-7.9 |
| [011](ADR-011-authentication.md) | JWT bearer, Argon2id, constructor-scoped repositories | Accepted | SRS-8.1, PDR-035🟠 |
| [012](ADR-012-frontend-stack.md) | React + TypeScript + Vite | Accepted | PDR-046🟠 |
| [013](ADR-013-deployment.md) | Docker Compose, single-host V1 | Accepted | PDR-002 |
| [014](ADR-014-mvp-simplifications.md) | **V1 MVP simplifications** — amends 001, 002, 011 for V1 only | Accepted | PDR-002 |
| [015](ADR-015-analysis-engine-v1.md) | Analysis engine V1 — Insight contract, stdlib statistics, no persistence | Accepted | PDR-031, SRS-2.1, SRS-6.* |
| [016](ADR-016-narration-layer.md) | Narration V1 — five sections, code-rendered confidence, template-first ⚠️ | Accepted | PDR-031, SRS-7.1 … 7.6 |
| [017](ADR-017-dashboard-v1.md) | Dashboard V1 — hand-rolled SVG charts, dev proxy, validated palette | Accepted | PDR-046🟠, ADR-012 |
| [018](ADR-018-chat-assistant.md) | Chat V1 — guard-first, deterministic routing, no conversation state | Accepted | PDR-027, PDR-037🟠, SRS-7.7 |
| [019](ADR-019-demo-dataset.md) | Demo V1 — planted patterns below the API, validated by the real engine ⭐ | Accepted | PDR-012, SRS-3.18/3.19 |

> **ADR-016 supersedes ADR-009 §4.4's `{headline, body}` output shape.** Every other part of ADR-009 — the provenance validator, the lexical validator, the fallback doctrine — is implemented as written.

> **ADR-014 changes how 001, 002 and 011 should be read.** Those three describe the target architecture; 014 records which parts of them V1 does not implement yet, which parts it refuses to simplify, and what triggers each reversion. Check it before assuming any of the three describes the running code.
