"""The Behavior Analysis Engine.

**This package is the application's source of truth.** Every number a user
will ever see is computed here, in an ``Insight`` object, before any renderer,
dashboard, report, or language model runs.

Three properties hold throughout, and the rest of the system depends on them:

**Pure.** Nothing here performs I/O. No database session, no HTTP client, no
filesystem, no model. The engine consumes an ``AnalysisDataset`` of plain
frozen dataclasses and returns ``Insight`` objects. Loading is somebody else's
job (``app/services/analysis_service.py``).

**Deterministic.** The same dataset and the same clock produce byte-identical
output, including insight ids. No randomness, no wall-clock reads, no
iteration over unordered sets.

**Silent about language.** The engine emits ``title_key``, not a title.
Turning ``"RELATIONSHIP_EXERCISE_FOOD_DINING"`` into a sentence is a rendering
decision made downstream — by a template today, by a model later. An engine
that wrote prose would be an engine whose prose nobody could validate.
"""

from app.analysis.dataset import (
    AnalysisDataset,
    CheckInRecord,
    EventRecord,
    ExpenseRecord,
)
from app.analysis.engine import ENGINE_VERSION, AnalysisResult, analyse
from app.analysis.gates import DEFAULT_GATES, GateConfig
from app.analysis.models import (
    Evidence,
    EvidenceKind,
    Insight,
    InsightTier,
    InsightType,
)
from app.analysis.window import AnalysisWindow

__all__ = [
    "AnalysisDataset",
    "AnalysisResult",
    "AnalysisWindow",
    "CheckInRecord",
    "DEFAULT_GATES",
    "ENGINE_VERSION",
    "Evidence",
    "EvidenceKind",
    "EventRecord",
    "ExpenseRecord",
    "GateConfig",
    "Insight",
    "InsightTier",
    "InsightType",
    "analyse",
]
