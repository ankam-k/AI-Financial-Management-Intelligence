"""The five gates (07_AI_Architecture.md §2.5).

```
   candidate association
          │
    ┌─────▼─────┐  G1  history ≥ 8 weeks
    ├───────────┤  G2  n ≥ 6 in EACH compared group
    ├───────────┤  G3  per-habit coverage ≥ 60%
    ├───────────┤  G4  |Δ| ≥ ₹500/week AND ≥ 15% relative
    ├───────────┤  G5  BH-FDR q = 0.10 across ALL hypotheses in the run
    └─────┬─────┘
     pass │ fail → SUPPRESSED ENTIRELY (never downgraded)
          ▼
      Insight + Evidence
```

**The FDR family is every hypothesis tested in the run** (ADR-007 decision #4),
not a post-effect-size subset. G4 and G5 are both *necessary* conditions — an
association must clear the effect-size floor AND survive BH-FDR — but the
correction is computed over the whole candidate set. Shrinking the family by
effect size before correcting would weaken FDR control, because effect size and
the test statistic are correlated under the null. Effect size is checked first
only for attributing a suppression reason: significance is necessary, never
sufficient.

**Failure suppresses; it never downgrades.** There is no low-confidence tier.
When G1 or G3 fails, a Data Sufficiency Notice is emitted instead (SRS-6.11) —
telling the user what is missing is honest; showing them a weak claim is not.

The thresholds are parameters rather than constants so a demo can widen them
deliberately and visibly. The defaults are the documented values, and
``DEFAULT_GATES`` is what production uses.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Gate(str, Enum):
    """Which gate rejected a candidate. Recorded, so suppression is auditable."""

    G1_HISTORY = "G1_HISTORY"
    G2_GROUP_SIZE = "G2_GROUP_SIZE"
    G3_COVERAGE = "G3_COVERAGE"
    G4_EFFECT_SIZE = "G4_EFFECT_SIZE"
    G5_SIGNIFICANCE = "G5_SIGNIFICANCE"


@dataclass(frozen=True, slots=True)
class GateConfig:
    """Thresholds for one analysis run."""

    #: G1 — weeks of history required before any association is considered.
    min_history_weeks: int = 8
    #: G2 — observations required in each compared group.
    min_group_size: int = 6
    #: G3 — fraction of weeks in which the habit was recorded at least once.
    min_coverage_ratio: float = 0.60
    #: G4 — absolute weekly effect, in paise. ₹500.
    min_effect_paise: int = 50_000
    #: G4 — relative effect, as a fraction of the smaller group's level.
    min_relative_effect: float = 0.15
    #: G5 — Benjamini–Hochberg false discovery rate.
    fdr_q: float = 0.10
    #: Cap on emitted correlational insights per run (SRS-6.10).
    max_relationships: int = 5

    def __post_init__(self) -> None:
        if self.min_history_weeks < 1:
            raise ValueError("min_history_weeks must be at least 1")
        if self.min_group_size < 2:
            raise ValueError("min_group_size must be at least 2")
        if not 0.0 < self.min_coverage_ratio <= 1.0:
            raise ValueError("min_coverage_ratio must be in (0, 1]")
        if self.min_effect_paise < 0:
            raise ValueError("min_effect_paise cannot be negative")
        if not 0.0 <= self.min_relative_effect:
            raise ValueError("min_relative_effect cannot be negative")
        if not 0.0 < self.fdr_q <= 1.0:
            raise ValueError("fdr_q must be in (0, 1]")
        if self.max_relationships < 1:
            raise ValueError("max_relationships must be at least 1")

    def as_dict(self) -> dict[str, float | int]:
        """Recorded on every run, so a claim can be re-derived later."""
        return {
            "min_history_weeks": self.min_history_weeks,
            "min_group_size": self.min_group_size,
            "min_coverage_ratio": self.min_coverage_ratio,
            "min_effect_paise": self.min_effect_paise,
            "min_relative_effect": self.min_relative_effect,
            "fdr_q": self.fdr_q,
            "max_relationships": self.max_relationships,
        }


#: The documented production thresholds.
DEFAULT_GATES = GateConfig()
