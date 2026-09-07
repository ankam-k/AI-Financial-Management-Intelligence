r"""Deterministic narration, written by hand.

**This is not a stub for when the model is missing.** It is what runs by
default, what every user sees whenever a generation is rejected, and the
baseline the model has to improve on (07_AI_Architecture §5.3, SRS-7.6).
Nothing factual is lost when it is used — only fluency.

Because these strings are assembled from the same metrics the model would
receive, they are correct by construction: no template can invent a number,
because every number it prints is read out of the insight. ``test_templates``
nonetheless runs the full validator suite over template output, so a template
that drifted into causal phrasing or cited a truncated value would fail the
build alongside a model that did.

Every ``InsightType`` must have an entry here. A parametrised test over the
enum fails if one is added without prose, so an unrenderable insight cannot
reach a user.
"""

from __future__ import annotations

from typing import Any, Callable, Mapping

from app.analysis.models import Insight, InsightTier, InsightType
from app.domain.money import format_paise

#: Rendered sections: observation, evidence, interpretation, suggestion.
Sections = tuple[str, str, str, str | None]

HABIT_LABELS: dict[str, str] = {
    "sleep_minutes": "sleep",
    "exercise": "exercise",
    "home_cooked_meals": "home-cooked meals",
    "stress_level": "stress level",
    "alcohol": "alcohol",
    "work_mode": "work mode",
}

CATEGORY_LABELS: dict[str, str] = {
    "FOOD_DINING": "Food & Dining",
    "GROCERIES": "Groceries",
    "TRANSPORT": "Transport",
    "SHOPPING": "Shopping",
    "ENTERTAINMENT": "Entertainment",
    "UTILITIES": "Utilities",
    "RENT_HOUSING": "Rent & Housing",
    "HEALTH_FITNESS": "Health & Fitness",
    "EDUCATION": "Education",
    "TRAVEL": "Travel",
    "PERSONAL_CARE": "Personal Care",
    "SUBSCRIPTIONS": "Subscriptions",
    "TRANSFERS": "Transfers",
    "INCOME": "Income",
    "FEES_CHARGES": "Fees & Charges",
    "UNCATEGORIZED": "Uncategorised",
}

GATE_LABELS: dict[str, str] = {
    "G1_HISTORY": "not enough history",
    "G2_GROUP_SIZE": "not enough weeks in one of the compared groups",
    "G3_COVERAGE": "that habit was not logged often enough",
}


def money(paise: int) -> str:
    """``412050`` → ``"₹4,120.50"``. Integer arithmetic throughout."""
    text = format_paise(paise)
    negative = text.startswith("-")
    whole, _, fraction = text.lstrip("-").partition(".")
    return f"{'-' if negative else ''}₹{int(whole):,}.{fraction}"


def percent(ratio: float, places: int = 1) -> str:
    return f"{abs(ratio) * 100:.{places}f}%"


def habit_label(name: str | None) -> str:
    return HABIT_LABELS.get(name or "", name or "that habit")


def category_label(name: str | None) -> str:
    return CATEGORY_LABELS.get(name or "", (name or "spending").replace("_", " ").title())


# ── Confidence, rendered by code and never by the model ─────────────────────


def render_confidence(insight: Insight) -> str:
    """The confidence sentence.

    Derived from the insight's tier and statistics. The model is never asked
    for a confidence figure, so it cannot invent one — which is a stronger
    guarantee than checking one afterwards.
    """
    if insight.type is InsightType.DATA_SUFFICIENCY:
        return (
            "No conclusion is drawn here, so there is no confidence figure — this "
            "is a note about what the data cannot yet support."
        )

    if insight.tier is InsightTier.T3_CORRELATIONAL and insight.confidence is not None:
        statistics = insight.metrics.get("statistics", {})
        tested = statistics.get("hypotheses_tested")
        q_value = statistics.get("q_value")
        detail = ""
        if isinstance(tested, int) and q_value is not None:
            # `q_value` is this association's own adjusted p-value, not the
            # false-discovery rate it was tested against — describing it as the
            # rate would misstate what the number means.
            detail = (
                f" It was one of {tested} associations tested in this run, and its "
                f"p-value after correction for multiple comparisons was {q_value}."
            )
        return f"Confidence {percent(insight.confidence, 1)}.{detail}"

    if insight.tier is InsightTier.T2_COMPARATIVE:
        return (
            "This compares two complete periods directly. It is arithmetic over what "
            "you recorded, not a statistical estimate, so no confidence figure applies."
        )

    return (
        "This is exact arithmetic over what you recorded, not a statistical estimate, "
        "so no confidence figure applies."
    )


