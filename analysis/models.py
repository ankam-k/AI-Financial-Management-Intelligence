"""The ``Insight`` — the object every other part of the system consumes.

Dashboard renders it. Reports format it. A model, when one arrives, explains
it and nothing else. Defining it once, here, is what stops each of those
inventing its own response shape.

## Why there is no ``title``

A title is natural language, and the engine does not write natural language.
``title_key`` is a stable machine identifier — ``"TOP_CATEGORY"``,
``"RELATIONSHIP_EXERCISE_FOOD_DINING"`` — that a renderer maps to a sentence.

The distinction is not pedantry. ADR-009's provenance validator works by
extracting every numeric literal from generated prose and asserting
set-membership against the insight's numbers. That check is only possible
because the insight is finished, and finished in structured form, *before*
generation begins. An engine that emitted "You spent ₹4,120 on food" would
have produced an unvalidatable sentence, and the guarantee would be gone.

## Why ``confidence`` is optional

``confidence: float`` in a first sketch is tempting, but a total-spending
figure has no confidence — it is a sum. Emitting ``1.0`` would be inventing a
number, which is precisely what this engine exists to avoid.

So confidence is **required for T3 and forbidden for T1/T2** (SRS-2.1,
PDR-032🟠), enforced below rather than documented and hoped for.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Mapping

from app.analysis.window import AnalysisWindow


class InsightTier(str, Enum):
    """How the claim was established (07_AI_Architecture.md §2).

    The tier determines what may be said about the insight, not how
    interesting it is.
    """

    #: Exact arithmetic over the ledger. Provable by summation.
    T1_DESCRIPTIVE = "T1"
    #: Threshold-based comparison with the parameters recorded on the insight.
    T2_COMPARATIVE = "T2"
    #: Statistical association, gated and FDR-corrected. Correlational only.
    T3_CORRELATIONAL = "T3"


class InsightType(str, Enum):
    """The closed set of things this engine can conclude."""

    # ── Expense analytics (T1/T2) ───────────────────────────────────────────
    SPENDING_TOTAL = "SPENDING_TOTAL"
    SPENDING_BY_CATEGORY = "SPENDING_BY_CATEGORY"
    SPENDING_MONTHLY_COMPARISON = "SPENDING_MONTHLY_COMPARISON"
    SPENDING_WEEKLY_COMPARISON = "SPENDING_WEEKLY_COMPARISON"
    SPENDING_DAILY_TREND = "SPENDING_DAILY_TREND"
    BUDGET_UTILIZATION = "BUDGET_UTILIZATION"

    # ── Habit analytics (T1) ────────────────────────────────────────────────
    HABIT_COMPLETION = "HABIT_COMPLETION"
    HABIT_STREAK = "HABIT_STREAK"
    HABIT_SLEEP_AVERAGE = "HABIT_SLEEP_AVERAGE"
    HABIT_EXERCISE_FREQUENCY = "HABIT_EXERCISE_FREQUENCY"
    HABIT_MISSED_DAYS = "HABIT_MISSED_DAYS"

    # ── Event analytics (T1/T2) ─────────────────────────────────────────────
    EVENT_SUMMARY = "EVENT_SUMMARY"
    EVENT_IMPACT = "EVENT_IMPACT"

    # ── Behaviour relationships (T3) ────────────────────────────────────────
    BEHAVIOR_RELATIONSHIP = "BEHAVIOR_RELATIONSHIP"

    # ── The honest empty state (SRS-6.11, PDR-030) ──────────────────────────
    DATA_SUFFICIENCY = "DATA_SUFFICIENCY"


class EvidenceKind(str, Enum):
    """What an evidence row points at."""

    EXPENSE = "EXPENSE"
    CHECK_IN = "CHECK_IN"
    LIFE_EVENT = "LIFE_EVENT"
    #: A computed group, bucket, or aggregate — no single row to point at.
    AGGREGATE = "AGGREGATE"


#: What a metrics payload is allowed to contain. Enforced, because the whole
#: object is serialised to JSON and handed to renderers: a ``date`` or a
#: ``Decimal`` slipping in here becomes a 500 at the API boundary, far from
#: the analytics function that produced it.
_JSON_SCALARS = (str, int, float, bool, type(None))


def _assert_json_safe(value: Any, path: str) -> None:
    if isinstance(value, bool) or isinstance(value, _JSON_SCALARS):
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(f"{path}: metric keys must be strings, got {key!r}")
            _assert_json_safe(item, f"{path}.{key}")
        return
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _assert_json_safe(item, f"{path}[{index}]")
        return
    if isinstance(value, (date, datetime)):
        raise TypeError(
            f"{path}: dates must be stored as ISO strings, not {type(value).__name__}"
        )
    raise TypeError(f"{path}: {type(value).__name__} is not JSON-serialisable")


@dataclass(frozen=True, slots=True)
class Evidence:
    """A pointer to something the user can check.

    **An insight with no evidence is a defect** (SRS-2.5). The point of this
    product is that a claim can be opened and inspected; a claim with nothing
    behind it is the thing it was built not to produce.
    """

    kind: EvidenceKind
    #: Machine key describing this row's role: ``"group_a"``, ``"top_expense"``.
    label: str
    #: Id of the source record, when the evidence is a record.
    ref_id: str | None = None
    payload: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.label:
            raise ValueError("evidence requires a label")
        if self.kind is not EvidenceKind.AGGREGATE and self.ref_id is None:
            raise ValueError(f"{self.kind.value} evidence requires a ref_id")
        _assert_json_safe(self.payload, "evidence.payload")

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "label": self.label,
            "ref_id": self.ref_id,
            "payload": dict(self.payload),
        }


@dataclass(frozen=True, slots=True)
class Insight:
    """A structured, finished conclusion about a window of user data.

    Frozen: an insight is a statement about a window at a moment. Mutating one
    after construction means something downstream disagreed with the engine,
    which is exactly the situation this design exists to prevent.
    """

    type: InsightType
    tier: InsightTier
    #: Stable renderer key. Never prose.
    title_key: str
    window: AnalysisWindow
    #: Every number the user will ever see, in JSON-safe primitives.
    metrics: Mapping[str, Any]
    evidence: tuple[Evidence, ...]
    created_at: datetime
    #: The entity this is about: a category, a habit, an event id. Machine key.
    subject: str | None = None
    #: Required for T3, forbidden for T1/T2.
    confidence: float | None = None
    #: Derived — see :meth:`_derive_id`.
    id: str = field(init=False, default="")

    def __post_init__(self) -> None:
        if not self.evidence:
            raise ValueError(
                f"{self.type.value} has no evidence. An insight with zero "
                "evidence is a defect (SRS-2.5)."
            )
        if self.tier is InsightTier.T3_CORRELATIONAL:
            if self.confidence is None:
                raise ValueError("a T3 insight must carry a confidence")
            if not 0.0 <= self.confidence <= 1.0:
                raise ValueError(f"confidence out of range: {self.confidence}")
        elif self.confidence is not None:
            raise ValueError(
                f"{self.tier.value} insights carry no confidence — a sum is not "
                "uncertain, and inventing 1.0 would be inventing a number."
            )
        _assert_json_safe(self.metrics, "metrics")
        object.__setattr__(self, "id", self._derive_id())

    def _derive_id(self) -> str:
        """A content-addressed id.

        Deterministic rather than random: the same run over the same data must
        produce the same ids, so a test can assert on them and so a future
        feedback row can point at an insight that regenerates identically.
        """
        seed = "|".join(
            [
                self.type.value,
                self.title_key,
                self.subject or "",
                self.window.start.isoformat(),
                self.window.end.isoformat(),
            ]
        )
        return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]

    def as_dict(self) -> dict[str, Any]:
        """JSON-safe representation. The API layer's serialisation is this."""
        return {
            "id": self.id,
            "type": self.type.value,
            "tier": self.tier.value,
            "title_key": self.title_key,
            "subject": self.subject,
            "window": self.window.as_dict(),
            "metrics": dict(self.metrics),
            "evidence": [item.as_dict() for item in self.evidence],
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
        }
