# Deployment

| Field | Value |
|---|---|
| **Document Name** | 10_Deployment.md |
| **Product** | AI Financial Intelligence Platform |
| **Version** | 1.0 |
| **Status** | 🟢 **Approved** |
| **Owner** | Engineering |
| **Dependencies** | `04_System_Architecture.md` v1.0 · ADR-002, ADR-008, ADR-013 |
| **Traceability** | See §8. |
| **Blocks** | — |
| **Lifecycle stage** | Draft → Review → **Approved** → Frozen → Superseded |
| **Last Updated** | 2026-07-27 |

---

## Purpose

To define how the system is built, configured, deployed, operated and recovered.

## Scope

**In scope:** topology, configuration, build/release, migrations, seeding, observability, backup/restore, security posture, runbooks.

**Out of scope:** cloud provider selection, IaC, multi-region.

## Assumptions

**None.** Topology follows ADR-013; the local-inference constraint follows ADR-008.

## References

`04_System_Architecture.md` · ADR-002 · ADR-008 · ADR-013

## Related Documents

`docs/INDEX.md` · `09_Testing_Strategy.md`

---

## 1. Topology

Single host, Docker Compose (ADR-013). Local inference is not a cost choice — it is required by PDR-024's privacy commitment (ADR-008).

```
                          ┌──────────────┐
          HTTPS  ────────▶│    proxy     │  Caddy — TLS + static frontend
                          └──────┬───────┘
                                 │
                          ┌──────▼───────┐
                          │     api      │  FastAPI (stateless)
                          └───┬──────┬───┘
                              │      │
                   ┌──────────▼─┐  ┌─▼──────────┐
                   │     db     │  │   ollama   │
                   │ PostgreSQL │  │ Qwen2.5-7B │
                   └────────────┘  └────────────┘
                         │                │
                   pg_data volume   ollama_models volume
```

| Service | Image | Purpose |
|---|---|---|
| `proxy` | caddy:2 | TLS termination; serves the frontend bundle (ADR-012) |
| `api` | built | FastAPI application |
| `db` | postgres:16 | Primary datastore (ADR-002) |
| `ollama` | ollama/ollama | Local model serving (ADR-008) |

**Host requirements:** 4 vCPU, **16 GB RAM** (the 7B model dominates), 40 GB disk, Linux with Docker Engine 24+.

## 2. Configuration

Environment-based; no secret is ever committed.

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection |
| `JWT_SECRET_KEY` | Token signing (ADR-011) |
| `ACCESS_TOKEN_TTL` / `REFRESH_TOKEN_TTL` | 15m / 30d |
| `OLLAMA_BASE_URL`, `LLM_MODEL_NAME` | Model serving |
| `LLM_TIMEOUT_SECONDS` | Fallback trigger (ADR-009) |
| `ANALYSIS_MIN_HISTORY_WEEKS` | G1 — default 8 |
| `ANALYSIS_MIN_GROUP_SIZE` | G2 — default 6 |
| `ANALYSIS_MIN_COVERAGE_RATIO` | G3 — default 0.60 |
| `ANALYSIS_MIN_EFFECT_PAISE` / `_RELATIVE` | G4 — default 50000 / 0.15 |
| `ANALYSIS_FDR_Q` | G5 — default 0.10 |
| `CATEGORIZATION_CONFIDENCE_FLOOR` | Below → UNCATEGORIZED (ADR-005) |
| `SEED_SYNTHETIC_DATA` | Seed demo datasets on start |

> **The five gate thresholds are configuration (SRS-6.8) so they can be tuned against synthetic datasets — not so they can be quietly loosened in production.** Any change requires re-running INV-4 and INV-5 (`09_Testing_Strategy.md`). A deploy that changes a gate without those results is not releasable.

## 3. Build and release

```
git tag ──▶ CI ──▶ lint · type-check · import-linter
                 · unit · INVARIANTS · integration · contract · E2E
                 · AI evaluation (if AI-touching)
                        │ all green
                        ▼
              build api image + frontend bundle
                        │
                        ▼
              deploy: pull → migrate → restart → health check
```

**Any invariant failure blocks the release. There is no override** (`09_Testing_Strategy.md` §8).

The frontend builds to static assets served by `proxy` — no Node runtime in production (ADR-012).

## 4. Migrations and seeding

**Migrations** run via an Alembic entrypoint before the API starts. Reviewed by hand (ADR-002).

Two migration classes are **rejected in review**:
1. Adding a `DEFAULT` to any `check_in` habit column — a correctness regression (`05_Database_Design.md` §5.1, PDR-040🟠).
2. Introducing a floating-point type for money (SRS-3.10).

