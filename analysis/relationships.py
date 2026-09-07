r"""Behaviour relationships — the T3 statistical core.

This is the module the product exists for, and the one with the most ways to
be quietly wrong.

## The hypothesis space

Six habits against fourteen spending categories is **84 hypotheses per run**.
At α = 0.05 with no correction, four would clear the bar by chance alone — and
each would be shown to the user as a discovered pattern about their life. That
number is why gate G5 is mandatory rather than a refinement.

## The unit of observation

The ISO week (07_AI_Architecture.md §2.3). A bad night's sleep shows up as a
week of takeaway, not as a same-day correlation, and weekly buckets suit how
the persona actually experiences routine.

Only **complete** weeks count. A three-day fragment at the window edge would
contribute a low spending total that is an artefact of the window.

## The missing-data rule ⭐

```
For each week, for each habit:
    observations ← days in that week with a NON-NULL value for THAT habit
    if none  → week is UNKNOWN for that habit → EXCLUDED from this test
    else     → aggregate the recorded values
```

Excluded weeks are counted and reported on the insight (SRS-6.4). They are
never imputed and never read as a recorded negative. Note that this is
per-habit: a week may be usable for the sleep tests and excluded from the
exercise tests, and the counts will differ accordingly.

## Why events are not consulted here

``events.py`` reports what happened during annotated events. This module
ignores annotations entirely. If a life event could excuse a candidate from a
gate, the gates would be negotiable — and a user could produce any correlation
they liked by annotating around it.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Sequence

from app.analysis.dataset import (
    NON_SPENDING_CATEGORIES,
    AnalysisDataset,
    CheckInRecord,
)
from app.analysis.gates import Gate, GateConfig
from app.analysis.models import Evidence, EvidenceKind, Insight, InsightTier, InsightType
from app.analysis.stats import (
    TestResult,
    benjamini_hochberg,
    kruskal_wallis,
    mann_whitney_u,
    median_paise,
    spearman,
)
from app.domain.enums import Category, WorkMode

#: Habits tested with Mann–Whitney U on two groups of weeks.
BINARY_HABITS: tuple[str, ...] = ("exercise", "alcohol")

#: Habits tested with Spearman rank correlation on a weekly mean.
NUMERIC_HABITS: tuple[str, ...] = ("sleep_minutes", "stress_level", "home_cooked_meals")

#: Habits tested with Kruskal–Wallis across their levels.
CATEGORICAL_HABITS: tuple[str, ...] = ("work_mode",)

#: Fixed order, so a run over the same data always emits insights in the same
#: sequence and ties break identically.
WORK_MODE_ORDER: dict[WorkMode, int] = {
    WorkMode.OFFICE: 0,
    WorkMode.REMOTE: 1,
    WorkMode.LEAVE: 2,
}

SPENDING_CATEGORIES: tuple[Category, ...] = tuple(
    c for c in Category if c not in NON_SPENDING_CATEGORIES
)


@dataclass(frozen=True, slots=True)
class _Week:
    """One complete ISO week of the window."""

    key: str
    start: date
    end: date
    check_ins: tuple[CheckInRecord, ...]
    spend_by_category: dict[str, int]

    def spend(self, category: Category) -> int:
        return self.spend_by_category.get(category.value, 0)

    def habit_values(self, habit: str) -> list[Any]:
        """Recorded values for one habit this week. Empty means UNKNOWN."""
        return [
            value
            for record in self.check_ins
            if (value := record.habit(habit)) is not None
        ]


@dataclass(frozen=True, slots=True)
class _Candidate:
    """A (habit, category) association that has been measured but not yet judged."""

    habit: str
    category: Category
    result: TestResult
    group_a: dict[str, Any]
    group_b: dict[str, Any]
    difference_paise: int
    relative_difference: float
    observations_included: int
    observations_excluded_unknown: int
    coverage_ratio: float
    week_keys_a: tuple[str, ...]
    week_keys_b: tuple[str, ...]

    @property
    def pair_key(self) -> str:
        return f"{self.habit}:{self.category.value}"


@dataclass(frozen=True, slots=True)
class RelationshipRun:
    """Everything one relationship pass produced, including what it refused."""

    insights: tuple[Insight, ...]
    notices: tuple[Insight, ...]
    hypotheses_tested: int
    suppressed: tuple[dict[str, Any], ...]


# ── Weekly aggregation ──────────────────────────────────────────────────────


def build_weeks(dataset: AnalysisDataset) -> list[_Week]:
    """Bucket the window into complete ISO weeks, oldest first."""
    weeks: list[_Week] = []
    for key, start, end in dataset.window.complete_weeks():
        check_ins = tuple(
            sorted(
                (r for r in dataset.check_ins if start <= r.date <= end),
                key=lambda r: r.date,
            )
        )
        spend: dict[str, int] = defaultdict(int)
        for expense in dataset.spending:
            if start <= expense.date <= end:
                spend[expense.category.value] += expense.amount_paise
        weeks.append(
            _Week(
                key=key,
                start=start,
                end=end,
                check_ins=check_ins,
                spend_by_category=dict(spend),
            )
        )
    return weeks


def _binary_week_value(week: _Week, habit: str) -> bool | None:
    """``True`` if the habit occurred at least once, ``False`` if it was
    recorded and never occurred, ``None`` if the week says nothing."""
    values = week.habit_values(habit)
    if not values:
        return None
    return any(bool(value) for value in values)


def _numeric_week_value(week: _Week, habit: str) -> float | None:
    """Mean of the recorded values. ``None`` when nothing was recorded.

    Mean rather than sum: a week with three logged days and a week with seven
    must be comparable, and a sum would rank the diligent logger higher purely
    for logging.
    """
    values = week.habit_values(habit)
    if not values:
        return None
    return sum(float(value) for value in values) / len(values)


def _modal_week_value(week: _Week, habit: str) -> WorkMode | None:
    """The most frequent level, ties broken by fixed enum order."""
    values = week.habit_values(habit)
    if not values:
        return None
    counts = Counter(values)
    return min(counts, key=lambda mode: (-counts[mode], WORK_MODE_ORDER[mode]))


# ── Candidate construction ──────────────────────────────────────────────────


def _group_stats(label: str, amounts: Sequence[int]) -> dict[str, Any]:
    return {
        "label": label,
        "n": len(amounts),
        "median_paise": median_paise(list(amounts)) if amounts else 0,
        "total_paise": sum(amounts),
    }


def _relative(difference: int, reference: int) -> float:
    """Effect relative to the reference group's level.

    Zero when the reference is zero: a percentage against a zero baseline is
    unbounded, and reporting "up ∞%" is not a claim a user can check.
    """
    if reference == 0:
        return 0.0
    return round(abs(difference) / reference, 4)


def _binary_candidate(
    weeks: list[_Week], habit: str, category: Category, gates: GateConfig
) -> tuple[_Candidate | None, Gate | None]:
    known = [(w, value) for w in weeks if (value := _binary_week_value(w, habit)) is not None]
    excluded = len(weeks) - len(known)
    coverage = len(known) / len(weeks) if weeks else 0.0

    if coverage < gates.min_coverage_ratio:
        return None, Gate.G3_COVERAGE

    with_habit = [w for w, value in known if value]
    without_habit = [w for w, value in known if not value]

    if len(with_habit) < gates.min_group_size or len(without_habit) < gates.min_group_size:
        return None, Gate.G2_GROUP_SIZE

    amounts_a = [w.spend(category) for w in with_habit]
    amounts_b = [w.spend(category) for w in without_habit]
    result = mann_whitney_u(amounts_a, amounts_b)

    group_a = _group_stats(f"weeks with {habit}", amounts_a)
    group_b = _group_stats(f"weeks without {habit}", amounts_b)
    difference = group_b["median_paise"] - group_a["median_paise"]

    return (
        _Candidate(
            habit=habit,
            category=category,
            result=result,
            group_a=group_a,
            group_b=group_b,
            difference_paise=difference,
            relative_difference=_relative(difference, group_a["median_paise"]),
            observations_included=len(known),
            observations_excluded_unknown=excluded,
            coverage_ratio=round(coverage, 4),
            week_keys_a=tuple(w.key for w in with_habit),
            week_keys_b=tuple(w.key for w in without_habit),
        ),
        None,
    )


def _numeric_candidate(
    weeks: list[_Week], habit: str, category: Category, gates: GateConfig
) -> tuple[_Candidate | None, Gate | None]:
    known = [
        (w, value) for w in weeks if (value := _numeric_week_value(w, habit)) is not None
    ]
    excluded = len(weeks) - len(known)
    coverage = len(known) / len(weeks) if weeks else 0.0

    if coverage < gates.min_coverage_ratio:
        return None, Gate.G3_COVERAGE
    # A median split produces two halves, and each must satisfy G2.
    if len(known) < gates.min_group_size * 2:
        return None, Gate.G2_GROUP_SIZE

    amounts = [w.spend(category) for w, _ in known]
    values = [value for _, value in known]
    result = spearman(values, amounts)

    # The test is the rank correlation over all weeks. The *effect size* needs
    # a rupees-per-week figure for gate G4, so the weeks are split at their
    # median habit value and the two halves compared. Splitting by index
    # rather than by value keeps the halves balanced when values tie.
    ordered = sorted(known, key=lambda row: (row[1], row[0].key))
    midpoint = len(ordered) // 2
    low_weeks = [w for w, _ in ordered[:midpoint]]
    high_weeks = [w for w, _ in ordered[len(ordered) - midpoint :]]

    low_amounts = [w.spend(category) for w in low_weeks]
    high_amounts = [w.spend(category) for w in high_weeks]

    group_a = _group_stats(f"weeks with higher {habit}", high_amounts)
    group_b = _group_stats(f"weeks with lower {habit}", low_amounts)
    difference = group_b["median_paise"] - group_a["median_paise"]

    return (
        _Candidate(
            habit=habit,
            category=category,
            result=result,
            group_a=group_a,
            group_b=group_b,
            difference_paise=difference,
            relative_difference=_relative(difference, group_a["median_paise"]),
            observations_included=len(known),
            observations_excluded_unknown=excluded,
            coverage_ratio=round(coverage, 4),
            week_keys_a=tuple(w.key for w in high_weeks),
            week_keys_b=tuple(w.key for w in low_weeks),
        ),
        None,
    )


def _categorical_candidate(
    weeks: list[_Week], habit: str, category: Category, gates: GateConfig
) -> tuple[_Candidate | None, Gate | None]:
    known = [
        (w, value) for w in weeks if (value := _modal_week_value(w, habit)) is not None
    ]
    excluded = len(weeks) - len(known)
    coverage = len(known) / len(weeks) if weeks else 0.0

    if coverage < gates.min_coverage_ratio:
        return None, Gate.G3_COVERAGE

    by_level: dict[WorkMode, list[_Week]] = defaultdict(list)
    for week, level in known:
        by_level[level].append(week)

    usable = {
        level: group
        for level, group in by_level.items()
        if len(group) >= gates.min_group_size
    }
    if len(usable) < 2:
        return None, Gate.G2_GROUP_SIZE

    levels = sorted(usable, key=lambda level: WORK_MODE_ORDER[level])
    samples = [[w.spend(category) for w in usable[level]] for level in levels]
    result = kruskal_wallis(samples)

    medians = [(level, median_paise(sample)) for level, sample in zip(levels, samples)]
    highest = max(medians, key=lambda row: (row[1], WORK_MODE_ORDER[row[0]]))
    lowest = min(medians, key=lambda row: (row[1], WORK_MODE_ORDER[row[0]]))

    high_weeks = usable[highest[0]]
    low_weeks = usable[lowest[0]]
    group_a = _group_stats(
        f"weeks mostly {lowest[0].value}", [w.spend(category) for w in low_weeks]
    )
    group_b = _group_stats(
        f"weeks mostly {highest[0].value}", [w.spend(category) for w in high_weeks]
    )
    difference = group_b["median_paise"] - group_a["median_paise"]

    return (
        _Candidate(
            habit=habit,
            category=category,
            result=result,
            group_a=group_a,
            group_b=group_b,
            difference_paise=difference,
            relative_difference=_relative(difference, group_a["median_paise"]),
            observations_included=sum(len(group) for group in usable.values()),
            observations_excluded_unknown=excluded,
            coverage_ratio=round(coverage, 4),
            week_keys_a=tuple(w.key for w in low_weeks),
            week_keys_b=tuple(w.key for w in high_weeks),
        ),
        None,
    )


# ── The run ─────────────────────────────────────────────────────────────────


def _insufficient_data_notice(
    dataset: AnalysisDataset,
    now: datetime,
    gate: Gate,
    current: Any,
    required: Any,
    subject: str | None = None,
) -> Insight:
    """The honest empty state (PDR-030, SRS-6.11).

    Under-claiming costs a session. Over-claiming costs the user.
    """
    return Insight(
        type=InsightType.DATA_SUFFICIENCY,
        tier=InsightTier.T1_DESCRIPTIVE,
        title_key=f"DATA_SUFFICIENCY_{gate.value}",
        window=dataset.window,
        metrics={
            "failed_gate": gate.value,
            "current_value": current,
            "required_value": required,
            "subject": subject,
        },
        evidence=(
            Evidence(
                kind=EvidenceKind.AGGREGATE,
                label="gate_check",
                payload={
                    "gate": gate.value,
                    "current": current,
                    "required": required,
                },
            ),
        ),
        created_at=now,
        subject=subject,
    )


def _build_insight(
    dataset: AnalysisDataset,
    now: datetime,
    candidate: _Candidate,
    q_value: float,
    hypotheses_tested: int,
    weeks_by_key: dict[str, _Week],
) -> Insight:
    higher = "group_b" if candidate.difference_paise > 0 else "group_a"

    metrics: dict[str, Any] = {
        "habit": candidate.habit,
        "category": candidate.category.value,
        "group_a": candidate.group_a,
        "group_b": candidate.group_b,
        "higher_group": higher,
        "difference_paise": candidate.difference_paise,
        "relative_difference": candidate.relative_difference,
        "statistics": {
            "test": candidate.result.test,
            "statistic": round(candidate.result.statistic, 6),
            "p_value": round(candidate.result.p_value, 6),
            "q_value": round(q_value, 6),
            "hypotheses_tested": hypotheses_tested,
        },
        "observations": {
            "included": candidate.observations_included,
            "excluded_unknown": candidate.observations_excluded_unknown,
            "coverage_ratio": candidate.coverage_ratio,
        },
        # New associations are TENTATIVE. Promotion to ESTABLISHED requires
        # passing every gate again in a later, non-identical window (SRS-6.7),
        # which needs stored history that V1 does not keep.
        "stability_status": "TENTATIVE",
        # Correlational, never causal. The renderer is bound by this flag.
        "claim_type": "ASSOCIATION",
        "currency": dataset.currency,
    }

    evidence: list[Evidence] = [
        Evidence(kind=EvidenceKind.AGGREGATE, label="group_a", payload=candidate.group_a),
        Evidence(kind=EvidenceKind.AGGREGATE, label="group_b", payload=candidate.group_b),
    ]

    # A check-in from each group, so the user can open the raw day behind the
    # classification rather than taking the grouping on trust.
    for label, keys in (("group_a_week", candidate.week_keys_a), ("group_b_week", candidate.week_keys_b)):
        for key in keys[:2]:
            week = weeks_by_key[key]
            if week.check_ins:
                record = week.check_ins[0]
                evidence.append(
                    Evidence(
                        kind=EvidenceKind.CHECK_IN,
                        label=label,
                        ref_id=record.id,
                        payload={"week": key, "date": record.date.isoformat()},
                    )
                )

    return Insight(
        type=InsightType.BEHAVIOR_RELATIONSHIP,
        tier=InsightTier.T3_CORRELATIONAL,
        title_key=f"RELATIONSHIP_{candidate.habit.upper()}_{candidate.category.value}",
        window=dataset.window,
        metrics=metrics,
        evidence=tuple(evidence),
        created_at=now,
        subject=candidate.pair_key,
        # Confidence is the complement of the false-discovery rate at which
        # this insight would be accepted. It is a reading of q, not a score
        # invented to look like one.
        confidence=round(max(0.0, min(1.0, 1.0 - q_value)), 3),
    )


def behaviour_relationships(
    dataset: AnalysisDataset, now: datetime, gates: GateConfig
) -> RelationshipRun:
    """Run every (habit, category) hypothesis through the five gates."""
    weeks = build_weeks(dataset)
    suppressed: list[dict[str, Any]] = []

    # G1 — history. Checked once for the whole run.
    if len(weeks) < gates.min_history_weeks:
        return RelationshipRun(
            insights=(),
            notices=(
                _insufficient_data_notice(
                    dataset,
                    now,
                    Gate.G1_HISTORY,
                    current=len(weeks),
                    required=gates.min_history_weeks,
                ),
            ),
            hypotheses_tested=0,
            suppressed=(),
        )

    weeks_by_key = {week.key: week for week in weeks}
    candidates: list[_Candidate] = []
    coverage_failures: dict[str, float] = {}

    for habit in BINARY_HABITS + NUMERIC_HABITS + CATEGORICAL_HABITS:
        if habit in BINARY_HABITS:
            build = _binary_candidate
        elif habit in NUMERIC_HABITS:
            build = _numeric_candidate
        else:
            build = _categorical_candidate

        for category in SPENDING_CATEGORIES:
            candidate, failed = build(weeks, habit, category, gates)
            if candidate is None:
                suppressed.append(
                    {
                        "habit": habit,
                        "category": category.value,
                        "gate": failed.value if failed else None,
                    }
                )
                if failed is Gate.G3_COVERAGE:
                    known = sum(1 for w in weeks if w.habit_values(habit))
                    coverage_failures[habit] = round(known / len(weeks), 4)
                continue
            candidates.append(candidate)

    hypotheses_tested = len(candidates)

    # G5 — Benjamini-Hochberg across ALL hypotheses tested in the run, which is
    # the family ADR-007 (decision #4) names: "FDR at q = 0.10 across every
    # hypothesis in a run." The correction is computed over the full candidate
    # set, NOT over a post-effect-size subset. Effect size and the test
    # statistic are correlated under the null (a larger median gap tends to
    # produce a smaller p-value), so shrinking the family by effect size first
    # would correct over a favourably-selected subset and weaken FDR control.
    # Correcting over the whole family is the more conservative reading, in
    # keeping with "when in doubt, say nothing."
    q_values = benjamini_hochberg(
        [c.result.p_value for c in candidates], q=gates.fdr_q
    )

    # G4 remains a NECESSARY condition, never sufficient (ADR-007 #5): an
    # association must clear both the effect-size floor and BH-FDR. A candidate
    # is attributed to G4 when the effect is trivial (checked first, matching
    # the documented gate order), otherwise to G5 when it fails significance.
    accepted: list[tuple[_Candidate, float]] = []
    for candidate, q_value in zip(candidates, q_values):
        big_enough = (
            abs(candidate.difference_paise) >= gates.min_effect_paise
            and candidate.relative_difference >= gates.min_relative_effect
        )
        if not big_enough:
            suppressed.append(
                {
                    "habit": candidate.habit,
                    "category": candidate.category.value,
                    "gate": Gate.G4_EFFECT_SIZE.value,
                    "difference_paise": candidate.difference_paise,
                    "relative_difference": candidate.relative_difference,
                }
            )
            continue
        if q_value <= gates.fdr_q:
            accepted.append((candidate, q_value))
        else:
            suppressed.append(
                {
                    "habit": candidate.habit,
                    "category": candidate.category.value,
                    "gate": Gate.G5_SIGNIFICANCE.value,
                    "p_value": round(candidate.result.p_value, 6),
                    "q_value": round(q_value, 6),
                }
            )

    # Rank by effect size, then by significance, then by name for determinism.
    accepted.sort(
        key=lambda row: (-abs(row[0].difference_paise), row[1], row[0].pair_key)
    )

    insights = tuple(
        _build_insight(dataset, now, candidate, q_value, hypotheses_tested, weeks_by_key)
        for candidate, q_value in accepted[: gates.max_relationships]
    )

    notices: list[Insight] = []
    if not insights:
        for habit, coverage in sorted(coverage_failures.items()):
            notices.append(
                _insufficient_data_notice(
                    dataset,
                    now,
                    Gate.G3_COVERAGE,
                    current=coverage,
                    required=gates.min_coverage_ratio,
                    subject=habit,
                )
            )

    return RelationshipRun(
        insights=insights,
        notices=tuple(notices),
        hypotheses_tested=hypotheses_tested,
        suppressed=tuple(suppressed),
    )