# ── Per-type templates ──────────────────────────────────────────────────────


def _spending_total(metrics: Mapping[str, Any], insight: Insight) -> Sections:
    total = metrics["total_paise"]
    days = metrics["window_days"]
    count = metrics["expense_count"]

    if count == 0:
        return (
            f"You have no recorded spending in the last {days} days.",
            f"No expenses were logged across the {days}-day window.",
            "There is nothing to analyse yet. Adding expenses will let the rest of "
            "the analysis run.",
            None,
        )

    observation = f"You spent {money(total)} over the last {days} days."
    evidence = (
        f"That is {count} expenses across {metrics['active_days']} days with any "
        f"spending, averaging {money(metrics['average_per_day_paise'])} per day. "
        f"The largest single expense was {money(metrics['largest_expense_paise'])}."
    )
    interpretation = (
        f"Your typical expense is {money(metrics['median_expense_paise'])}, against a "
        f"mean of {money(metrics['average_per_expense_paise'])}."
    )
    if metrics.get("excluded_non_spending_count"):
        interpretation += (
            f" A further {metrics['excluded_non_spending_count']} entries "
            f"({money(metrics['excluded_non_spending_paise'])}) are transfers or income "
            "and are excluded from every spending figure here."
        )
    return observation, evidence, interpretation, None


def _spending_by_category(metrics: Mapping[str, Any], insight: Insight) -> Sections:
    top = category_label(metrics["top_category"])
    return (
        f"{top} is your largest spending category.",
        f"It accounts for {money(metrics['top_category_paise'])} of "
        f"{money(metrics['total_paise'])} total, or "
        f"{percent(metrics['top_category_share_ratio'])} of everything you spent "
        f"across {metrics['category_count']} categories.",
        f"Spending is concentrated in {top}, so changes there move your total more "
        "than changes anywhere else.",
        None,
    )


def _period_comparison(metrics: Mapping[str, Any], insight: Insight) -> Sections:
    unit = "month" if metrics["period_type"] == "MONTH" else "week"
    direction = metrics["direction"]
    current = metrics["current_paise"]
    previous = metrics["previous_paise"]
    difference = abs(metrics["difference_paise"])

    if direction == "STABLE":
        observation = (
            f"Your spending held roughly steady between the last two complete "
            f"{unit}s."
        )
    else:
        word = "rose" if direction == "INCREASED" else "fell"
        observation = f"Your spending {word} in the most recent complete {unit}."

    evidence = (
        f"{metrics['current_period']} totalled {money(current)} across "
        f"{metrics['current_expense_count']} expenses, against {money(previous)} in "
        f"{metrics['previous_period']} — a difference of {money(difference)}."
    )
    relative = metrics.get("relative_change")
    if relative is not None:
        evidence += f" That is a change of {percent(relative)}."

    interpretation = (
        f"Only complete {unit}s are compared, so this is not an artefact of where "
        f"the analysis window happens to start. Moves smaller than "
        f"{percent(metrics['stable_band'], 0)} are reported as steady."
    )
    return observation, evidence, interpretation, None


def _daily_trend(metrics: Mapping[str, Any], insight: Insight) -> Sections:
    direction = metrics["direction"]
    verb = {
        "INCREASED": "higher in the second half",
        "DECREASED": "lower in the second half",
        "STABLE": "roughly even across both halves",
    }[direction]

    evidence = (
        f"The first half of the window totalled "
        f"{money(metrics['first_half_paise'])} and the second half "
        f"{money(metrics['second_half_paise'])}. Your heaviest single day was "
        f"{metrics['busiest_day']} at {money(metrics['busiest_day_paise'])}."
    )
    interpretation = (
        f"You had {metrics['zero_spend_days']} days with no spending at all out of "
        f"{metrics['window_days']}."
    )
    return (
        f"Day-to-day spending was {verb} of the window.",
        evidence,
        interpretation,
        None,
    )