Changing narration normalization increments `normalization_version` and requires a backfill recomputing `dedup_key` (ADR-006).

**Seeding.** With `SEED_SYNTHETIC_DATA=true`, synthetic datasets load on first start (PDR-012), so `docker compose up` yields an immediately explorable application. Seeded records carry `is_synthetic = true` and are labelled everywhere (SRS-3.20).

## 5. Observability

**Logging** — structured JSON, correlation id per request, propagated through ingestion and analysis runs (SRS-9.6).

**Redaction is mandatory (SRS-8.9):** credentials and tokens are never logged at any level; amounts and merchant identities are stripped below WARNING. The redaction filter is unit-tested — a log leak of financial data is a privacy incident, and PDR-024 makes privacy a product commitment rather than a policy note.

**Health checks**

| Endpoint | Reports |
|---|---|
| `/health/live` | Process alive |
| `/health/ready` | DB reachable, migrations current |
| `/health/model` | Ollama reachable — **degraded, never unhealthy** |

> A model outage must **not** mark the API unhealthy. NFR-7 requires the product to function without the model via template fallback (ADR-009). Failing readiness on a model outage would take down a system that is, by design, still fully functional.

**Metrics** — ingestion success/duplicate/rejection counts; analysis run duration and hypotheses tested; insights emitted vs suppressed per gate; template fallback rate; validation failure rates; guard block counts by category.

**Suppression-by-gate is the key operational metric.** It reveals whether the product is silent because users lack data (G1/G3) or because gates are too strict (G4/G5) — the difference between a user problem and a product problem.

## 6. Backup and recovery

| Aspect | V1 policy |
|---|---|
| Method | Nightly `pg_dump`, retained 30 days, stored off-host |
| Model volume | Not backed up — re-pullable |
| RPO / RTO | 24 hours / 2 hours (single-host, manual) |
| Restore drill | Documented; exercised before first real user |

**A restore has never been tested until it has been tested.** The drill is part of release readiness, not an aspiration.

Backups contain personal financial data and inherit PDR-024's obligations: encrypted at rest, access-controlled, and included in the account-deletion procedure (§7).

## 7. Security posture

- TLS terminated at `proxy`; HTTP redirects to HTTPS.
- Only `proxy` publishes ports. `db` and `ollama` are reachable only on the internal Compose network — **the model server is never externally reachable.**
- Argon2id password hashing; refresh-token rotation with reuse detection (ADR-011).
- Rate limiting on `/auth/*` and `/qa/ask`.
- Non-root containers; pinned base images; dependency scanning in CI.
- **Deletion completeness (PDR-033🟠):** account deletion removes live rows immediately; backups containing deleted users age out within the 30-day retention window. This is documented as the honest limit of the guarantee rather than overstated.

## 8. Runbooks

| Situation | Response |
|---|---|
| Model unavailable | Expected degradation. Verify template fallback is serving; restart `ollama`; no user-facing outage (NFR-7). |
| Import failures spike for one bank | Likely export-format drift (ADR-004). Capture a sample, update the adapter fingerprint, add a fixture. **Never** loosen validation to make it pass. |
| Insight volume drops to zero across users | Check suppression-by-gate metrics. If G4/G5 dominate, investigate before changing thresholds — and re-run INV-4/INV-5 if changed. |
| `NOT_TRUE` feedback rises above 5% | PDR-045🟠 hard bound breached. Treat as a defect class, triage to root cause. Do **not** treat as user preference. |
| Disk pressure | `raw_record.raw_payload` JSONB is the largest consumer. It is **provenance (PDR-017) and must not be pruned** — expand disk instead. |
| Restore needed | Stop `api`, restore dump, run migrations, verify counts, restart, verify a known user's ledger totals. |

## 9. Traceability

| Section | Source |
|---|---|
| §1 Single-host Compose | ADR-013 |
| §1 Local model serving | **PDR-024**, ADR-008 |
| §2 Gate thresholds as config | SRS-6.8, PDR-043🟠 |
| §3 Invariants block release | SRS-10.*, PDR-002 |
| §4 Rejected migration classes | SRS-3.10, **SRS-5.5**, PDR-040🟠 |
| §4 Synthetic seeding | PDR-012, SRS-3.20 |
| §5 Log redaction | SRS-8.9, PDR-024 |
| §5 Model degraded ≠ unhealthy | NFR-7, ADR-009 |
| §6 Backup obligations | PDR-024, PDR-033🟠 |
| §7 Internal-only model server | PDR-024, PDR-034🟠 |
| §8 Never loosen validation | PDR-002, NFR-8 |
