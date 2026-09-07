# API Design

| Field | Value |
|---|---|
| **Document Name** | 06_API_Design.md |
| **Product** | AI Financial Intelligence Platform |
| **Version** | 1.0 |
| **Status** | 🟢 **Approved** |
| **Owner** | Engineering |
| **Dependencies** | `03_SRS.md` v1.0 · `04_System_Architecture.md` v1.0 · `05_Database_Design.md` v1.0 |
| **Traceability** | Every endpoint cites its SRS requirement. See §11. |
| **Blocks** | Implementation, `08_UI_UX.md` |
| **Lifecycle stage** | Draft → Review → **Approved** → Frozen → Superseded |
| **Last Updated** | 2026-07-27 |

---

## Purpose

To define the HTTP contract between client and server: resources, methods, payload shapes, status codes and error semantics.

## Scope

**In scope:** REST resource design, request/response shapes, status codes, error model, versioning, auth.

**Out of scope:** handler implementation, DB queries, UI behavior (→ `08`).

## Assumptions

**None.** Every endpoint traces to an SRS requirement.

## References

`03_SRS.md` · `05_Database_Design.md` · ADR-003 (money) · ADR-010 (advice guard) · ADR-011 (auth)

## Related Documents

`docs/INDEX.md` · `07_AI_Architecture.md` · `08_UI_UX.md`

---

## 1. Conventions

**Base path:** `/api/v1`. Version in the path; breaking changes mint `/api/v2`.

**Auth:** `Authorization: Bearer <access_token>` on everything except `/auth/*` and `/demo/*` (ADR-011).

**Money — the critical convention (ADR-003, SRS-3.10):**

```json
{ "amount": { "paise": -45000, "currency": "INR", "display": "₹450.00" } }
```

Integer paise is authoritative. `display` is server-formatted. **Clients never perform money arithmetic** — a float in a client would reintroduce exactly the rounding class SRS-3.10 exists to eliminate.

**Habit values — the second critical convention (SRS-5.5, PDR-040🟠):**

```json
{ "exercise": { "state": "RECORDED", "value": false } }   // asserted: did not exercise
{ "exercise": { "state": "UNKNOWN" } }                     // not logged
```

UNKNOWN and Recorded Negative are **structurally distinct in the wire format**. A bare `false` or `null` would let a client conflate them, defeating SRS-5.5(e) at the API boundary. This shape is mandatory on every habit field in every response.

**Dates:** `YYYY-MM-DD`, IST. **Timestamps:** RFC 3339 with offset.
**Pagination:** `?limit=&cursor=`, response `{ "items": [], "next_cursor": null }`.
**Idempotency:** `Idempotency-Key` header on `POST /data-sources` (SRS-3.8).

## 2. Error model

```json
{
  "error": {
    "code": "INGESTION_PARSE_FAILED",
    "message": "Could not parse row 47: 'Withdrawal Amt.' is not a valid amount.",
    "details": { "row_number": 47, "column": "Withdrawal Amt.", "value": "N/A" },
    "correlation_id": "01J8X..."
  }
}
```

| Status | Meaning |
|---|---|
| 400 | Malformed request |
| 401 / 403 | Unauthenticated / not permitted |
| 404 | Not found **or not owned** — never distinguish; distinguishing leaks existence (SRS-8.1) |
| 409 | Conflict (duplicate check-in date) |
| 422 | Domain rule violation (backfill > 30 days) |
| 503 | Model unavailable — **never returned for insights**, which fall back to template (NFR-7) |

Every error carries `correlation_id` (SRS-9.6). No unhandled exception reaches the client (SRS-9.7).

## 3. Auth

| Method | Path | Purpose | SRS |
|---|---|---|---|
| POST | `/auth/register` | Create account; captures consent | SRS-8.7 |
| POST | `/auth/login` | Access + refresh tokens | ADR-011 |
| POST | `/auth/refresh` | Rotate refresh token | ADR-011 |
| POST | `/auth/logout` | Invalidate refresh family | ADR-011 |

`POST /auth/register` requires explicit consent flags:

```json
{ "email": "...", "password": "...",
  "consents": { "data_upload": true, "ai_processing": true } }
```

Registration is rejected without both (SRS-8.7, PDR-024).

## 4. Data sources and ingestion

| Method | Path | Purpose | SRS |
|---|---|---|---|
| POST | `/data-sources` | Upload a CSV (multipart) | SRS-3.1 |
| GET | `/data-sources` | List | — |
| GET | `/data-sources/{id}` | Status and row counts | SRS-3.6 |
| DELETE | `/data-sources/{id}` | **Cascading delete** of the source and everything derived | SRS-8.5 |
| POST | `/data-sources/preview` | Detect format, return column mapping for confirmation | ADR-004 |

**`POST /data-sources` response — all four counts, always (SRS-3.6):**

```json
{
  "id": "...", "status": "COMPLETED", "adapter": "hdfc_csv",
  "rows": { "total": 312, "imported": 298, "duplicate": 14, "rejected": 0 },
  "rejections": []
}
```

