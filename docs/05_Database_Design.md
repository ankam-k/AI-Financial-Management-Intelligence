# Database Design

| Field | Value |
|---|---|
| **Document Name** | 05_Database_Design.md |
| **Product** | AI Financial Intelligence Platform |
| **Version** | 1.0 |
| **Status** | 🟢 **Approved** |
| **Owner** | Engineering |
| **Dependencies** | `03_SRS.md` v1.0 · `04_System_Architecture.md` v1.0 · ADR-002, ADR-003, ADR-006, ADR-007 |
| **Traceability** | Every table and constraint cites its SRS requirement. See §10. |
| **Blocks** | Implementation |
| **Lifecycle stage** | Draft → Review → **Approved** → Frozen → Superseded |
| **Last Updated** | 2026-07-27 |

---

> ## ⚠️ Target engine vs. V1 implementation
>
> The schema, constraints, and semantics below are implemented **as written**
> (integer paise, the three-state habit columns with no `DEFAULT`, cascade
> deletes, CHECK constraints). What differs in V1/V1.1 is the **engine**:
> it runs on **SQLite**, not PostgreSQL, with **`Base.metadata.create_all`**
> instead of **Alembic** migrations (ADR-014). Consequences:
> Postgres-specific types are mapped to their SQLite equivalents (UUIDs stored
> as text, timestamps as naive UTC), and foreign-key enforcement is turned on
> per-connection with `PRAGMA foreign_keys=ON`. The `datasets/` and `scripts/`
> directories are placeholders — the demo dataset is generated in code
> (`app/demo/`), not stored on disk.

## Purpose

To define the persistent data model: tables, columns, types, constraints, indexes and retention rules — and to encode the SRS's correctness invariants in the schema itself, so they cannot be violated by application code.

## Scope

**In scope:** logical model, physical schema, constraints, indexes, cascade behavior, migration policy.

**Out of scope:** ORM mapping code, query implementations, endpoint shapes (→ `06`).

## Assumptions

**None.** Every design element traces to an SRS requirement or an ADR.

## References

`03_SRS.md` · `04_System_Architecture.md` · ADR-002 (PostgreSQL/SQLAlchemy) · ADR-003 (money/time) · ADR-006 (deduplication) · ADR-007 (missing data)

## Related Documents

`docs/INDEX.md` · `06_API_Design.md` · `07_AI_Architecture.md`

---

## 1. Design principles

| # | Principle | Source |
|---|---|---|
| 1 | **Money is `BIGINT` paise.** No `FLOAT`, `REAL`, or `DOUBLE PRECISION` column ever holds money. | SRS-3.10, ADR-003 |
| 2 | **No habit column has a `DEFAULT`.** NULL means UNKNOWN and must stay distinguishable from a recorded `false`/`0`. | **SRS-5.5**, ADR-007 |
| 3 | **Every user-owned row carries `user_id`** with a foreign key and an index. | SRS-8.1, ADR-011 |
| 4 | **Deletion cascades.** No soft-delete flags on user data. | SRS-8.5, SRS-8.6, PDR-033🟠 |
| 5 | **Evidence is a persisted relation**, not a computed convenience. | SRS-2.5, PDR-017 |
| 6 | **Raw source rows are retained** and linked to what they produced. | SRS-3.4, PDR-017 |
| 7 | **Currency is a column**, constrained to INR, never hardcoded. | SRS-3.14, PDR-025 |

## 2. Entity relationship overview

```
                              ┌──────────┐
                              │   user   │
                              └─────┬────┘
                                    │ 1:N (all cascade on delete)
        ┌──────────────┬────────────┼──────────────┬─────────────────┐
        ▼              ▼            ▼              ▼                 ▼
  ┌───────────┐  ┌──────────┐ ┌──────────┐  ┌────────────┐  ┌──────────────┐
  │data_source│  │ check_in │ │life_event│  │  insight   │  │consent_record│
  └─────┬─────┘  └──────────┘ └──────────┘  └─────┬──────┘  └──────────────┘
        │ 1:N                                     │ 1:N
        ▼                                         ▼
  ┌───────────┐                            ┌──────────────────┐
  │raw_record │                            │ insight_evidence │
  └─────┬─────┘                            └────────┬─────────┘
        │ 1:1                                       │ polymorphic ref
        ▼                                           │
  ┌─────────────┐  N:1  ┌──────────┐                │
  │ transaction │──────▶│ merchant │                │
  └──────┬──────┘       └──────────┘                │
         │ ◀────────────────────────────────────────┘
         │ 1:N
         ▼
  ┌──────────────────────┐
  │ category_assignment  │  (automated + user override)
  └──────────────────────┘
```

