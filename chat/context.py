"""The context builder: minimum necessary, and nothing else.

The model receives the insights the matched intent can be answered from, and
their existing narrations. Not the ledger, not the window's other twelve
insights, not the database.

"Minimum necessary" is a correctness property here, not a token-cost
optimisation. Every number in the context becomes a number the answer is
*allowed* to contain, because the provenance validator builds its permitted
set from exactly this payload. A context that ships the whole run would
license the model to quote any figure from any insight — including ones
irrelevant to the question, where a plausible-looking mix-up would pass every
check.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.analysis.engine import AnalysisResult
from app.analysis.models import Insight, InsightType
from app.chat.intents import Intent, capability_for
from app.narration.models import Narration
from app.narration.payload import allowed_numbers, build_payload

#: Per-insight cap. A category breakdown plus its narration is already a
#: substantial prompt; six is generous for every intent in the map.
MAX_INSIGHTS = 6

#: Data-sufficiency notices are one per habit and all read the same — "X was
#: recorded in 33% of weeks, below the 60% needed". Six of them is the same
#: sentence six times, which buries the point rather than making it. Two is
#: enough to establish that coverage is the blocker.
MAX_NOTICES = 2


@dataclass(frozen=True, slots=True)
class ChatContext:
    """Everything the model is allowed to see for one question."""

    intent: Intent
    window: dict[str, Any]
    currency: str
    #: The insights selected for this intent, in capability order.
    insights: tuple[Insight, ...] = ()
    #: Their existing narrations, keyed by insight id. Reused, not regenerated
    #: — Sprint 3 already wrote and validated this prose.
    narrations: dict[str, Narration] = field(default_factory=dict)

    @property
    def is_empty(self) -> bool:
        return not self.insights

    def payloads(self) -> list[dict[str, Any]]:
        """The insight payloads, as the narration layer builds them."""
        return [build_payload(insight) for insight in self.insights]

    def allowed_numbers(self) -> frozenset[str]:
        """Every numeric literal the answer may contain.

        Union across the selected insights only. An insight left out of the
        context contributes nothing here, which is what makes the selection a
        control rather than a convenience.
        """
        permitted: set[str] = set()
        for payload in self.payloads():
            permitted |= allowed_numbers(payload)
        for value in self.window.values():
            permitted |= allowed_numbers({"window": value})
        return frozenset(permitted)

    def as_model_input(self) -> dict[str, Any]:
        """The JSON handed to the model."""
        return {
            "question_topic": self.intent.value,
            "window": self.window,
            "currency": self.currency,
            "findings": [
                {
                    "insight_type": insight.type.value,
                    "tier": insight.tier.value,
                    "subject": insight.subject,
                    "metrics": payload["metrics"],
                    "existing_explanation": _explanation(self.narrations.get(insight.id)),
                }
                for insight, payload in zip(self.insights, self.payloads())
            ],
        }

    def summary(self) -> dict[str, Any]:
        """Audit record: what was sent, without sending it again."""
        return {
            "intent": self.intent.value,
            "insight_count": len(self.insights),
            "insight_types": [insight.type.value for insight in self.insights],
            "tiers": sorted({insight.tier.value for insight in self.insights}),
            "narrations_included": len(self.narrations),
            "allowed_number_count": len(self.allowed_numbers()),
        }

    @property
    def has_correlational_finding(self) -> bool:
        """True when any selected insight is an inference rather than a sum.

        Decides whether the answer is held to correlational language.
        """
        return any(insight.tier.value == "T3" for insight in self.insights)


def _explanation(narration: Narration | None) -> dict[str, str] | None:
    if narration is None:
        return None
    return {
        "observation": narration.observation,
        "evidence": narration.evidence,
        "interpretation": narration.interpretation,
        "confidence": narration.confidence,
    }


def build_context(
    intent: Intent,
    analysis: AnalysisResult,
    narrations: dict[str, Narration],
) -> ChatContext:
    """Select the finished outputs that answer this intent.

    Notices are searched alongside insights: for a relationship question with
    no finding, the Data Sufficiency notice *is* the answer, and leaving it out
    would turn "here is why I can't tell you" into silence.
    """
    wanted: tuple[InsightType, ...] = capability_for(intent)
    available = list(analysis.insights) + list(analysis.notices)

    selected: list[Insight] = []
    for insight_type in wanted:
        limit = MAX_NOTICES if insight_type is InsightType.DATA_SUFFICIENCY else MAX_INSIGHTS
        taken = 0
        for insight in available:
            if insight.type is insight_type and insight not in selected:
                selected.append(insight)
                taken += 1
                if taken >= limit or len(selected) >= MAX_INSIGHTS:
                    break
        if len(selected) >= MAX_INSIGHTS:
            break

    return ChatContext(
        intent=intent,
        window=dict(analysis.run["window"]),
        currency=str(analysis.run.get("currency", "INR")),
        insights=tuple(selected),
        narrations={
            insight.id: narrations[insight.id]
            for insight in selected
            if insight.id in narrations
        },
    )