def _budget(metrics: Mapping[str, Any], insight: Insight) -> Sections:
    status = metrics["status"]
    spent = metrics["spent_paise"]
    budget = metrics["budget_paise"]
    remaining = metrics["remaining_paise"]

    # Note the absence of `days_in_month - days_elapsed`. A remaining-days
    # figure would be a number this renderer computed rather than read, which
    # is exactly what the model is forbidden from doing — and the validator
    # suite in test_templates holds templates to the same rule. Both operands
    # are stated instead, and the reader can do the subtraction.
    elapsed = f"{metrics['days_elapsed']} days into a {metrics['days_in_month']}-day month"

    if status == "OVER_BUDGET":
        observation = f"You are over your monthly budget for {metrics['month']}."
        interpretation = f"You are {money(abs(remaining))} past the budget, {elapsed}."
        suggestion = (
            "You may want to look at your largest category before the month closes."
        )
    elif status == "NEAR_LIMIT":
        observation = f"You are close to your monthly budget for {metrics['month']}."
        interpretation = f"{money(remaining)} remains, {elapsed}."
        suggestion = "Slowing discretionary spending for the rest of the month could help."
    else:
        observation = f"You are within your monthly budget for {metrics['month']}."
        interpretation = f"{money(remaining)} remains, {elapsed}."
        suggestion = None

    evidence = (
        f"You have spent {money(spent)} of {money(budget)} — "
        f"{percent(metrics['utilization_ratio'])} — after {metrics['days_elapsed']} "
        f"of {metrics['days_in_month']} days."
    )
    if not metrics.get("covers_full_month_to_date", True):
        evidence += (
            " The analysis window starts mid-month, so this counts only the covered part."
        )
    return observation, evidence, interpretation, suggestion


def _habit_completion(metrics: Mapping[str, Any], insight: Insight) -> Sections:
    logged = metrics["logged_days"]
    days = metrics["window_days"]

    if logged == 0:
        return (
            f"You have not logged any check-ins in the last {days} days.",
            f"All {days} days in the window are unrecorded.",
            "Behavioural analysis needs habit data to work with. Without check-ins "
            "the engine can describe your spending but cannot relate it to anything.",
            "Logging a few habits each day may unlock the behavioural analysis.",
        )

    sparse = [
        row for row in metrics["per_habit"] if row["coverage_ratio"] < 0.6
    ]
    observation = (
        f"You logged a check-in on {logged} of {days} days — "
        f"{percent(metrics['completion_ratio'])} of the window."
    )
    evidence = (
        f"Averaged across the six habits, coverage is "
        f"{percent(metrics['average_habit_coverage_ratio'])}. Coverage is counted per "
        "habit: a check-in that records only sleep provides none for exercise."
    )
    if sparse:
        names = ", ".join(habit_label(row["habit"]) for row in sparse[:3])
        # No count and no threshold figure: both would be numbers this renderer
        # produced rather than read from the insight, which is the rule the
        # model is held to and `test_templates` holds these to as well.
        interpretation = (
            f"Some habits are logged too rarely for behavioural analysis to use them, "
            f"including {names}. Coverage is judged per habit, so a well-logged habit "
            "does not compensate for a sparse one."
        )
        suggestion = f"Logging {names} more consistently could bring them into range."
    else:
        interpretation = "Every habit is logged often enough for behavioural analysis."
        suggestion = None
    return observation, evidence, interpretation, suggestion


def _habit_streak(metrics: Mapping[str, Any], insight: Insight) -> Sections:
    current = metrics["current_logging_streak"]
    longest = metrics["longest_logging_streak"]

    if metrics["streak_is_live"]:
        observation = f"You are on a {current}-day check-in streak."
    elif metrics["last_logged_date"]:
        observation = (
            f"Your check-in streak has lapsed — the last one was "
            f"{metrics['last_logged_date']}."
        )
    else:
        observation = "You have no check-in streak in this window."

    evidence = (
        f"Your longest run of consecutive check-ins was {longest} days. Your longest "
        f"run of consecutive exercise days was {metrics['longest_exercise_streak']}."
    )
    interpretation = (
        f"A day with no exercise recorded ends an exercise streak rather than "
        f"extending it — {metrics['unknown_exercise_days']} days in this window have "
        "no exercise value at all, so the streak figures are conservative."
    )
    return observation, evidence, interpretation, None