## 3. Core tables

### 3.1 `user`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `email` | CITEXT | UNIQUE, NOT NULL |
| `password_hash` | TEXT | NOT NULL — Argon2id (ADR-011) |
| `display_name` | TEXT | |
| `timezone` | TEXT | NOT NULL, DEFAULT `'Asia/Kolkata'` (ADR-003) |
| `created_at` | TIMESTAMPTZ | NOT NULL |
| `deleted_at` | TIMESTAMPTZ | NULL — **audit trail of the deletion event only**; all owned rows are hard-deleted (SRS-8.6) |

### 3.2 `data_source`

One upload or synthetic dataset. The unit of source-level deletion (SRS-8.5).

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `user_id` | UUID | FK → `user` ON DELETE CASCADE, INDEXED |
| `source_type` | ENUM | `CSV_UPLOAD` \| `SYNTHETIC` |
| `adapter_name` | TEXT | NOT NULL — e.g. `hdfc_csv`, `generic_csv` (ADR-004) |
| `is_synthetic` | BOOLEAN | NOT NULL — drives the demo-data label (SRS-3.20) |
| `original_filename` | TEXT | |
| `column_mapping` | JSONB | NULL — saved generic-adapter mapping (ADR-004) |
| `dedup_strategy` | TEXT | NOT NULL — `balance_hash` \| `occurrence_index` (ADR-006) |
| `row_count_total` / `_imported` / `_duplicate` / `_rejected` | INTEGER | NOT NULL — the four numbers shown to the user (SRS-3.6) |
| `status` | ENUM | `PENDING` \| `COMPLETED` \| `FAILED` |
| `created_at` | TIMESTAMPTZ | NOT NULL |

### 3.3 `raw_record`

Provenance. Retained so any displayed number is reconstructible (SRS-3.4, PDR-017).

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `data_source_id` | UUID | FK → `data_source` ON DELETE CASCADE, INDEXED |
| `row_number` | INTEGER | NOT NULL |
| `raw_payload` | JSONB | NOT NULL — the source row verbatim |
| `parse_status` | ENUM | `PARSED` \| `DUPLICATE` \| `REJECTED` |
| `rejection_reason` | TEXT | NULL |

`UNIQUE (data_source_id, row_number)`

### 3.4 `transaction`

The canonical ledger entry.

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `user_id` | UUID | FK → `user` ON DELETE CASCADE, INDEXED |
| `data_source_id` | UUID | FK → `data_source` ON DELETE CASCADE |
| `raw_record_id` | UUID | FK → `raw_record`, UNIQUE — 1:1 provenance link |
| `transaction_date` | DATE | NOT NULL, INDEXED (ADR-003) |
| `value_date` | DATE | NULL — distinct from transaction date (SRS-3.11) |
| **`amount_paise`** | **BIGINT** | **NOT NULL** — signed; negative = outflow. **Never FLOAT** (SRS-3.10) |
| `currency` | CHAR(3) | NOT NULL, CHECK (`currency = 'INR'`) — column, not constant (SRS-3.14) |
| `instrument_type` | ENUM | `UPI` \| `BANK` \| `DEBIT_CARD` \| `CREDIT_CARD` \| `WALLET` (SRS-3.12) |
| `narration_raw` | TEXT | NOT NULL — as received |
| `narration_normalized` | TEXT | NOT NULL — input to the dedup hash (ADR-006) |
| `merchant_id` | UUID | FK → `merchant`, NULL |
| `running_balance_paise` | BIGINT | NULL — dedup disambiguator (ADR-006) |
| **`dedup_key`** | **TEXT** | **NOT NULL** (ADR-006) |
| `normalization_version` | SMALLINT | NOT NULL — versioned so a rule change is a migration event |
| `created_at` | TIMESTAMPTZ | NOT NULL |

**Constraints and indexes**

```sql
CONSTRAINT uq_txn_dedup UNIQUE (user_id, dedup_key);        -- SRS-3.7/3.8/3.9
CREATE INDEX ix_txn_user_date ON transaction (user_id, transaction_date);
CREATE INDEX ix_txn_user_merchant ON transaction (user_id, merchant_id);
```

