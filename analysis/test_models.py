"""The Insight contract.

These tests defend the shape every downstream consumer will code against.
Breaking one of them is an API break for the dashboard, the report writer, and
the model that eventually narrates these objects.
"""

from __future__ import annotations

from datetime import date, datetime

import pytest

from app.analysis.models import (
    Evidence,
    EvidenceKind,
    Insight,
    InsightTier,
    InsightType,
)
from app.analysis.window import AnalysisWindow

WINDOW = AnalysisWindow(date(2026, 6, 1), date(2026, 6, 30))
NOW = datetime(2026, 7, 1, 9, 0)

AGGREGATE = Evidence(kind=EvidenceKind.AGGREGATE, label="total", payload={"total_paise": 1})


def build(**overrides: object) -> Insight:
    kwargs: dict[str, object] = {
        "type": InsightType.SPENDING_TOTAL,
        "tier": InsightTier.T1_DESCRIPTIVE,
        "title_key": "SPENDING_TOTAL",
        "window": WINDOW,
        "metrics": {"total_paise": 1},
        "evidence": (AGGREGATE,),
        "created_at": NOW,
    }
    kwargs.update(overrides)
    return Insight(**kwargs)  # type: ignore[arg-type]


class TestEvidenceIsMandatory:
    def test_an_insight_with_no_evidence_is_rejected(self) -> None:
        """SRS-2.5. The product's promise is that a claim can be opened and
        checked; a claim with nothing behind it is what it exists not to make."""
        with pytest.raises(ValueError, match="no evidence"):
            build(evidence=())

    def test_record_evidence_requires_a_reference(self) -> None:
        with pytest.raises(ValueError, match="requires a ref_id"):
            Evidence(kind=EvidenceKind.EXPENSE, label="largest")

    def test_aggregate_evidence_needs_no_reference(self) -> None:
        assert Evidence(kind=EvidenceKind.AGGREGATE, label="total").ref_id is None

    def test_evidence_requires_a_label(self) -> None:
        with pytest.raises(ValueError, match="label"):
            Evidence(kind=EvidenceKind.AGGREGATE, label="")


class TestConfidenceRules:
    def test_a_t3_insight_must_carry_confidence(self) -> None:
        with pytest.raises(ValueError, match="must carry a confidence"):
            build(tier=InsightTier.T3_CORRELATIONAL)

    def test_a_t1_insight_must_not_carry_confidence(self) -> None:
        """A sum is not uncertain. Emitting 1.0 would be inventing a number,
        which is the one thing this engine exists to avoid."""
        with pytest.raises(ValueError, match="carry no confidence"):
            build(confidence=1.0)

    def test_confidence_outside_zero_to_one_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="out of range"):
            build(tier=InsightTier.T3_CORRELATIONAL, confidence=1.5)

    def test_a_valid_t3_insight_is_accepted(self) -> None:
        insight = build(tier=InsightTier.T3_CORRELATIONAL, confidence=0.82)

        assert insight.confidence == 0.82


class TestMetricsMustBeJsonSafe:
    def test_a_date_object_is_rejected(self) -> None:
        """Caught here rather than as a 500 at the API boundary, far from the
        analytics function that produced it."""
        with pytest.raises(TypeError, match="ISO strings"):
            build(metrics={"as_of": date(2026, 6, 1)})

    def test_a_nested_date_is_also_caught(self) -> None:
        with pytest.raises(TypeError, match="ISO strings"):
            build(metrics={"series": [{"date": date(2026, 6, 1)}]})

    def test_non_string_keys_are_rejected(self) -> None:
        with pytest.raises(TypeError, match="keys must be strings"):
            build(metrics={1: "one"})

    def test_primitives_lists_and_nested_maps_are_allowed(self) -> None:
        insight = build(
            metrics={
                "total_paise": 100,
                "ratio": 0.5,
                "label": "x",
                "flag": True,
                "missing": None,
                "rows": [{"a": 1}, {"b": 2}],
            }
        )

        assert insight.metrics["rows"][1]["b"] == 2


class TestIdentity:
    def test_the_id_is_derived_not_random(self) -> None:
        assert build().id == build().id

    def test_different_windows_produce_different_ids(self) -> None:
        other = AnalysisWindow(date(2026, 5, 1), date(2026, 5, 31))

        assert build().id != build(window=other).id

    def test_different_subjects_produce_different_ids(self) -> None:
        assert build(subject="FOOD_DINING").id != build(subject="TRANSPORT").id

    def test_the_id_does_not_depend_on_the_metrics(self) -> None:
        """The id addresses *what* the insight is about, not its values — so a
        later run over changed data updates rather than duplicates it."""
        assert build(metrics={"total_paise": 1}).id == build(metrics={"total_paise": 2}).id


class TestImmutability:
    def test_an_insight_cannot_be_mutated(self) -> None:
        insight = build()

        with pytest.raises(Exception):
            insight.title_key = "SOMETHING_ELSE"  # type: ignore[misc]


class TestSerialisation:
    def test_as_dict_is_flat_and_json_ready(self) -> None:
        payload = build(subject="FOOD_DINING").as_dict()

        assert payload["type"] == "SPENDING_TOTAL"
        assert payload["tier"] == "T1"
        assert payload["window"] == {
            "start": "2026-06-01",
            "end": "2026-06-30",
            "days": 30,
        }
        assert payload["created_at"] == NOW.isoformat()
        assert payload["evidence"][0]["kind"] == "AGGREGATE"
        assert payload["confidence"] is None

    def test_every_insight_type_has_a_string_value(self) -> None:
        """Renderers key off these; an auto() value would be meaningless JSON."""
        assert all(item.value == item.name for item in InsightType)


class TestNoNaturalLanguage:
    def test_the_title_key_is_a_machine_key(self) -> None:
        """The engine emits keys, not prose. Rendering happens downstream,
        which is what makes ADR-009's provenance validation possible."""
        key = build().title_key

        assert key.isupper() or "_" in key
        assert " " not in key
