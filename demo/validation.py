"""Does the demo still demonstrate what it claims?

This is the check that makes the whole dataset trustworthy. It runs the **real
analysis engine** over generated data — not a mock, not a re-implementation —
and asks two questions:

1. Did every planted pattern survive all five gates?
2. Did either negative control produce a false positive?

The second matters more. A generator that manufactured a pattern everywhere
would prove the engine detects noise, which is the opposite of the claim the
product makes. 07_AI_Architecture.md §8 names **zero T3 insights on negative
controls** as the primary metric, ahead of recall on planted ones.

Pure: no database. It converts the generated seeds into the engine's own input
records and calls ``analyse``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.analysis.dataset import AnalysisDataset, CheckInRecord, EventRecord, ExpenseRecord
from app.analysis.engine import analyse
from app.analysis.models import InsightType
from app.analysis.window import AnalysisWindow
from app.core.clock import IST
from app.demo.design import NEGATIVE_CONTROLS, PLANTED_PATTERNS
from app.demo.generator import DemoDataset

#: Every insight type the demo is expected to produce. ``DATA_SUFFICIENCY`` is
#: absent on purpose: the dataset is deliberately sufficient, so a notice would
#: mean a gate failed. It is demonstrable on a short window instead
#: (``/api/insights?days=14``).
EXPECTED_TYPES: frozenset[InsightType] = frozenset(InsightType) - {
    InsightType.DATA_SUFFICIENCY
}


@dataclass(frozen=True, slots=True)
class ValidationReport:
    complete_weeks: int
    hypotheses_tested: int
    insight_types: frozenset[str]
    #: ``(habit, category) -> {q_value, confidence, test}`` for patterns found.
    found_patterns: dict[tuple[str, str], dict[str, Any]] = field(default_factory=dict)
    control_false_positives: int = 0

    @property
    def missing_insight_types(self) -> frozenset[str]:
        return frozenset(t.value for t in EXPECTED_TYPES) - self.insight_types

    @property
    def all_patterns_found(self) -> bool:
        return all(
            (pattern.habit, pattern.category.value) in self.found_patterns
            for pattern in PLANTED_PATTERNS
        )

    @property
    def is_valid(self) -> bool:
        return (
            self.all_patterns_found
            and self.control_false_positives == 0
            and not self.missing_insight_types
        )


def to_analysis_dataset(dataset: DemoDataset, window: AnalysisWindow) -> AnalysisDataset:
    """Convert generated seeds into the engine's own input records."""
    return AnalysisDataset(
        window=window,
        expenses=tuple(
            ExpenseRecord(
                id=f"demo-exp-{index}",
                date=seed.expense_date,
                amount_paise=seed.amount_paise,
                category=seed.category,
                payment_method=seed.payment_method,
                merchant=seed.merchant,
            )
            for index, seed in enumerate(dataset.expenses)
            if window.contains(seed.expense_date)
        ),
        check_ins=tuple(
            CheckInRecord(
                id=f"demo-chk-{index}",
                date=seed.log_date,
                sleep_minutes=seed.sleep_minutes,
                exercise=seed.exercise,
                home_cooked_meals=seed.home_cooked_meals,
                stress_level=seed.stress_level,
                alcohol=seed.alcohol,
                work_mode=seed.work_mode,
            )
            for index, seed in enumerate(dataset.check_ins)
            if window.contains(seed.log_date)
        ),
        events=tuple(
            EventRecord(
                id=f"demo-evt-{index}",
                event_type=seed.event_type,
                title=seed.title,
                start_date=seed.start_date,
                end_date=seed.end_date,
            )
            for index, seed in enumerate(dataset.events)
            if seed.start_date <= window.end
            and (seed.end_date or seed.start_date) >= window.start
        ),
        monthly_budget_paise=dataset.persona.monthly_budget_paise,
    )


def validate_dataset(dataset: DemoDataset, *, window_days: int = 90) -> ValidationReport:
    """Run the real engine and report against the declared design."""
    window = AnalysisWindow.trailing(end=dataset.end_date, days=window_days)
    analysis_input = to_analysis_dataset(dataset, window)
    now = datetime.combine(dataset.end_date, datetime.min.time()).replace(
        hour=9, tzinfo=IST
    )

    result = analyse(analysis_input, now)

    found: dict[tuple[str, str], dict[str, Any]] = {}
    controls = 0
    for insight in result.insights:
        if insight.type is not InsightType.BEHAVIOR_RELATIONSHIP:
            continue
        habit = str(insight.metrics["habit"])
        category = str(insight.metrics["category"])
        statistics = insight.metrics["statistics"]
        if habit in NEGATIVE_CONTROLS:
            controls += 1
            continue
        found[(habit, category)] = {
            "q_value": float(statistics["q_value"]),
            "confidence": float(insight.confidence or 0.0),
            "test": str(statistics["test"]),
        }

    return ValidationReport(
        complete_weeks=len(window.complete_weeks()),
        hypotheses_tested=int(result.run["hypotheses_tested"]),
        insight_types=frozenset(i.type.value for i in result.insights),
        found_patterns=found,
        control_false_positives=controls,
    )