> `uq_txn_dedup` makes duplication **impossible at the storage layer**, not merely unlikely. SRS-3.9 is enforced by the database, not by application discipline.

### 3.5 `merchant`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `user_id` | UUID | FK → `user` ON DELETE CASCADE, INDEXED |
| `normalized_name` | TEXT | NOT NULL |
| `display_name` | TEXT | NOT NULL |
| `source` | ENUM | `DICTIONARY` \| `EXTRACTED` \| `USER` (ADR-005) |

`UNIQUE (user_id, normalized_name)` — merchants are per-user; no cross-user table exists (PDR-034🟠, SRS-8.2).

### 3.6 `category_assignment`

Separating assignment from the transaction is what lets a user override outlive re-import (SRS-4.4).

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `transaction_id` | UUID | FK → `transaction` ON DELETE CASCADE, INDEXED |
| `category` | ENUM | Fixed V1 taxonomy (§4) |
| `assigned_by` | ENUM | `USER` \| `RULE` \| `DICTIONARY` \| `EMBEDDING` (ADR-005) |
| `confidence` | NUMERIC(4,3) | NULL — **NULL when `assigned_by = 'USER'`** (SRS-4.2, PDR-032🟠) |
| `reason_code` | TEXT | NOT NULL — machine-readable |
| `reason_detail` | JSONB | NOT NULL — renders the visible explanation (SRS-4.2) |
| `is_active` | BOOLEAN | NOT NULL |
| `created_at` | TIMESTAMPTZ | NOT NULL |

```sql
CREATE UNIQUE INDEX uq_active_category
  ON category_assignment (transaction_id) WHERE is_active;
```

A user override deactivates the automated assignment and inserts a `USER` row. History is retained; precedence is unambiguous.

## 4. Category taxonomy (V1, fixed)

`FOOD_DINING` · `GROCERIES` · `TRANSPORT` · `SHOPPING` · `ENTERTAINMENT` · `UTILITIES` · `RENT_HOUSING` · `HEALTH_FITNESS` · `EDUCATION` · `TRAVEL` · `PERSONAL_CARE` · `SUBSCRIPTIONS` · `TRANSFERS` · `INCOME` · `FEES_CHARGES` · `UNCATEGORIZED`

15 spending categories drive ≈90 hypotheses per run against 6 habits — the multiplicity load ADR-007's BH-FDR correction is sized for. `TRANSFERS` and `INCOME` are excluded from behavioral correlation.

## 5. Behavior tables

### 5.1 `check_in` ⭐

**The most important table in the schema.** It implements SRS-5.5 and PDR-040🟠.

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `user_id` | UUID | FK → `user` ON DELETE CASCADE, INDEXED |
| `log_date` | DATE | NOT NULL |
| `sleep_hours` | NUMERIC(3,1) | **NULL allowed. NO DEFAULT.** CHECK (0 ≤ x ≤ 24) |
| `exercise` | BOOLEAN | **NULL allowed. NO DEFAULT.** |
| `home_cooked_meals` | SMALLINT | **NULL allowed. NO DEFAULT.** CHECK (0 ≤ x ≤ 3) |
| `stress_level` | SMALLINT | **NULL allowed. NO DEFAULT.** CHECK (1 ≤ x ≤ 5) |
| `alcohol` | BOOLEAN | **NULL allowed. NO DEFAULT.** |
| `work_mode` | ENUM | **NULL allowed. NO DEFAULT.** `OFFICE` \| `REMOTE` \| `LEAVE` |
| `created_at` / `updated_at` | TIMESTAMPTZ | NOT NULL |

```sql
CONSTRAINT uq_checkin_user_date UNIQUE (user_id, log_date);   -- SRS-5.3
CREATE INDEX ix_checkin_user_date ON check_in (user_id, log_date);
```

> ### ⭐ The `DEFAULT`-free rule — SRS-5.5, ADR-007
>
> **No habit column declares a `DEFAULT`.** This is the single most important line in this document.
>
> - **No row for a date** → UNKNOWN for all six habits *(SRS-5.5a)*
> - **NULL in an existing row** → UNKNOWN for that habit only *(SRS-5.5b)*
> - **`false` / `0`** → **Recorded Negative**: an explicit assertion the behavior did not occur *(SRS-5.5c)*
>
> A `BOOLEAN NOT NULL DEFAULT FALSE` on `exercise` would silently encode "user didn't log" as "user didn't exercise." A user who logs gym visits only on days they go would appear to have skipped every unlogged day, manufacturing a correlation from nothing — while every individual row stayed perfectly traceable, satisfying PDR-017 in letter and destroying it in substance.
>
> **A migration adding a DEFAULT to any of these six columns is a correctness regression and must be rejected in review.**

