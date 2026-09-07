"""Deterministic answers, assembled from prose that already exists.

Not a stub. This runs whenever no model is configured, whenever one times out,
and whenever a generation is rejected — and it is what makes the assistant
usable with the model switched off, as everything else in this product is.

It writes almost nothing new. Sprint 3 already produced a validated
observation, evidence and interpretation for every insight; these functions
select and join them. Prose that has already passed the provenance, lexical
and advice validators cannot fail them by being quoted.
"""

from __future__ import annotations

from app.chat.context import ChatContext
from app.chat.intents import Intent

_LEAD: dict[Intent, str] = {
    Intent.SPENDING_SUMMARY: "Here is what your spending looks like over this window.",
    Intent.BIGGEST_EXPENSES: "Here is where the largest amounts went.",
    Intent.CATEGORY_BREAKDOWN: "Here is how your spending splits by category.",
    Intent.PERIOD_COMPARISON: "Here is how the last two complete periods compare.",
    Intent.BUDGET_STATUS: "Here is where you stand against your budget.",
    Intent.HABIT_SUMMARY: "Here is what your habit logging looks like.",
    Intent.HABIT_RELATIONSHIP: "Here is what the analysis found about your habits and spending.",
    Intent.EVENT_CONTEXT: "Here is what happened around the events you recorded.",
    Intent.IMPROVEMENT: "Here is what stands out as worth your attention.",
    Intent.OVERVIEW: "Here is the short version.",
}

#: Shown when the intent matched but the window holds nothing to answer from.
EMPTY_CONTEXT_TEXT = (
    "I don't have enough recorded data in this window to answer that. "
    "The analysis needs expenses, daily check-ins or life events to work "
    "from, and there aren't any here yet.\n\n"
    "Adding a few will let me answer — nothing is estimated in the meantime."
)


def render(question: str, context: ChatContext) -> str:
    """Build an answer from the selected insights' existing narrations."""
    if context.is_empty:
        return EMPTY_CONTEXT_TEXT

    parts: list[str] = [_LEAD.get(context.intent, "Here is what the analysis shows.")]

    for insight in context.insights:
        narration = context.narrations.get(insight.id)
        if narration is None:
            continue
        line = f"- **{narration.observation}** {narration.evidence}"
        if insight.tier.value == "T3":
            # The correlational caveat travels with the claim, never separately.
            line = f"{line} {narration.interpretation}"
        parts.append(line)

    if len(parts) == 1:
        # Selected insights, but none of them had narration attached.
        return (
            "I found relevant analysis for that, but no written explanation is "
            "attached to it in this run. The dashboard shows the same figures."
        )

    if context.intent is Intent.IMPROVEMENT:
        parts.append(
            "I can only point at what the analysis already found — I won't "
            "invent a plan beyond it."
        )

    return "\n".join(parts)
