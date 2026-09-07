"""Runs the analysis engine, then narrates what it produced.

Composes two things that must not know about each other: ``AnalysisService``
loads and analyses, ``NarrationRenderer`` explains. Neither imports the other.

The order is fixed and one-directional. Narration reads a finished
``AnalysisResult`` and cannot ask for more data, which is the structural form
of "the AI must never read directly from the database" — there is no handle
here for it to read one through.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from app.analysis.engine import AnalysisResult
from app.analysis.models import Insight
from app.models.user import User
from app.narration.models import NarrationRun
from app.narration.renderer import NarrationRenderer
from app.services.analysis_service import AnalysisService


@dataclass(frozen=True, slots=True)
class NarratedAnalysis:
    """An analysis run plus an explanation of every insight in it."""

    analysis: AnalysisResult
    narration: NarrationRun

    def as_dict(self) -> dict[str, Any]:
        return {
            "run": self.analysis.run,
            "narration": self.narration.stats,
            "narrations": [item.as_dict() for item in self.narration.narrations],
        }


class NarrationService:
    """Analyse, then explain."""

    def __init__(self, analysis: AnalysisService, renderer: NarrationRenderer) -> None:
        self._analysis = analysis
        self._renderer = renderer

    def run(
        self,
        user: User,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        days: int | None = None,
        allow_generation: bool = True,
    ) -> NarratedAnalysis:
        """Explain every insight and every data-sufficiency notice.

        Notices are narrated too, and deliberately: a user with three days of
        data gets a plain explanation of what is missing rather than an empty
        page (PDR-030). That is the response the honest empty state was
        designed to produce, and it is the one a new user sees most.
        """
        result = self._analysis.run(
            user, start_date=start_date, end_date=end_date, days=days
        )

        subjects: tuple[Insight, ...] = result.insights + result.notices
        narration = self._renderer.narrate_all(
            subjects,
            display_name=user.display_name,
            allow_generation=allow_generation,
        )

        return NarratedAnalysis(analysis=result, narration=narration)