**Backfill (SRS-5.6, SRS-5.7):** `log_date ≥ CURRENT_DATE - 30` and `log_date ≤ CURRENT_DATE`, enforced in the application against the injected clock (ADR-003) — not as a DB check, since `CURRENT_DATE` in a constraint is not deterministic.

### 5.2 `life_event`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `user_id` | UUID | FK → `user` ON DELETE CASCADE, INDEXED |
| `event_type` | ENUM | `TRAVEL` \| `ILLNESS` \| `JOB_CHANGE` \| `RELOCATION` \| `FESTIVAL` \| `FAMILY_EVENT` \| `OTHER` (SRS-5.9) |
| `title` | TEXT | NOT NULL |
| `start_date` | DATE | NOT NULL |
| `end_date` | DATE | NULL — NULL = point event (SRS-5.10) |
| `notes` | TEXT | NULL |

`CHECK (end_date IS NULL OR end_date >= start_date)` — SRS-5.10

## 6. Insight tables

### 6.1 `insight`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `user_id` | UUID | FK → `user` ON DELETE CASCADE, INDEXED |
| `tier` | ENUM | `T1` \| `T2` \| `T3` (SRS-2.1) |
| `insight_type` | TEXT | NOT NULL |
| `window_start` / `window_end` | DATE | NOT NULL — the analysis window (SRS-6.12) |
| `claim_payload` | JSONB | NOT NULL — **the structured truth**; all numbers live here (ADR-009) |
| `narration_text` | TEXT | NULL — LLM or template prose |
| `narration_source` | ENUM | `LLM` \| `TEMPLATE` (ADR-009) |
| `confidence` | NUMERIC(4,3) | NULL — **NOT NULL for T3, NULL for T1/T2** (PDR-032🟠) |
| `stability_status` | ENUM | `TENTATIVE` \| `ESTABLISHED` (SRS-6.7) |
| `effect_size_paise` | BIGINT | NULL — T3 only (SRS-6.1 G4) |
| `effect_size_relative` | NUMERIC(5,4) | NULL — T3 only |
| `p_value` / `q_value` | NUMERIC(8,7) | NULL — T3 only; `q_value` is post-BH (SRS-6.5) |
| `hypotheses_tested` | INTEGER | NULL — audit trail for multiplicity (SRS-6.6) |
| `observations_included` / `observations_excluded_unknown` | INTEGER | NULL — **excluded-UNKNOWN count is surfaced** (SRS-6.4) |
| `coverage_ratio` | NUMERIC(4,3) | NULL — per-habit coverage (SRS-6.2) |
| `rank_score` | NUMERIC | NULL (SRS-6.10) |
| `is_stale` | BOOLEAN | NOT NULL — set when a check-in in the window is edited (SRS-5.8) |
| `created_at` | TIMESTAMPTZ | NOT NULL |

```sql
CHECK (tier <> 'T3' OR confidence IS NOT NULL)              -- PDR-032🟠
CHECK (tier <> 'T3' OR q_value IS NOT NULL)                 -- SRS-6.5
CHECK (tier <> 'T3' OR observations_excluded_unknown IS NOT NULL)  -- SRS-6.4
```

> These CHECKs make it impossible to persist a T3 insight lacking confidence, FDR correction, or its excluded-observation count. The gates of SRS-6.1 are enforced by the database as well as the engine.

### 6.2 `insight_evidence`

The persisted realization of PDR-017 and SRS-2.5.

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `insight_id` | UUID | FK → `insight` ON DELETE CASCADE, INDEXED |
| `evidence_type` | ENUM | `TRANSACTION` \| `CHECK_IN` \| `LIFE_EVENT` \| `AGGREGATE` |
| `transaction_id` / `check_in_id` / `life_event_id` | UUID | FK ON DELETE CASCADE, all NULL-able |
| `aggregate_payload` | JSONB | NULL — for computed evidence |
| `role` | TEXT | NOT NULL — e.g. `group_a`, `group_b`, `context` |

