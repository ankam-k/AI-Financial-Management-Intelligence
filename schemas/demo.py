"""Demo-mode schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.demo.loader import DemoStatus


class DemoStatusRead(BaseModel):
    """What is currently loaded, and whether seeding is permitted."""

    enabled: bool
    profile: str | None
    expenses: int
    check_ins: int
    events: int
    monthly_budget_paise: int | None
    earliest: str | None
    latest: str | None
    is_empty: bool

    @classmethod
    def from_domain(cls, status: DemoStatus, *, enabled: bool) -> "DemoStatusRead":
        return cls(enabled=enabled, **status.as_dict())


class DemoDesignRead(BaseModel):
    """The declared design, so the demo can be checked rather than trusted."""

    seed: int
    days: int
    planted_patterns: list[dict[str, Any]] = Field(default_factory=list)
    negative_controls: list[str] = Field(default_factory=list)
    note: str = (
        "Patterns are planted deliberately and asserted by tests that run the "
        "real analysis engine. The negative controls are generated "
        "independently of every category and must produce no findings at all."
    )
