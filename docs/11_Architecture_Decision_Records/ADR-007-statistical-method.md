# ADR-007 — Non-parametric tests, BH-FDR correction, complete-case analysis

**Status:** Accepted · **Date:** 2026-07-27 · **Serves:** **SRS-5.5**, SRS-6.1 … 6.9, PDR-040🟠, PDR-043🟠 · **Closes:** D-29

> **This is the most consequential ADR in the project.** It is where the product either earns PDR-017's promise or quietly breaks it while appearing to comply.

## Decision

1. **`HabitValue` is a sum type** — `Unknown | Recorded(T)` — not a nullable primitive.
2. **Complete-case analysis.** `Unknown` observations are excluded. No imputation of any kind.
3. **Non-parametric tests:** Mann–Whitney U for binary habit splits, Spearman rank correlation for ordinal and numeric habits.
4. **Benjamini–Hochberg FDR at q = 0.10** across every hypothesis in a run.
5. **Effect size gates before significance** — significance is necessary, never sufficient.

## Context

Six habits × ~15 categories ≈ **90 hypotheses per analysis run**. At a naive p < 0.05, roughly 4–5 would appear significant by chance alone. A user with 12 weeks of data has ~12 weekly observations per group — far too few for asymptotic assumptions.

The deeper hazard is missing data. Manual daily logging (PDR-029) guarantees gaps. The naive schema — a `BOOLEAN DEFAULT FALSE` column — silently encodes "user didn't log" as "habit didn't happen." A user who logs gym visits only on days they go would appear to have skipped the gym on every unlogged day, manufacturing a correlation from nothing. Every individual number would remain traceable to a stored row, satisfying PDR-017 in letter while destroying it in substance. **No downstream care can repair this.**

## Alternatives

### Missing data

**A. Treat missing as `false`/`0`.** Simplest, and the default that falls out of a naive schema. Catastrophic per above. Rejected absolutely.

**B. Mean/mode imputation.** Retains sample size. But it fabricates observations — inventing data is precisely what PDR-017 forbids, and it artificially narrows variance, inflating significance.

**C. Multiple imputation.** Statistically respectable. But it assumes missing-at-random, which is exactly false here: people log more on organized days, so missingness correlates with the behavior under study. It also introduces stochasticity, breaking SRS-9.1 determinism.

**D. Complete-case analysis with a coverage floor.** Discards data, reducing power. Makes no assumption about why data is missing.

### Test selection

**Parametric t-test / Pearson.** More powerful when assumptions hold. Weekly spending is right-skewed with heavy tails (one wedding, one flight), and n is small — assumptions do not hold.

**Non-parametric (Mann–Whitney, Spearman).** Robust to skew and outliers, valid at small n. Lower power.

**Bayesian estimation.** Attractive — credible intervals communicate uncertainty more honestly than p-values. But prior selection becomes an unauditable product decision, and explaining a posterior to a non-technical user is harder than explaining a group difference. Deferred, not dismissed.

### Multiplicity

**None.** Rejected: guarantees false insights, directly threatening PDR-045🟠's <5% False Insight Rate.
**Bonferroni.** Controls family-wise error. Far too conservative at 90 hypotheses with n≈12 — nothing would ever surface, making the product vacuous.
**Benjamini–Hochberg FDR.** Controls the *expected proportion* of false discoveries. At q = 0.10, at most ~10% of surfaced insights are expected false — which aligns with, and is stricter than, the <5% bound once effect-size gating also applies.

## Tradeoffs

| Gain | Cost |
|---|---|
| Missing data can never masquerade as a recorded negative | Sample sizes shrink; some real patterns go undetected |
| No fabricated observations anywhere in the pipeline | Users with sparse logging get few or no insights |
| Robust to the skew that real spending data always has | Lower statistical power than parametric alternatives |
| BH-FDR surfaces something while bounding false discoveries | q = 0.10 is a judgement call requiring empirical tuning |
| Fully deterministic | Rules out Bayesian and multiple-imputation approaches for now |

## Final Choice

All five decisions as stated. The unifying principle: **when in doubt, say nothing.** PDR-030 already establishes silence as a designed product state, so under-claiming costs a session while over-claiming costs the user.

The sum type is the load-bearing implementation detail. Analysis code physically cannot read a habit value without handling `Unknown`, because the type system refuses to compile the alternative. SRS-5.5 becomes structurally enforced rather than review-enforced.

## Consequences

- No habit column in the schema declares a `DEFAULT`. No code path coalesces NULL (SRS-5.5(d)).
- Coverage (G3) is computed per-habit over non-NULL values, not per check-in row — a user may log sleep daily and exercise rarely.
- Excluded-observation counts are recorded on every insight and shown in its evidence (SRS-6.4).
- Hypothesis count per run is recorded for audit (SRS-6.6).
- All thresholds — q, effect floors, coverage floor — are externalized configuration, tuned against synthetic datasets with planted patterns **and negative controls** (SRS-3.18, SRS-3.19).
- The negative-control test (SRS-10.5) is the primary defense: the engine must emit **zero** T3 insights on data containing no planted relationship.
- Statistical code lives in `domain/analysis/statistics`, pure and unit-testable with no DB and no model.
- If power proves too low in practice, the correct response is lengthening the analysis window — **not** loosening the gates.

## V1.1 correction (2026-08-13)

Decision #4 — "BH-FDR at q = 0.10 **across every hypothesis in a run**" — is the
authoritative statement of the family. V1.0 shipped a deviation: it applied the
correction only to the candidates that had already passed the G4 effect-size
gate, a smaller and effect-selected family. Because effect size and the test
statistic are correlated under the null, correcting over that subset is a
*weaker* correction than decision #4 intends. V1.1 restores the documented
behaviour: BH-FDR is computed over the **full** candidate set, and G4 remains a
necessary-but-not-sufficient condition applied alongside G5. The change makes
the gate strictly more conservative; the planted demo patterns still surface
(exercise ↔ Food moved from q ≈ 0.007 to q ≈ 0.047, still under 0.10) and the
negative controls remain silent. Locked by `tests/demo/test_fdr_family.py`.
