"""The engine entry point.

``analyse(dataset, now, gates)`` is the whole public surface. Everything else
in this package is an implementation detail that this function composes.

The signature takes ``now`` rather than reading a clock, and takes a dataset
rather than a session. Both are deliberate: given the same inputs this
function returns byte-identical output, insight ids included, which is what
makes the results testable and — later — reproducible from an audit record.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.analysis import events, expenses, habits
from app.analysis.dataset import AnalysisDataset
from app.analysis.gates import DEFAULT_GATES, GateConfig
from app.analysis.models import Insight, InsightType
from app.analysis.relationships import behaviour_relationships

#: Bumped when a change alters the numbers this engine produces. Recorded on
#: every run so a stored insight can be traced to the code that made it.
ENGINE_VERSION = "1.0.0"


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    """One complete pass over a dataset."""

    insights: tuple[Insight, ...]
    #: Data Sufficiency notices — what could not be said, and what would unlock it.
    notices: tuple[Insight, ...]
    #: Run metadata: window, engine version, gate thresholds, hypothesis count.
    run: dict[str, Any]

    def by_type(self, insight_type: InsightType) -> tuple[Insight, ...]:
        return tuple(i for i in self.insights if i.type is insight_type)

    def first(self, insight_type: InsightType) -> Insight | None:
        found = self.by_type(insight_type)
        return found[0] if found else None

    def as_dict(self) -> dict[str, Any]:
        return {
            "run": self.run,
            "insights": [insight.as_dict() for insight in self.insights],
            "notices": [notice.as_dict() for notice in self.notices],
        }


def analyse(
    dataset: AnalysisDataset,
    now: datetime,
    gates: GateConfig = DEFAULT_GATES,
) -> AnalysisResult:
    """Produce every insight the data supports, and no others.

    Analytics functions return ``None`` when there is nothing truthful to say;
    those are dropped here rather than turned into empty insights. An insight
    that exists only to report its own emptiness is noise a renderer then has
    to filter, and a claim nobody can check.
    """
    produced: list[Insight] = []

    # ── Expense analytics ───────────────────────────────────────────────────
    produced.append(expenses.total_spending(dataset, now))
    produced.extend(
        insight
        for insight in (
            expenses.spending_by_category(dataset, now),
            expenses.monthly_comparison(dataset, now),
            expenses.weekly_comparison(dataset, now),
            expenses.daily_trend(dataset, now),
            expenses.budget_utilization(dataset, now),
        )
        if insight is not None
    )

    # ── Habit analytics ─────────────────────────────────────────────────────
    produced.append(habits.completion_rate(dataset, now))
    produced.append(habits.missed_days(dataset, now))
    produced.extend(
        insight
        for insight in (
            habits.streaks(dataset, now),
            habits.average_sleep(dataset, now),
            habits.exercise_frequency(dataset, now),
        )
        if insight is not None
    )

    # ── Event analytics ─────────────────────────────────────────────────────
    produced.extend(events.event_summaries(dataset, now))
    impact = events.event_impact(dataset, now)
    if impact is not None:
        produced.append(impact)

    # ── Behaviour relationships (T3) ────────────────────────────────────────
    relationships = behaviour_relationships(dataset, now, gates)
    produced.extend(relationships.insights)

    run = {
        "engine_version": ENGINE_VERSION,
        "generated_at": now.isoformat(),
        "window": dataset.window.as_dict(),
        "gates": gates.as_dict(),
        "hypotheses_tested": relationships.hypotheses_tested,
        "relationships_emitted": len(relationships.insights),
        "relationships_suppressed": len(relationships.suppressed),
        "insight_count": len(produced),
        "notice_count": len(relationships.notices),
        "inputs": {
            "expenses": len(dataset.expenses),
            "check_ins": len(dataset.check_ins),
            "events": len(dataset.events),
        },
        "currency": dataset.currency,
    }

    return AnalysisResult(
        insights=tuple(produced),
        notices=relationships.notices,
        run=run,
    )