```sql
CHECK (num_nonnulls(transaction_id, check_in_id, life_event_id) = 1
       OR evidence_type = 'AGGREGATE')
```

**An insight with zero evidence rows is a defect (SRS-2.5).** Verified by an invariant test, not merely asserted.

### 6.3 `insight_feedback`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `insight_id` | UUID | FK → `insight` ON DELETE CASCADE |
| `user_id` | UUID | FK → `user` ON DELETE CASCADE |
| `verdict` | ENUM | `USEFUL` \| `NOT_USEFUL` \| `NOT_TRUE` (PDR-044🟠) |
| `note` | TEXT | NULL |
| `created_at` | TIMESTAMPTZ | NOT NULL |

`UNIQUE (insight_id, user_id)` — one verdict per insight, updatable.

`NOT_TRUE` feeds the False Insight Rate counter-metric and is triaged as a defect (PDR-045🟠).

### 6.4 `data_sufficiency_notice`

The honest empty state of PDR-030, persisted so it is testable rather than incidental UI copy.

| Column | Type |
|---|---|
| `id` | UUID PK |
| `user_id` | UUID FK ON DELETE CASCADE |
| `failed_gate` | ENUM `G1_HISTORY` \| `G2_GROUP_SIZE` \| `G3_COVERAGE` |
| `current_value` / `required_value` | TEXT |
| `created_at` | TIMESTAMPTZ |

## 7. Supporting tables

**`consent_record`** — `(user_id, consent_type: DATA_UPLOAD | AI_PROCESSING, granted, granted_at, revoked_at)`. SRS-8.7.

**`user_merchant_category_map`** — an override on a merchant promotes to a personal dictionary entry so future transactions resolve at layer 3 (ADR-005). SRS-4.4.

**`analysis_run`** — `(user_id, started_at, completed_at, hypotheses_tested, insights_emitted, engine_version, clock_timestamp)`. Records the injected clock value so a run is exactly reproducible (SRS-9.1, ADR-003).

## 8. Deletion behavior

| Action | Effect | SRS |
|---|---|---|
| Delete `data_source` | CASCADE → `raw_record` → `transaction` → `category_assignment`; then insights whose evidence referenced those transactions are removed | SRS-8.5 |
| Delete `user` | CASCADE across every table above. No user-attributable row survives | SRS-8.6 |
| Edit `check_in` | Insights whose window contains `log_date` set `is_stale = true`, recomputed on next run | SRS-5.8 |

**No soft-delete flag exists on any user data table.** `user.deleted_at` records only that a deletion occurred, after the owned rows are gone (PDR-033🟠).

Test SRS-10.11 asserts zero user-attributable rows remain after account deletion, table by table.

## 9. Migration policy

- Alembic, reviewed by hand; autogenerate is a draft only (ADR-002).
- **A migration adding a `DEFAULT` to any `check_in` habit column is rejected** — it is a correctness regression (§5.1).
- **A migration introducing a float type for money is rejected** (SRS-3.10).
- Changing narration normalization increments `normalization_version` and requires a backfill recomputing `dedup_key` (ADR-006).
- Every migration is reversible or documents why it is not.

## 10. Traceability

| Element | SRS | PDR / ADR |
|---|---|---|
| `amount_paise` BIGINT | SRS-3.10 | PDR-002, ADR-003 |
| `transaction_date` / `value_date` | SRS-3.11 | ADR-003 |
| `uq_txn_dedup` | SRS-3.7 … 3.9 | ADR-006 |
| `raw_record` retention | SRS-3.4 | PDR-017 |
| **`check_in` DEFAULT-free** | **SRS-5.5** | **PDR-040🟠, ADR-007** |
| `uq_checkin_user_date` | SRS-5.3 | PDR-039🟠 |
| `life_event` shape | SRS-5.9, 5.10 | PDR-042🟠 |
| `insight` T3 CHECKs | SRS-6.1, 6.4, 6.5 | PDR-043🟠, PDR-032🟠 |
| `insight_evidence` | SRS-2.5 | **PDR-017** |
| `insight_feedback` | — | PDR-044🟠, PDR-045🟠 |
| `data_sufficiency_notice` | SRS-6.11 | PDR-030 |
| `user_id` + cascade everywhere | SRS-8.1, 8.5, 8.6 | PDR-033🟠, 034🟠, 035🟠 |
| `currency` as column | SRS-3.14 | PDR-025 |
