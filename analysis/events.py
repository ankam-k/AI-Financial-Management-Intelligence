"""Event analytics — what spending looked like during annotated life events.

A life event is the user's own explanation for a spending change, and this
module is deliberately the *only* place that explanation is used. The
relationship engine (``relationships.py``) does not consult events at all: a
correlation is either statistically supported or suppressed, and letting an
annotation nudge that decision would make the gates negotiable.

Here, events do something narrower and more honest — they partition the
window into "days you told us something was happening" and "ordinary days",
and report both. Whether ₹8,000/day during a trip is surprising is left to
the reader, because the engine has no basis for that judgement.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any

from app.analysis.dataset import AnalysisDataset, EventRecord
from app.analysis.models import Evidence, EvidenceKind, Insight, InsightTier, InsightType
from app.analysis.stats import round_half_up


def _event_window_days(dataset: AnalysisDataset, event: EventRecord) -> list:
    """Days of the event that fall inside the analysis window."""
    return [day for day in dataset.window.iter_days() if event.covers(day)]


def event_summaries(dataset: AnalysisDataset, now: datetime) -> list[Insight]:
    """One insight per life event overlapping the window, most recent first."""
    insights: list[Insight] = []

    for event in sorted(dataset.events, key=lambda e: (e.start_date, e.id), reverse=True):
        days = _event_window_days(dataset, event)
        if not days:
            continue

        covered = set(days)
        expenses = [e for e in dataset.spending if e.date in covered]
        total = sum(e.amount_paise for e in expenses)

        by_category: dict[str, int] = defaultdict(int)
        for expense in expenses:
            by_category[expense.category.value] += expense.amount_paise
        ranked = sorted(by_category.items(), key=lambda item: (-item[1], item[0]))

        metrics: dict[str, Any] = {
            "event_id": event.id,
            "event_type": event.event_type.value,
            "title": event.title,
            "start_date": event.start_date.isoformat(),
            "end_date": event.end_date.isoformat() if event.end_date else None,
            "is_point_event": event.end_date is None,
            "event_days_total": event.day_count,
            # An event may begin before the window; only the overlap is counted.
            "event_days_in_window": len(days),
            "total_paise": total,
            "expense_count": len(expenses),
            "average_per_day_paise": round_half_up(total, len(days)),
            "by_category": [
                {"category": category, "total_paise": amount}
                for category, amount in ranked
            ],
            "top_category": ranked[0][0] if ranked else None,
            "currency": dataset.currency,
        }

        evidence: list[Evidence] = [
            Evidence(
                kind=EvidenceKind.LIFE_EVENT,
                label="event",
                ref_id=event.id,
                payload={
                    "title": event.title,
                    "event_type": event.event_type.value,
                    "start_date": event.start_date.isoformat(),
                    "end_date": event.end_date.isoformat() if event.end_date else None,
                },
            )
        ]
        evidence.extend(
            Evidence(
                kind=EvidenceKind.EXPENSE,
                label="event_expense",
                ref_id=expense.id,
                payload={
                    "date": expense.date.isoformat(),
                    "amount_paise": expense.amount_paise,
                    "category": expense.category.value,
                },
            )
            for expense in sorted(expenses, key=lambda e: (-e.amount_paise, e.id))[:3]
        )

        insights.append(
            Insight(
                type=InsightType.EVENT_SUMMARY,
                tier=InsightTier.T1_DESCRIPTIVE,
                title_key="EVENT_SUMMARY",
                window=dataset.window,
                metrics=metrics,
                evidence=tuple(evidence),
                created_at=now,
                subject=event.id,
            )
        )

    return insights


def event_impact(dataset: AnalysisDataset, now: datetime) -> Insight | None:
    """Daily spending during events against daily spending outside them.

    Compared **per day**, not per period: events are short and irregular, so
    comparing totals would report that a four-day trip cost less than the
    other eighty-six days — true, and useless.

    Returns ``None`` when either side of the comparison is empty. A
    "difference" computed against zero days is not a comparison.
    """
    if not dataset.events:
        return None

    event_days = dataset.event_days()
    all_days = list(dataset.window.iter_days())
    ordinary_days = [day for day in all_days if day not in event_days]

    if not event_days or not ordinary_days:
        return None

    during = [e for e in dataset.spending if e.date in event_days]
    outside = [e for e in dataset.spending if e.date not in event_days]

    during_total = sum(e.amount_paise for e in during)
    outside_total = sum(e.amount_paise for e in outside)
    during_daily = round_half_up(during_total, len(event_days))
    outside_daily = round_half_up(outside_total, len(ordinary_days))

    difference = during_daily - outside_daily
    relative = (
        round(difference / outside_daily, 4) if outside_daily else None
    )

    metrics: dict[str, Any] = {
        "event_days": len(event_days),
        "ordinary_days": len(ordinary_days),
        "during_total_paise": during_total,
        "outside_total_paise": outside_total,
        "during_daily_paise": during_daily,
        "outside_daily_paise": outside_daily,
        "difference_daily_paise": difference,
        "relative_difference": relative,
        "direction": (
            "HIGHER" if difference > 0 else "LOWER" if difference < 0 else "EQUAL"
        ),
        "during_expense_count": len(during),
        "outside_expense_count": len(outside),
        "event_count": len(dataset.events),
        # This is a descriptive split, not a hypothesis test. No p-value is
        # reported because none was computed, and inventing one to make the
        # comparison look rigorous is the failure mode this project exists
        # to avoid. Statistical association lives in `relationships.py`.
        "is_statistical_test": False,
        "currency": dataset.currency,
    }

    evidence: list[Evidence] = [
        Evidence(
            kind=EvidenceKind.AGGREGATE,
            label="during_events",
            payload={
                "days": len(event_days),
                "total_paise": during_total,
                "daily_paise": during_daily,
            },
        ),
        Evidence(
            kind=EvidenceKind.AGGREGATE,
            label="outside_events",
            payload={
                "days": len(ordinary_days),
                "total_paise": outside_total,
                "daily_paise": outside_daily,
            },
        ),
    ]
    evidence.extend(
        Evidence(
            kind=EvidenceKind.LIFE_EVENT,
            label="contributing_event",
            ref_id=event.id,
            payload={
                "title": event.title,
                "event_type": event.event_type.value,
                "start_date": event.start_date.isoformat(),
            },
        )
        for event in sorted(dataset.events, key=lambda e: (e.start_date, e.id))
    )

    return Insight(
        type=InsightType.EVENT_IMPACT,
        tier=InsightTier.T2_COMPARATIVE,
        title_key="EVENT_IMPACT",
        window=dataset.window,
        metrics=metrics,
        evidence=tuple(evidence),
        created_at=now,
    )