`duplicate` is reported, never hidden — silence is what NFR-8 forbids. Import is atomic: a failure returns 4xx and creates nothing (SRS-3.5).

**`POST /data-sources/preview`** returns detected columns and a proposed mapping for an unrecognized format; the user confirms rather than the system guessing (ADR-004).

## 5. Demo data

| Method | Path | Purpose | SRS |
|---|---|---|---|
| GET | `/demo/datasets` | List synthetic personalities | SRS-3.17 |
| POST | `/demo/load` | Load one into the session | SRS-3.17 |

Unauthenticated, so a first-time visitor explores without an account (PDR-012, FR-1.10). Every response from demo-backed data carries `"is_synthetic": true` (SRS-3.20).

## 6. Transactions

| Method | Path | Purpose | SRS |
|---|---|---|---|
| GET | `/transactions` | List; filter by date, category, merchant | — |
| GET | `/transactions/{id}` | Detail with provenance | SRS-3.4 |
| PATCH | `/transactions/{id}/category` | User override | SRS-4.4 |

**Every transaction carries its categorization reason (SRS-4.2):**

```json
{
  "id": "...", "transaction_date": "2026-06-12",
  "amount": { "paise": -45000, "currency": "INR", "display": "₹450.00" },
  "instrument_type": "UPI",
  "merchant": { "display_name": "Swiggy" },
  "category": {
    "value": "FOOD_DINING",
    "assigned_by": "DICTIONARY",
    "confidence": 0.94,
    "reason": "Merchant 'SWIGGY' matched the food delivery dictionary."
  },
  "provenance": { "data_source_id": "...", "raw_record_id": "...", "row_number": 47 }
}
```

`confidence` is `null` when `assigned_by = "USER"` — a user's own correction is not a probabilistic claim (PDR-032🟠).

`PATCH .../category` sets the override permanently and across re-imports (SRS-4.4).

## 7. Behavior capture

| Method | Path | Purpose | SRS |
|---|---|---|---|
| PUT | `/check-ins/{date}` | Create or update a daily check-in | SRS-5.3 |
| GET | `/check-ins/{date}` | Fetch one | — |
| GET | `/check-ins` | Range, including coverage summary | SRS-6.2 |
| POST/GET/PATCH/DELETE | `/life-events[/{id}]` | Manage life events | SRS-5.9 |

**`PUT /check-ins/2026-06-12` — partial submission is valid (SRS-5.4):**

```json
{ "sleep_hours": 6.5, "exercise": false, "stress_level": 4 }
```

Omitted fields stay UNKNOWN. `"exercise": false` is a **Recorded Negative** — an assertion, not an absence.

**Response — every field uses the two-state envelope:**

```json
{
  "log_date": "2026-06-12",
  "habits": {
    "sleep_hours":       { "state": "RECORDED", "value": 6.5 },
    "exercise":          { "state": "RECORDED", "value": false },
    "home_cooked_meals": { "state": "UNKNOWN" },
    "stress_level":      { "state": "RECORDED", "value": 4 },
    "alcohol":           { "state": "UNKNOWN" },
    "work_mode":         { "state": "UNKNOWN" }
  }
}
```

**Errors:** `422 BACKFILL_WINDOW_EXCEEDED` beyond 30 days (SRS-5.6); `422 FUTURE_DATE_NOT_ALLOWED` (SRS-5.7). Editing sets affected insights stale (SRS-5.8).

**`GET /check-ins?from=&to=`** returns per-habit coverage, since a user may log sleep daily and exercise rarely (SRS-6.2):

```json
{ "items": [...],
  "coverage": { "sleep_hours": 0.86, "exercise": 0.52, "home_cooked_meals": 0.31,
                "stress_level": 0.79, "alcohol": 0.48, "work_mode": 0.86 },
  "days_in_range": 84 }
```

## 8. Insights

| Method | Path | Purpose | SRS |
|---|---|---|---|
| GET | `/insights` | Current insights (≤5) or a sufficiency notice | SRS-6.10, 6.11 |
| GET | `/insights/{id}` | Detail | — |
| GET | `/insights/{id}/evidence` | **Full drill-down** | SRS-2.5, PDR-017 |
| POST | `/insights/{id}/feedback` | Useful / Not useful / Not true | PDR-044🟠 |
| POST | `/analysis/run` | Trigger an analysis run | SRS-6.* |

**`GET /insights` — a T3 insight in full:**

```json
{
  "insights": [{
    "id": "...", "tier": "T3", "stability_status": "TENTATIVE",
    "window": { "start": "2026-04-01", "end": "2026-06-30" },
    "narration": "Food & Dining spending was associated with weeks when no exercise was logged.",
    "narration_source": "LLM",
    "claim": {
      "habit": "exercise", "category": "FOOD_DINING",
      "group_a": { "label": "weeks with exercise", "n": 7,
                   "median": { "paise": 412000, "currency": "INR", "display": "₹4,120.00" } },
      "group_b": { "label": "weeks without exercise", "n": 6,
                   "median": { "paise": 587000, "currency": "INR", "display": "₹5,870.00" } },
      "difference": { "paise": 175000, "currency": "INR", "display": "₹1,750.00" },
      "relative_difference": 0.4247
    },
    "confidence": 0.82,
    "statistics": { "test": "mann_whitney_u", "p_value": 0.0231, "q_value": 0.0840,
                    "hypotheses_tested": 90, "fdr_level": 0.10 },
    "observations": { "included": 13, "excluded_unknown": 5, "coverage_ratio": 0.72 }
  }],
  "max_insights": 5
}
```

