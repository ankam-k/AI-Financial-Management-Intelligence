"""The model's input, and the numbers it will be held to."""

from __future__ import annotations

import json

import pytest

from app.analysis.models import Insight, InsightType
from app.narration.payload import (
    MAX_ARRAY_ITEMS,
    allowed_numbers,
    build_payload,
    canonical,
    extract_numbers,
)


class TestCanonicalisation:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("4,120.00", "4120"),
            ("4120.0", "4120"),
            ("4120", "4120"),
            ("0.4939", "0.4939"),
            ("49.40", "49.4"),
            ("1,00,000", "100000"),
            ("0", "0"),
        ],
    )
    def test_formatting_choices_collapse_to_one_form(self, raw: str, expected: str) -> None:
        """A comma or a trailing zero is a style decision by the model, not a
        different number. Treating them as different would reject correct
        prose."""
        assert canonical(raw) == expected

    def test_extraction_finds_every_literal(self) -> None:
        numbers = extract_numbers("You spent ₹4,120.50 across 16 weeks, up 49.4%.")

        assert numbers == ["4120.5", "16", "49.4"]

    def test_extraction_ignores_words(self) -> None:
        assert extract_numbers("You spent more in some weeks than others.") == []


class TestPayloadContents:
    def test_it_carries_the_insight_and_nothing_else(
        self, relationship_insight: Insight
    ) -> None:
        """SRS-7.2 — never raw transactions, never the ledger, never a
        database handle."""
        payload = build_payload(relationship_insight)

        assert set(payload) == {
            "insight_type",
            "tier",
            "subject",
            "window",
            "metrics",
            "evidence",
            "currency",
        }

    def test_it_is_json_serialisable(self, relationship_insight: Insight) -> None:
        assert json.loads(json.dumps(build_payload(relationship_insight)))

    def test_long_arrays_are_truncated(self, every_insight: dict[InsightType, Insight]) -> None:
        """A 90-day daily series is thousands of tokens the model cannot use
        in three sentences."""
        trend = every_insight[InsightType.SPENDING_DAILY_TREND]

        series = build_payload(trend)["metrics"]["series"]

        assert len(series) == MAX_ARRAY_ITEMS + 1
        assert "more omitted" in series[-1]

    def test_truncation_is_announced_not_silent(
        self, every_insight: dict[InsightType, Insight]
    ) -> None:
        trend = every_insight[InsightType.SPENDING_DAILY_TREND]
        original = len(trend.metrics["series"])

        marker = build_payload(trend)["metrics"]["series"][-1]

        assert str(original - MAX_ARRAY_ITEMS) in marker

    def test_evidence_is_summarised(self, relationship_insight: Insight) -> None:
        payload = build_payload(relationship_insight)

        assert payload["evidence"]
        for item in payload["evidence"]:
            assert set(item) == {"kind", "label", "detail"}

    def test_the_payload_is_stable_across_builds(
        self, relationship_insight: Insight
    ) -> None:
        first = build_payload(relationship_insight)
        second = build_payload(relationship_insight)

        assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


class TestAllowedNumbers:
    def test_money_licenses_its_rupee_forms(self, relationship_insight: Insight) -> None:
        """412000 paise is ₹4,120 — the model may write either."""
        payload = build_payload(relationship_insight)
        allowed = allowed_numbers(payload)

        median = relationship_insight.metrics["group_a"]["median_paise"]
        assert canonical(str(median)) in allowed
        assert canonical(f"{median / 100:.2f}") in allowed

    def test_ratios_license_their_percent_forms(
        self, relationship_insight: Insight
    ) -> None:
        allowed = allowed_numbers(build_payload(relationship_insight))
        relative = relationship_insight.metrics["relative_difference"]

        assert canonical(f"{relative * 100:.2f}") in allowed
        assert canonical(f"{relative * 100:.1f}") in allowed
        assert canonical(f"{relative * 100:.0f}") in allowed

    def test_counts_are_licensed(self, relationship_insight: Insight) -> None:
        allowed = allowed_numbers(build_payload(relationship_insight))

        assert canonical(str(relationship_insight.metrics["group_a"]["n"])) in allowed

    def test_dates_license_their_components(self, relationship_insight: Insight) -> None:
        """A narration quoting '2026-06-21' must not trip the validator."""
        allowed = allowed_numbers(build_payload(relationship_insight))

        assert "2026" in allowed

    def test_an_invented_number_is_not_licensed(
        self, relationship_insight: Insight
    ) -> None:
        allowed = allowed_numbers(build_payload(relationship_insight))

        assert canonical("987654321") not in allowed

    def test_truncated_values_are_not_licensed(
        self, every_insight: dict[InsightType, Insight]
    ) -> None:
        """⭐ The set is built from the trimmed payload. A number the model was
        never shown is one it cannot have read, and citing it would be a
        fabrication that happened to be true."""
        trend = every_insight[InsightType.SPENDING_DAILY_TREND]
        payload = build_payload(trend)
        allowed = allowed_numbers(payload)

        dropped = trend.metrics["series"][MAX_ARRAY_ITEMS:]
        distinctive = [
            canonical(str(row["total_paise"]))
            for row in dropped
            if row["total_paise"] > 0
        ]
        # At least one dropped value must be absent, or truncation bought
        # nothing. (Some may coincide with retained values.)
        assert any(value not in allowed for value in distinctive) or not distinctive

    def test_booleans_are_not_treated_as_numbers(
        self, every_insight: dict[InsightType, Insight]
    ) -> None:
        """`True` is `1` in Python. Licensing it would let the model write
        '1' anywhere a flag happened to be set."""
        impact = every_insight[InsightType.EVENT_IMPACT]
        assert impact.metrics["is_statistical_test"] is False

        payload = build_payload(impact)
        payload_only_flag = {"metrics": {"is_statistical_test": True, "other": False}}

        assert allowed_numbers(payload_only_flag) == frozenset()
        assert allowed_numbers(payload)  # the real payload still has numbers