def _sleep(metrics: Mapping[str, Any], insight: Insight) -> Sections:
    return (
        f"You slept {metrics['mean_hours']} hours a night on average.",
        f"That is across {metrics['observations_included']} nights you recorded, "
        f"ranging from {metrics['min_hours']} to {metrics['max_hours']} hours, with a "
        f"median of {metrics['median_hours']}.",
        f"{metrics['observations_excluded_unknown']} days in the window have no sleep "
        "recorded and are excluded rather than assumed — the average describes the "
        "nights you logged, not every night.",
        None,
    )


def _exercise(metrics: Mapping[str, Any], insight: Insight) -> Sections:
    return (
        f"You exercised on {metrics['exercised_days']} of the "
        f"{metrics['recorded_days']} days you recorded.",
        f"That is {percent(metrics['frequency_ratio'])} of recorded days, or about "
        f"{metrics['sessions_per_week']} sessions a week.",
        f"The denominator is days you actually answered, not days in the window. "
        f"{metrics['observations_excluded_unknown']} days have no exercise value and "
        "are excluded — counting them as rest days would understate your rate.",
        None,
    )


def _missed(metrics: Mapping[str, Any], insight: Insight) -> Sections:
    missed = metrics["missed_days"]

    if missed == 0:
        return (
            "You logged a check-in every day in this window.",
            f"All {metrics['window_days']} days are recorded.",
            "Full coverage means the behavioural analysis has the most data it can "
            "use from this period.",
            None,
        )

    observation = (
        f"You missed {missed} of {metrics['window_days']} days of check-ins."
    )
    evidence = (
        f"That is {percent(metrics['missed_ratio'])} of the window, with the longest "
        f"unbroken gap running {metrics['longest_gap_days']} days."
    )
    interpretation = (
        "A missed day is not a day nothing happened — it is a day with no "
        "information, and it is excluded from every habit figure rather than "
        "counted as a zero."
    )
    return observation, evidence, interpretation, None


def _event_summary(metrics: Mapping[str, Any], insight: Insight) -> Sections:
    title = metrics["title"]
    total = metrics["total_paise"]

    observation = f"You spent {money(total)} during {title}."
    evidence = (
        f"That is {metrics['expense_count']} expenses over "
        f"{metrics['event_days_in_window']} days, averaging "
        f"{money(metrics['average_per_day_paise'])} a day."
    )
    if metrics.get("top_category"):
        evidence += f" The largest category was {category_label(metrics['top_category'])}."

    interpretation = (
        f"This covers the days you marked as {title.lower()} within the analysis "
        "window. Whether that is high or low is for you to judge — the engine only "
        "reports the split."
    )
    return observation, evidence, interpretation, None


def _event_impact(metrics: Mapping[str, Any], insight: Insight) -> Sections:
    direction = metrics["direction"]
    during = metrics["during_daily_paise"]
    outside = metrics["outside_daily_paise"]

    word = {"HIGHER": "higher", "LOWER": "lower", "EQUAL": "the same"}[direction]
    observation = f"Your daily spending during life events was {word} than on ordinary days."
    evidence = (
        f"{money(during)} a day across {metrics['event_days']} event days, against "
        f"{money(outside)} a day across {metrics['ordinary_days']} ordinary days."
    )
    relative = metrics.get("relative_difference")
    if relative is not None:
        evidence += f" That is a difference of {percent(relative)}."

    interpretation = (
        "This is a per-day comparison, not a statistical test — a short event will "
        "always total less than the rest of the window, so totals would mislead. No "
        "significance is claimed."
    )
    return observation, evidence, interpretation, None


