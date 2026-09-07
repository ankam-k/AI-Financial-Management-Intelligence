"""Narration schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.llm.base import LLMHealth
from app.narration.models import Narration
from app.schemas.insight import AnalysisRunRead
from app.services.narration_service import NarratedAnalysis


class ValidationFailureRead(BaseModel):
    """Why a generation was discarded. Surfaced rather than hidden — a client
    that cannot tell generated prose from a template cannot show the
    difference to a user."""

    validator: str
    detail: str


class NarrationRead(BaseModel):
    """One explanation, in five sections.

    ``confidence`` is a rendered sentence and ``confidence_value`` the figure
    behind it, present only for T3. Neither is ever authored by the model.
    """

    insight_id: str
    insight_type: str
    tier: str

    observation: str
    evidence: str
    interpretation: str
    confidence: str
    confidence_value: float | None
    suggestion: str | None

    source: str
    model: str | None
    validation_failures: list[ValidationFailureRead] = Field(default_factory=list)
    fallback_reason: str | None

    @classmethod
    def from_domain(cls, narration: Narration) -> "NarrationRead":
        return cls(**narration.as_dict())


class NarrationStatsRead(BaseModel):
    """How the prose in this response was produced."""

    total: int
    generated: int
    templated: int
    generation_attempted: int
    rejected_by_validation: int
    provider: str
    model: str


class NarratedAnalysisRead(BaseModel):
    """The full response: what was analysed, and what it means."""

    run: AnalysisRunRead
    narration: NarrationStatsRead
    narrations: list[NarrationRead] = Field(default_factory=list)

    @classmethod
    def from_domain(cls, narrated: NarratedAnalysis) -> "NarratedAnalysisRead":
        return cls(**narrated.as_dict())


class LLMStatusRead(BaseModel):
    """Whether a model is configured and reachable."""

    provider: str
    model: str
    available: bool
    detail: str
    #: What a request would produce right now.
    narration_mode: str

    @classmethod
    def from_domain(cls, health: LLMHealth) -> "LLMStatusRead":
        return cls(
            provider=health.provider,
            model=health.model,
            available=health.available,
            detail=health.detail,
            narration_mode="GENERATED" if health.available else "TEMPLATE",
        )


class PromptPreviewRead(BaseModel):
    """The exact prompt a given insight would produce.

    Exposed because "what did the model actually see?" should be answerable
    without attaching a debugger — and because the answer demonstrates that it
    sees a finished insight and nothing else.
    """

    insight_id: str
    insight_type: str
    tier: str
    system_prompt: str
    user_prompt: str
    output_schema: dict[str, Any]
    allowed_numbers: list[str]
