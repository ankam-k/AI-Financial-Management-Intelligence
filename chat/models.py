"""What a chat turn produces.

An answer is a value object, not a message in a thread. It carries what was
asked, what was used to answer it, where the words came from, and — when the
generated version was thrown away — which validator rejected it.

There is deliberately no ``Conversation`` type. Adding one would create the
state that SRS-7.7 forbids, and the absence of a mechanism is what makes
single-turn true rather than merely intended.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.narration.models import NarrationSource, ValidationFailure


class AnswerStatus(str, Enum):
    """What happened to the question."""

    ANSWERED = "ANSWERED"
    REFUSED = "REFUSED"


class RefusalReason(str, Enum):
    """Why a question was not answered.

    Distinct reasons because they mean different things to a user: one is a
    boundary the product will never cross, the others are gaps that more data
    or a clearer question would close.
    """

    #: Directing future capital allocation. Never crossed (PDR-027, ADR-010).
    PROHIBITED_TOPIC = "PROHIBITED_TOPIC"
    #: A real question the analysis engine has no output for.
    NOT_ANSWERABLE_FROM_ANALYSIS = "NOT_ANSWERABLE_FROM_ANALYSIS"
    #: The intent matched, but the window holds nothing to answer from.
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    #: Not a question this system can parse at all.
    UNCLEAR = "UNCLEAR"


@dataclass(frozen=True, slots=True)
class Citation:
    """An insight the answer drew on, so a claim can be opened and checked."""

    insight_id: str
    insight_type: str
    tier: str

    def as_dict(self) -> dict[str, str]:
        return {
            "insight_id": self.insight_id,
            "insight_type": self.insight_type,
            "tier": self.tier,
        }


@dataclass(frozen=True, slots=True)
class ChatAnswer:
    """One question, answered or refused."""

    question: str
    status: AnswerStatus
    answer: str
    intent: str | None = None
    refusal_reason: RefusalReason | None = None
    source: NarrationSource = NarrationSource.TEMPLATE
    model: str | None = None
    citations: tuple[Citation, ...] = ()
    validation_failures: tuple[ValidationFailure, ...] = ()
    fallback_reason: str | None = None
    #: What the context builder actually sent, for auditing prompt size.
    context_summary: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.answer.strip():
            raise ValueError("an answer cannot be empty")
        if self.status is AnswerStatus.REFUSED and self.refusal_reason is None:
            raise ValueError("a refusal must state its reason")
        if self.status is AnswerStatus.ANSWERED and self.refusal_reason is not None:
            raise ValueError("an answered question carries no refusal reason")
        if self.source is NarrationSource.LLM and self.validation_failures:
            raise ValueError(
                "an answer cannot be model-written and also carry validation "
                "failures — failure discards, it never repairs"
            )

    def as_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "status": self.status.value,
            "answer": self.answer,
            "intent": self.intent,
            "refusal_reason": self.refusal_reason.value if self.refusal_reason else None,
            "source": self.source.value,
            "model": self.model,
            "citations": [item.as_dict() for item in self.citations],
            "validation_failures": [f.as_dict() for f in self.validation_failures],
            "fallback_reason": self.fallback_reason,
            "context_summary": dict(self.context_summary),
        }
