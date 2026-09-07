"""Insight schemas.

Thin by design. The engine already produces JSON-safe structures — enforced by
``_assert_json_safe`` in ``analysis/models.py`` — so these models describe the
shape rather than transform it. A schema that reshaped insights would be a
second place where the response format is decided, which is exactly what
defining ``Insight`` once was meant to prevent.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.analysis.engine import AnalysisResult
from app.analysis.models import Evidence, Insight


class EvidenceRead(BaseModel):
    """A pointer to something the user can open and check."""

    kind: str
    label: str
    ref_id: str | None
    payload: dict[str, Any]

    @classmethod
    def from_domain(cls, evidence: Evidence) -> "EvidenceRead":
        return cls(**evidence.as_dict())


class WindowRead(BaseModel):
    start: str
    end: str
    days: int


class InsightRead(BaseModel):
    """A finished conclusion.

    ``title_key`` is a stable renderer key, never prose — the engine does not
    write natural language. ``confidence`` is present only on T3 insights; a
    sum is not uncertain.
    """

    id: str
    type: str
    tier: str
    title_key: str
    subject: str | None
    window: WindowRead
    metrics: dict[str, Any]
    evidence: list[EvidenceRead]
    confidence: float | None
    created_at: str

    @classmethod
    def from_domain(cls, insight: Insight) -> "InsightRead":
        return cls(**insight.as_dict())


class AnalysisRunRead(BaseModel):
    """Metadata for one pass: window, engine version, gates, hypothesis count."""

    engine_version: str
    generated_at: str
    window: WindowRead
    gates: dict[str, Any]
    hypotheses_tested: int
    relationships_emitted: int
    relationships_suppressed: int
    insight_count: int
    notice_count: int
    inputs: dict[str, int]
    currency: str


class AnalysisResultRead(BaseModel):
    """The full response.

    ``notices`` is not an error channel. It carries Data Sufficiency notices —
    what the engine declined to claim and what would unlock it. A new user
    with three days of data gets an empty ``insights`` list and a notice
    saying so, which is the designed behaviour rather than a failure
    (PDR-030).
    """

    run: AnalysisRunRead
    insights: list[InsightRead] = Field(default_factory=list)
    notices: list[InsightRead] = Field(default_factory=list)

    @classmethod
    def from_domain(cls, result: AnalysisResult) -> "AnalysisResultRead":
        return cls(**result.as_dict())
