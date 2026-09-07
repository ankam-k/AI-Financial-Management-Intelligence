"""The narration object.

Five sections, as specified: Observation, Evidence, Interpretation,
Confidence, Suggestion.

**Confidence is rendered by code, not written by the model.** The model
authors the other four sections; the confidence sentence is derived
deterministically from the insight's tier and q-value. That is the one place
where letting the model write would put a fabricated number in the most
load-bearing sentence on the page — and "do not fabricate confidence values"
is better enforced by never asking than by checking afterwards.

Every narration also reports where it came from and, when the model's output
was discarded, exactly which validator rejected it. A client that cannot tell
generated prose from a template cannot show the difference to a user.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class NarrationSource(str, Enum):
    """Who wrote the prose."""

    #: A model generated it and it passed every validator.
    LLM = "LLM"
    #: Rendered deterministically from the insight. The default, and the
    #: fallback whenever generation is unavailable or rejected.
    TEMPLATE = "TEMPLATE"


@dataclass(frozen=True, slots=True)
class ValidationFailure:
    """Why a generation was discarded."""

    #: Machine name of the validator: ``provenance``, ``lexical``, ``advice_guard``.
    validator: str
    detail: str

    def as_dict(self) -> dict[str, str]:
        return {"validator": self.validator, "detail": self.detail}


@dataclass(frozen=True, slots=True)
class Narration:
    """A rendered explanation of exactly one :class:`Insight`."""

    insight_id: str
    insight_type: str
    tier: str

    observation: str
    evidence: str
    interpretation: str
    #: A rendered sentence, always present. Never model-authored.
    confidence: str
    #: The underlying figure, or ``None`` for T1/T2 where none exists.
    confidence_value: float | None
    suggestion: str | None

    source: NarrationSource
    #: ``provider:model`` when generated, ``None`` for templates.
    model: str | None = None
    #: Populated when a generation was produced and then rejected.
    validation_failures: tuple[ValidationFailure, ...] = ()
    #: Why this is a template: unavailability, timeout, or validation.
    fallback_reason: str | None = None

    def __post_init__(self) -> None:
        for name in ("observation", "evidence", "interpretation", "confidence"):
            if not getattr(self, name).strip():
                raise ValueError(f"narration section '{name}' cannot be empty")
        if self.source is NarrationSource.LLM and self.validation_failures:
            raise ValueError(
                "a narration cannot be sourced from the model and also carry "
                "validation failures — failure discards, it never repairs"
            )

    def as_dict(self) -> dict[str, Any]:
        return {
            "insight_id": self.insight_id,
            "insight_type": self.insight_type,
            "tier": self.tier,
            "observation": self.observation,
            "evidence": self.evidence,
            "interpretation": self.interpretation,
            "confidence": self.confidence,
            "confidence_value": self.confidence_value,
            "suggestion": self.suggestion,
            "source": self.source.value,
            "model": self.model,
            "validation_failures": [f.as_dict() for f in self.validation_failures],
            "fallback_reason": self.fallback_reason,
        }


@dataclass(frozen=True, slots=True)
class NarrationRun:
    """One narration pass over an analysis result."""

    narrations: tuple[Narration, ...] = ()
    stats: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "stats": dict(self.stats),
            "narrations": [n.as_dict() for n in self.narrations],
        }