Note what is always present: the excluded-UNKNOWN count (SRS-6.4), the hypothesis count (SRS-6.6), the q-value (SRS-6.5), and correlational narration (SRS-2.3). `narration_source` tells the client whether prose came from the model or the template fallback (ADR-009).

**When gates fail — the honest empty state (SRS-6.11, PDR-030):**

```json
{
  "insights": [],
  "sufficiency_notice": {
    "failed_gate": "G3_COVERAGE",
    "message": "Not enough habit check-ins yet to identify reliable patterns.",
    "current": "38% of days logged in the last 12 weeks",
    "required": "60% of days logged",
    "unblocks": "Log about 18 more days to unlock behavioral insights."
  }
}
```

This is a **200**, not an error. Insufficient data is a designed state (PDR-030).

**`GET /insights/{id}/evidence`** returns the exact transactions, check-ins and life events per group role — the one-interaction drill-down of FR-5.1.

## 9. Q&A

Bounded and single-turn (PDR-037🟠, SRS-7.7).

| Method | Path | Purpose | SRS |
|---|---|---|---|
| POST | `/qa/ask` | Ask one question | SRS-7.7 … 7.10 |

**No conversation resource exists.** There is no `conversation_id`, no history endpoint, and no server-side turn state — the absence is the enforcement of SRS-7.7.

**Answered:**

```json
{ "status": "ANSWERED",
  "answer": "You spent ₹18,400 on Food & Dining in June 2026.",
  "grounded_in": [{ "type": "SIGNAL", "id": "..." }],
  "confidence": null }
```

**Refused — prohibited topic (ADR-010, PDR-027):**

```json
{ "status": "REFUSED", "refusal_reason": "PROHIBITED_TOPIC",
  "answer": "I can't help with investment decisions. I can explain your own spending patterns and habits." }
```

**Refused — not answerable from engine outputs (SRS-7.8):**

```json
{ "status": "REFUSED", "refusal_reason": "NOT_ANSWERABLE_FROM_ANALYSIS",
  "answer": "I can only answer from your recorded transactions, habits and life events." }
```

Both refusals are **200** — a refusal is a valid outcome, not a failure. Neither attempts a partial answer (ADR-010). The guard runs before the model, so prohibited content is never generated (SRS-7.9).

## 10. Account, privacy and control

| Method | Path | Purpose | SRS |
|---|---|---|---|
| GET | `/account/data-inventory` | What is stored about the user | SRS-8.8 |
| POST | `/account/export` | Full machine-readable export | SRS-8.4 |
| GET | `/account/consents` | Current consents | SRS-8.7 |
| PATCH | `/account/consents` | Update | SRS-8.7 |
| DELETE | `/account` | **Irreversible cascading deletion** | SRS-8.6 |

`DELETE /account` requires `{ "confirmation": "DELETE" }` and password re-entry. Returns `204`. All user-attributable rows are hard-deleted (PDR-033🟠); soft-delete does not satisfy the requirement.

**No endpoint anywhere returns data aggregated across users** — there is no such capability in the system (SRS-8.2, PDR-034🟠).

## 11. Traceability

| API section | SRS | PDR / ADR |
|---|---|---|
| §1 Money envelope | SRS-3.10 | ADR-003 |
| §1 Habit two-state envelope | **SRS-5.5(e)** | **PDR-040🟠, ADR-007** |
| §2 404 for not-owned | SRS-8.1 | ADR-011 |
| §3 Consent on register | SRS-8.7 | PDR-024 |
| §4 Four row counts | SRS-3.6, 3.8 | ADR-006 |
| §4 DELETE cascade | SRS-8.5 | PDR-033🟠 |
| §5 Demo unauthenticated | SRS-3.17, 3.20 | PDR-012 |
| §6 Category reason + confidence | SRS-4.2 | ADR-005, PDR-032🟠 |
| §7 Partial check-in | SRS-5.4, 5.6, 5.7 | PDR-039🟠 |
| §7 Per-habit coverage | SRS-6.2 | PDR-040🟠 |
| §8 Excluded/hypotheses/q-value | SRS-6.4 … 6.6 | PDR-043🟠, ADR-007 |
| §8 Sufficiency notice as 200 | SRS-6.11 | **PDR-030** |
| §8 Evidence drill-down | SRS-2.5 | **PDR-017** |
| §9 No conversation resource | SRS-7.7 | PDR-037🟠 |
| §9 Refusal shapes | SRS-7.8, 7.9 | **PDR-027**, ADR-010 |
| §10 Hard delete | SRS-8.6 | PDR-033🟠 |
| §10 No cross-user endpoint | SRS-8.2 | PDR-034🟠 |
