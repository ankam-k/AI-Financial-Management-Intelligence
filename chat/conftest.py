"""Shared fixtures for chat tests."""

from __future__ import annotations

import pytest

from app.analysis.engine import AnalysisResult, analyse
from app.narration.models import Narration
from app.narration.renderer import NarrationRenderer
from app.llm.null import NullLLMClient
from tests.narration.conftest import NOW, signal_dataset


@pytest.fixture
def analysis() -> AnalysisResult:
    """A real sixteen-week run, including a T3 association."""
    return analyse(signal_dataset(), NOW)


@pytest.fixture
def narrations(analysis: AnalysisResult) -> dict[str, Narration]:
    """Template narration for that run — the prose chat quotes."""
    run = NarrationRenderer(NullLLMClient()).narrate_all(
        analysis.insights + analysis.notices
    )
    return {item.insight_id: item for item in run.narrations}


@pytest.fixture
def empty_analysis() -> AnalysisResult:
    """A window with nothing recorded in it."""
    from datetime import date

    from app.analysis.dataset import AnalysisDataset
    from app.analysis.window import AnalysisWindow

    return analyse(
        AnalysisDataset(window=AnalysisWindow(date(2026, 6, 1), date(2026, 6, 14))),
        NOW,
    )