def _relationship(metrics: Mapping[str, Any], insight: Insight) -> Sections:
    raw_habit = str(metrics["habit"])
    habit = habit_label(raw_habit)
    category = category_label(metrics["category"])
    group_a = metrics["group_a"]
    group_b = metrics["group_b"]
    higher = group_b if metrics["higher_group"] == "group_b" else group_a
    lower = group_a if metrics["higher_group"] == "group_b" else group_b
    observations = metrics["observations"]

    def phrase(group: Mapping[str, Any]) -> str:
        """The engine's group label, with the column name read out loud.

        The engine builds these from the habit's column name — "weeks with
        higher sleep_minutes" — which is correct as a machine key and wrong
        in a sentence a person reads. Substituting here rather than in the
        engine keeps the naming a presentation concern.
        """
        return str(group["label"]).replace(raw_habit, habit)

    observation = f"{category} spending was higher in weeks {phrase(higher).split('weeks ', 1)[-1]}."
    evidence = (
        f"{phrase(higher).capitalize()}: {money(higher['median_paise'])} a week across "
        f"{higher['n']} weeks. {phrase(lower).capitalize()}: "
        f"{money(lower['median_paise'])} across {lower['n']} weeks. The gap is "
        f"{money(abs(metrics['difference_paise']))} a week, or "
        f"{percent(metrics['relative_difference'])}."
    )
    interpretation = (
        f"This is an association between {habit} and {category} spending, not a cause "
        f"— the data does not show which came first. "
        f"{observations['excluded_unknown']} weeks were excluded for having no "
        f"{habit} recorded, leaving {observations['included']} weeks of coverage."
    )
    suggestion = (
        f"You may find it worth watching {category} spending in weeks where your "
        f"{habit} pattern changes."
    )
    return observation, evidence, interpretation, suggestion


def _sufficiency(metrics: Mapping[str, Any], insight: Insight) -> Sections:
    gate = metrics["failed_gate"]
    reason = GATE_LABELS.get(gate, "a requirement was not met")
    subject = metrics.get("subject")

    if gate == "G1_HISTORY":
        observation = "There is not yet enough history for behavioural analysis."
        evidence = (
            f"The window holds {metrics['current_value']} complete weeks; "
            f"{metrics['required_value']} are required before any habit-and-spending "
            "association is tested."
        )
        suggestion = "A few more weeks of records could unlock this analysis."
    else:
        label = habit_label(subject)
        observation = f"No reliable conclusion can be drawn about {label} yet."
        evidence = (
            f"{label.capitalize()} was recorded in "
            f"{percent(float(metrics['current_value']))} of the weeks analysed, below "
            f"the {percent(float(metrics['required_value']), 0)} needed to test it."
        )
        suggestion = f"Logging {label} more consistently may bring it into range."

    interpretation = (
        f"The analysis was stopped here because {reason}. Nothing is being hidden — "
        "there simply is not enough recorded data to support a claim, and reporting a "
        "weak one would be worse than reporting none."
    )
    return observation, evidence, interpretation, suggestion


TEMPLATES: dict[InsightType, Callable[[Mapping[str, Any], Insight], Sections]] = {
    InsightType.SPENDING_TOTAL: _spending_total,
    InsightType.SPENDING_BY_CATEGORY: _spending_by_category,
    InsightType.SPENDING_MONTHLY_COMPARISON: _period_comparison,
    InsightType.SPENDING_WEEKLY_COMPARISON: _period_comparison,
    InsightType.SPENDING_DAILY_TREND: _daily_trend,
    InsightType.BUDGET_UTILIZATION: _budget,
    InsightType.HABIT_COMPLETION: _habit_completion,
    InsightType.HABIT_STREAK: _habit_streak,
    InsightType.HABIT_SLEEP_AVERAGE: _sleep,
    InsightType.HABIT_EXERCISE_FREQUENCY: _exercise,
    InsightType.HABIT_MISSED_DAYS: _missed,
    InsightType.EVENT_SUMMARY: _event_summary,
    InsightType.EVENT_IMPACT: _event_impact,
    InsightType.BEHAVIOR_RELATIONSHIP: _relationship,
    InsightType.DATA_SUFFICIENCY: _sufficiency,
}


def render(insight: Insight) -> Sections:
    """Render one insight deterministically.

    A missing template is a programming error, not a runtime condition — every
    ``InsightType`` is covered and a test enforces it.
    """
    try:
        template = TEMPLATES[insight.type]
    except KeyError as exc:  # pragma: no cover - guarded by test_templates
        raise KeyError(
            f"No narration template for {insight.type.value}. Every InsightType "
            "must be renderable without a model."
        ) from exc
    return template(insight.metrics, insight)
