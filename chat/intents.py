r"""Intent → capability map.

Deterministic pattern matching, not a model and not embeddings. Three reasons
it stays that way:

* **It is the refusal mechanism.** A question that matches nothing is one the
  analysis engine has no output for, and the honest answer is to say so. An
  embedding-based matcher always returns a nearest neighbour, so "no capability
  covers this" stops being expressible.
* **It is testable.** Every routing decision in ``test_intents`` is an
  assertion about a rule, not about a model's mood.
* **It runs in microseconds**, which matters because it decides what the
  expensive step is even allowed to see.

Each intent names the ``InsightType``s that can answer it. That mapping *is*
the capability list — an intent with no insight types is a question the system
should not have claimed to support.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from app.analysis.models import InsightType


class Intent(str, Enum):
    """What the user is asking for."""

    SPENDING_SUMMARY = "SPENDING_SUMMARY"
    BIGGEST_EXPENSES = "BIGGEST_EXPENSES"
    CATEGORY_BREAKDOWN = "CATEGORY_BREAKDOWN"
    PERIOD_COMPARISON = "PERIOD_COMPARISON"
    BUDGET_STATUS = "BUDGET_STATUS"
    HABIT_SUMMARY = "HABIT_SUMMARY"
    HABIT_RELATIONSHIP = "HABIT_RELATIONSHIP"
    EVENT_CONTEXT = "EVENT_CONTEXT"
    IMPROVEMENT = "IMPROVEMENT"
    OVERVIEW = "OVERVIEW"


#: Which engine outputs can answer each intent. The context builder sends
#: these and nothing else.
CAPABILITIES: dict[Intent, tuple[InsightType, ...]] = {
    Intent.SPENDING_SUMMARY: (
        InsightType.SPENDING_TOTAL,
        InsightType.SPENDING_DAILY_TREND,
    ),
    Intent.BIGGEST_EXPENSES: (
        InsightType.SPENDING_TOTAL,
        InsightType.SPENDING_BY_CATEGORY,
    ),
    Intent.CATEGORY_BREAKDOWN: (
        InsightType.SPENDING_BY_CATEGORY,
        InsightType.SPENDING_TOTAL,
    ),
    Intent.PERIOD_COMPARISON: (
        InsightType.SPENDING_MONTHLY_COMPARISON,
        InsightType.SPENDING_WEEKLY_COMPARISON,
        InsightType.SPENDING_BY_CATEGORY,
    ),
    Intent.BUDGET_STATUS: (
        InsightType.BUDGET_UTILIZATION,
        InsightType.SPENDING_TOTAL,
        InsightType.SPENDING_BY_CATEGORY,
    ),
    Intent.HABIT_SUMMARY: (
        InsightType.HABIT_COMPLETION,
        InsightType.HABIT_STREAK,
        InsightType.HABIT_EXERCISE_FREQUENCY,
        InsightType.HABIT_SLEEP_AVERAGE,
        InsightType.HABIT_MISSED_DAYS,
    ),
    Intent.HABIT_RELATIONSHIP: (
        InsightType.BEHAVIOR_RELATIONSHIP,
        InsightType.DATA_SUFFICIENCY,
        InsightType.HABIT_COMPLETION,
    ),
    Intent.EVENT_CONTEXT: (
        InsightType.EVENT_SUMMARY,
        InsightType.EVENT_IMPACT,
    ),
    Intent.IMPROVEMENT: (
        InsightType.BUDGET_UTILIZATION,
        InsightType.SPENDING_BY_CATEGORY,
        InsightType.BEHAVIOR_RELATIONSHIP,
        InsightType.DATA_SUFFICIENCY,
    ),
    Intent.OVERVIEW: (
        InsightType.SPENDING_TOTAL,
        InsightType.SPENDING_BY_CATEGORY,
        InsightType.BUDGET_UTILIZATION,
        InsightType.HABIT_COMPLETION,
    ),
}


@dataclass(frozen=True, slots=True)
class IntentMatch:
    intent: Intent | None
    #: The rule that fired, for tests and debugging.
    matched: str = ""

    @property
    def is_supported(self) -> bool:
        return self.intent is not None


#: Ordered rules. The first match wins, so the more specific patterns come
#: first — "how has the gym affected my spending" is a relationship question,
#: not a habit summary, even though it names a habit.
_RULES: tuple[tuple[Intent, re.Pattern[str]], ...] = (
    (
        Intent.HABIT_RELATIONSHIP,
        re.compile(
            r"\b(affect|affected|impact|influence|correlat|relationship|linked|"
            r"connect(ed|ion)?|tied to|to do with)\b",
            re.IGNORECASE,
        ),
    ),
    (
        Intent.HABIT_RELATIONSHIP,
        re.compile(r"\b(strongest|biggest|most) .{0,24}(impact|effect|influence)\b", re.IGNORECASE),
    ),
    (
        Intent.EVENT_CONTEXT,
        re.compile(
            r"\b(during|around|while i was|what happened)\b.{0,40}"
            r"\b(week|trip|travel|holiday|vacation|exam|illness|ill|sick|flu|"
            r"festival|diwali|wedding|relocat|moving|event)\b",
            re.IGNORECASE,
        ),
    ),
    (
        Intent.EVENT_CONTEXT,
        re.compile(r"\b(life )?event(s)?\b|\bexam week\b|\bgoa trip\b", re.IGNORECASE),
    ),
    (
        Intent.BUDGET_STATUS,
        re.compile(
            r"\b(budget|overspend\w*|overspent|over ?spend\w*|over ?spent|"
            r"over my limit|blown)\b",
            re.IGNORECASE,
        ),
    ),
    (
        Intent.PERIOD_COMPARISON,
        re.compile(
            r"\b(compare|comparison|versus|vs\.?|last month|previous month|"
            r"last week|previous week|month[- ]on[- ]month|increased the most|"
            r"decreased the most|gone up|gone down|more than last)\b",
            re.IGNORECASE,
        ),
    ),
    (
        Intent.IMPROVEMENT,
        re.compile(
            r"\b(improve|do better|cut back|reduce|save more|fix|work on|"
            r"what should i (do|change|focus))\b",
            re.IGNORECASE,
        ),
    ),
    (
        Intent.BIGGEST_EXPENSES,
        re.compile(
            r"\b(biggest|largest|highest|top|most expensive) ?.{0,20}?"
            r"(expenses?|spend(ing)?|purchases?|transactions?|costs?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        Intent.CATEGORY_BREAKDOWN,
        re.compile(
            r"\b(categor\w*|breakdown|what did i spend .{0,20}on|"
            r"where .{0,20}(money|spending) go|spend (the )?most on)\b",
            re.IGNORECASE,
        ),
    ),
    (
        Intent.HABIT_SUMMARY,
        re.compile(
            r"\b(habit|gym|exercise|workout|sleep|sleeping|streak|check[- ]?in|"
            r"alcohol|stress|home[- ]cooked|work mode)\b",
            re.IGNORECASE,
        ),
    ),
    (
        Intent.SPENDING_SUMMARY,
        re.compile(
            r"\b(how much|total|spent|spending|expenses?|trend|daily|outflow)\b",
            re.IGNORECASE,
        ),
    ),
    (
        Intent.OVERVIEW,
        re.compile(
            r"\b(overview|summary|summar(y|ise|ize)|how am i doing|how's it going|"
            r"how is it going|tell me about my (money|finances))\b",
            re.IGNORECASE,
        ),
    ),
)


def detect_intent(question: str) -> IntentMatch:
    """Route a question to a capability, or to nothing.

    Returning ``None`` is a first-class outcome, not a failure: it is how the
    system says "the analysis engine has no output that answers this", which
    is the only honest response to a question it cannot ground.
    """
    text = question.strip()
    if len(text) < 3:
        return IntentMatch(None, "too short")

    for intent, pattern in _RULES:
        match = pattern.search(text)
        if match:
            return IntentMatch(intent, match.group(0).lower())

    return IntentMatch(None, "no rule matched")


def capability_for(intent: Intent) -> tuple[InsightType, ...]:
    return CAPABILITIES[intent]


#: Shown when nothing matched, so a refusal teaches rather than just declines.
SUPPORTED_EXAMPLES: tuple[str, ...] = (
    "How much did I spend this month?",
    "Which category did I spend the most on?",
    "Compare this month with last month.",
    "Am I over budget?",
    "How has my gym routine affected my spending?",
    "What happened during my trip?",
    "What should I improve?",
)
