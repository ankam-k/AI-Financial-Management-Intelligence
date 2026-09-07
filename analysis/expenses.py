"""Expense analytics — T1 sums and T2 period comparisons.

Every function takes an :class:`AnalysisDataset` and a timestamp, and returns
an ``Insight`` or ``None``. ``None`` means *there is nothing truthful to say*
— not "an error occurred". The engine turns a ``None`` into a Data
Sufficiency notice where one is useful, and into silence where it is not.

Two rules run through the module:

* ``TRANSFERS`` and ``INCOME`` are excluded from every spending figure. Moving
  money between your own accounts is not consumption.
* Comparisons use **complete** periods only. Half of July against all of June
  is a fact about the window, not about the user.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any

from app.analysis.dataset import NON_SPENDING_CATEGORIES, AnalysisDataset, ExpenseRecord
from app.analysis.models import Evidence, EvidenceKind, Insight, InsightTier, InsightType
from app.analysis.stats import mean_paise, median_paise, round_half_up
from app.analysis.window import month_end, month_key, month_start

#: Below this relative change, a period-over-period move is reported as STABLE
#: rather than as a direction. Recorded on the insight so the verdict is
#: reproducible (07_AI_Architecture.md §2.2).
STABLE_BAND = 0.05

#: Utilisation above this is reported as NEAR_LIMIT.
BUDGET_NEAR_LIMIT = 0.80


def _relative_change(current: int, previous: int) -> float | None:
    """Fractional change, or ``None`` when the baseline is zero.

    Dividing by a zero baseline yields infinity, which renders as "up ∞%" —
    a number the user cannot check and the engine should not claim.
    """
    if previous == 0:
        return None
    return round((current - previous) / previous, 4)


def _direction(current: int, previous: int) -> str:
    if previous == 0:
        return "INCREASED" if current > 0 else "STABLE"
    change = (current - previous) / previous
    if abs(change) < STABLE_BAND:
        return "STABLE"
    return "INCREASED" if change > 0 else "DECREASED"


def _expense_evidence(expense: ExpenseRecord, label: str) -> Evidence:
    return Evidence(
        kind=EvidenceKind.EXPENSE,
        label=label,
        ref_id=expense.id,
        payload={
            "date": expense.date.isoformat(),
            "amount_paise": expense.amount_paise,
            "category": expense.category.value,
            "merchant": expense.merchant,
        },
    )


def total_spending(dataset: AnalysisDataset, now: datetime) -> Insight:
    """Total outflow across the window.

    Always returns: zero spending over a window is itself a fact, and one the
    user may well want confirmed.
    """
    spending = dataset.spending
    amounts = [e.amount_paise for e in spending]
    total = sum(amounts)

    active_days = {e.date for e in spending}
    excluded = [e for e in dataset.expenses if not e.is_spending]

    by_method: dict[str, int] = defaultdict(int)
    for expense in spending:
        by_method[expense.payment_method.value] += expense.amount_paise

    metrics: dict[str, Any] = {
        "total_paise": total,
        "expense_count": len(spending),
        "window_days": dataset.window.days,
        "active_days": len(active_days),
        "average_per_day_paise": round_half_up(total, dataset.window.days),
        "average_per_active_day_paise": (
            round_half_up(total, len(active_days)) if active_days else 0
        ),
        "average_per_expense_paise": mean_paise(amounts) if amounts else 0,
        "median_expense_paise": median_paise(amounts) if amounts else 0,
        "largest_expense_paise": max(amounts) if amounts else 0,
        "by_payment_method": dict(sorted(by_method.items())),
        "excluded_non_spending_paise": sum(e.amount_paise for e in excluded),
        "excluded_non_spending_count": len(excluded),
        "excluded_categories": sorted(c.value for c in NON_SPENDING_CATEGORIES),
        "currency": dataset.currency,
    }

    evidence: list[Evidence] = [
        Evidence(
            kind=EvidenceKind.AGGREGATE,
            label="window_total",
            payload={"total_paise": total, "expense_count": len(spending)},
        )
    ]
    for expense in sorted(spending, key=lambda e: (-e.amount_paise, e.id))[:3]:
        evidence.append(_expense_evidence(expense, "largest_expense"))

    return Insight(
        type=InsightType.SPENDING_TOTAL,
        tier=InsightTier.T1_DESCRIPTIVE,
        title_key="SPENDING_TOTAL",
        window=dataset.window,
        metrics=metrics,
        evidence=tuple(evidence),
        created_at=now,
    )


def spending_by_category(dataset: AnalysisDataset, now: datetime) -> Insight | None:
    """Breakdown by category, largest first."""
    spending = dataset.spending
    if not spending:
        return None

    totals: dict[str, int] = defaultdict(int)
    counts: dict[str, int] = defaultdict(int)
    for expense in spending:
        totals[expense.category.value] += expense.amount_paise
        counts[expense.category.value] += 1

    grand_total = sum(totals.values())
    ordered = sorted(totals.items(), key=lambda item: (-item[1], item[0]))

    breakdown = [
        {
            "category": category,
            "total_paise": amount,
            "expense_count": counts[category],
            "share_ratio": round(amount / grand_total, 4) if grand_total else 0.0,
        }
        for category, amount in ordered
    ]

    top_category, top_amount = ordered[0]
    metrics: dict[str, Any] = {
        "total_paise": grand_total,
        "category_count": len(ordered),
        "categories": breakdown,
        "top_category": top_category,
        "top_category_paise": top_amount,
        "top_category_share_ratio": (
            round(top_amount / grand_total, 4) if grand_total else 0.0
        ),
        "currency": dataset.currency,
    }

    evidence = tuple(
        Evidence(
            kind=EvidenceKind.AGGREGATE,
            label=f"category:{row['category']}",
            payload=row,
        )
        for row in breakdown
    )

    return Insight(
        type=InsightType.SPENDING_BY_CATEGORY,
        tier=InsightTier.T1_DESCRIPTIVE,
        title_key="SPENDING_BY_CATEGORY",
        window=dataset.window,
        metrics=metrics,
        evidence=evidence,
        created_at=now,
        subject=top_category,
    )


def _period_comparison(
    dataset: AnalysisDataset,
    now: datetime,
    periods: list[tuple[str, Any, Any]],
    insight_type: InsightType,
    title_key: str,
    period_label: str,
) -> Insight | None:
    """Compare the two most recent complete periods of a given kind."""
    if len(periods) < 2:
        return None

    # "₹0 this week, ₹0 last week, STABLE" is true and reads as a finding. A
    # genuine drop to zero after a spending period is worth reporting; a user
    # with no data at all has nothing to compare. The distinction is whether
    # the window contains any spending, not whether a period does.
    if not dataset.spending:
        return None

    totals: dict[str, int] = {key: 0 for key, _, _ in periods}
    counts: dict[str, int] = {key: 0 for key, _, _ in periods}
    bounds = {key: (start, end) for key, start, end in periods}

    for expense in dataset.spending:
        for key, start, end in periods:
            if start <= expense.date <= end:
                totals[key] += expense.amount_paise
                counts[key] += 1
                break

    previous_key, current_key = periods[-2][0], periods[-1][0]
    previous, current = totals[previous_key], totals[current_key]

    metrics: dict[str, Any] = {
        "period_type": period_label,
        "current_period": current_key,
        "previous_period": previous_key,
        "current_paise": current,
        "previous_paise": previous,
        "difference_paise": current - previous,
        "relative_change": _relative_change(current, previous),
        "direction": _direction(current, previous),
        "stable_band": STABLE_BAND,
        "current_expense_count": counts[current_key],
        "previous_expense_count": counts[previous_key],
        "periods": [
            {
                "period": key,
                "start": bounds[key][0].isoformat(),
                "end": bounds[key][1].isoformat(),
                "total_paise": totals[key],
                "expense_count": counts[key],
            }
            for key, _, _ in periods
        ],
        "complete_periods_available": len(periods),
        "currency": dataset.currency,
    }

    evidence = tuple(
        Evidence(
            kind=EvidenceKind.AGGREGATE,
            label=f"{period_label.lower()}:{key}",
            payload={
                "period": key,
                "total_paise": totals[key],
                "expense_count": counts[key],
                "start": bounds[key][0].isoformat(),
                "end": bounds[key][1].isoformat(),
            },
        )
        for key in (previous_key, current_key)
    )

    return Insight(
        type=insight_type,
        tier=InsightTier.T2_COMPARATIVE,
        title_key=title_key,
        window=dataset.window,
        metrics=metrics,
        evidence=evidence,
        created_at=now,
        subject=current_key,
    )


def monthly_comparison(dataset: AnalysisDataset, now: datetime) -> Insight | None:
    """Most recent complete calendar month against the one before it."""
    return _period_comparison(
        dataset,
        now,
        dataset.window.complete_months(),
        InsightType.SPENDING_MONTHLY_COMPARISON,
        "SPENDING_MONTHLY_COMPARISON",
        "MONTH",
    )


def weekly_comparison(dataset: AnalysisDataset, now: datetime) -> Insight | None:
    """Most recent complete ISO week against the one before it."""
    return _period_comparison(
        dataset,
        now,
        dataset.window.complete_weeks(),
        InsightType.SPENDING_WEEKLY_COMPARISON,
        "SPENDING_WEEKLY_COMPARISON",
        "WEEK",
    )


def daily_trend(dataset: AnalysisDataset, now: datetime) -> Insight | None:
    """Per-day series, plus a first-half/second-half direction.

    Days with no spending appear as zero rather than being omitted: a gap in a
    series reads as missing data, and here it is a recorded fact.
    """
    spending = dataset.spending
    if not spending:
        return None

    daily: dict[str, int] = {day.isoformat(): 0 for day in dataset.window.iter_days()}
    for expense in spending:
        daily[expense.date.isoformat()] += expense.amount_paise

    series = [{"date": day, "total_paise": amount} for day, amount in daily.items()]
    values = list(daily.values())
    midpoint = len(values) // 2
    first_half, second_half = sum(values[:midpoint]), sum(values[midpoint:])

    busiest = max(series, key=lambda row: (row["total_paise"], row["date"]))

    metrics: dict[str, Any] = {
        "series": series,
        "window_days": dataset.window.days,
        "first_half_paise": first_half,
        "second_half_paise": second_half,
        "difference_paise": second_half - first_half,
        "relative_change": _relative_change(second_half, first_half),
        "direction": _direction(second_half, first_half),
        "stable_band": STABLE_BAND,
        "busiest_day": busiest["date"],
        "busiest_day_paise": busiest["total_paise"],
        "zero_spend_days": sum(1 for value in values if value == 0),
        "currency": dataset.currency,
    }

    evidence = (
        Evidence(
            kind=EvidenceKind.AGGREGATE,
            label="first_half",
            payload={"total_paise": first_half, "days": midpoint},
        ),
        Evidence(
            kind=EvidenceKind.AGGREGATE,
            label="second_half",
            payload={"total_paise": second_half, "days": len(values) - midpoint},
        ),
    )

    return Insight(
        type=InsightType.SPENDING_DAILY_TREND,
        tier=InsightTier.T1_DESCRIPTIVE,
        title_key="SPENDING_DAILY_TREND",
        window=dataset.window,
        metrics=metrics,
        evidence=evidence,
        created_at=now,
    )


def budget_utilization(dataset: AnalysisDataset, now: datetime) -> Insight | None:
    """Spending against the monthly budget, for the month the window ends in.

    Suppressed entirely when no budget is set. Inventing a budget — from
    average spend, say — would produce a utilisation figure measured against a
    number the user never chose.
    """
    budget = dataset.monthly_budget_paise
    if budget is None:
        return None

    anchor = dataset.window.end
    period_start = month_start(anchor)
    period_end = month_end(anchor)
    covered_from = max(period_start, dataset.window.start)

    spent = sum(
        e.amount_paise for e in dataset.spending if covered_from <= e.date <= anchor
    )
    utilisation = round(spent / budget, 4)
    days_elapsed = (anchor - period_start).days + 1
    days_in_month = (period_end - period_start).days + 1

    if spent > budget:
        status = "OVER_BUDGET"
    elif utilisation >= BUDGET_NEAR_LIMIT:
        status = "NEAR_LIMIT"
    else:
        status = "WITHIN_BUDGET"

    metrics: dict[str, Any] = {
        "month": month_key(anchor),
        "budget_paise": budget,
        "spent_paise": spent,
        "remaining_paise": budget - spent,
        "utilization_ratio": utilisation,
        "status": status,
        "near_limit_threshold": BUDGET_NEAR_LIMIT,
        "days_elapsed": days_elapsed,
        "days_in_month": days_in_month,
        "month_start": period_start.isoformat(),
        "as_of": anchor.isoformat(),
        # False when the window starts mid-month, in which case `spent_paise`
        # counts only the covered part and understates the true figure.
        "covers_full_month_to_date": covered_from == period_start,
        "currency": dataset.currency,
    }

    evidence = (
        Evidence(
            kind=EvidenceKind.AGGREGATE,
            label="month_to_date",
            payload={
                "month": month_key(anchor),
                "spent_paise": spent,
                "budget_paise": budget,
                "from": covered_from.isoformat(),
                "to": anchor.isoformat(),
            },
        ),
    )

    return Insight(
        type=InsightType.BUDGET_UTILIZATION,
        tier=InsightTier.T1_DESCRIPTIVE,
        title_key="BUDGET_UTILIZATION",
        window=dataset.window,
        metrics=metrics,
        evidence=evidence,
        created_at=now,
        subject=month_key(anchor),
    )
