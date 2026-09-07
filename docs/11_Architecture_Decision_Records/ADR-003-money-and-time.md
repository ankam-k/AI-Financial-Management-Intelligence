# ADR-003 — Money as integer paise; injected clock; explicit IST

**Status:** Accepted · **Date:** 2026-07-27 · **Serves:** SRS-3.10, SRS-3.11, SRS-9.1, PDR-021 · **Closes:** D-11, D-15

## Decision

Money is a `Money` value object wrapping a signed `int` of **paise**, stored as `BIGINT`. No float ever represents money at any layer. Current time is obtained only through an injected `ClockPort`. Dates are stored with explicit IST semantics, and `transaction_date` is distinct from `value_date`.

## Context

SRS-3.10 forbids floating-point money. SRS-9.1 requires deterministic analysis — which is impossible if code calls `datetime.now()` directly, since "the last 8 weeks" would differ between runs. Indian bank statements distinguish transaction date from value date, and conflating them shifts transactions between analysis windows, corrupting the weekly grouping that every T3 insight depends on.

## Alternatives

**Money — `float`.** Universally available, zero ceremony. Rejected outright: `0.1 + 0.2 != 0.3` produces user-visible rounding artifacts, and PDR-002 treats a wrong displayed number as a trust event.

**Money — `Decimal`.** Correct arithmetic, natural formatting. But `Decimal` is trivially constructible from a float (`Decimal(0.1)` silently inherits binary error), it serializes ambiguously across JSON boundaries, and nothing prevents a developer from dividing and producing an unrepresentable value.

**Money — integer minor units in a value object.** Exact by construction. Requires explicit conversion at every boundary.

**Time — direct `datetime.now()`.** Simplest. Makes deterministic tests impossible and makes "the last 8 weeks" a moving target within a single analysis run.

**Dates — store as naive local dates.** Simple, and V1 is India-only (PDR-021). But PDR-025 requires the architecture to accommodate other countries without redesigning the analysis engine, and retrofitting timezone awareness into a date-keyed analytical core is exactly the redesign PDR-025 forbids.

## Tradeoffs

| Gain | Cost |
|---|---|
| Rounding artifacts are structurally impossible | Conversion required at every I/O boundary (parse, API, display) |
| `Money` has no float constructor — the class makes misuse a type error | Slightly more verbose arithmetic |
| Injected clock makes analysis runs reproducible and testable | Every use case needing time takes a dependency |
| Date semantics explicit now | Two date columns instead of one; adapters must map both |

## Final Choice

**Integer paise in a `Money` value object; `ClockPort` injection; explicit IST with separate transaction/value dates.**

`Money` exposes no constructor accepting `float`, and no `__truediv__` returning an unrepresentable value — division allocates remainders explicitly. This makes SRS-3.10 unviolatable rather than merely mandated.

## Consequences

- Every ingestion adapter converts source amounts to paise at parse time, with an explicit rounding policy applied once and recorded.
- API responses carry paise as integers plus a formatted display string; clients never do money arithmetic.
- `ClockPort` has a `FrozenClock` test implementation, making every analysis test deterministic.
- Analysis windows are computed from the injected clock, so a run is reproducible given a fixed timestamp.
- A CI check asserts no `float` appears in any money-typed path (SRS-10.2).
- Adding a second currency later means adding a currency field to `Money`, not changing storage.
