"""⭐ The test that makes the demo trustworthy.

It runs the **real analysis engine** over generated data and asserts every
planted pattern survives all five gates, and that neither negative control
produces a finding.

Without this, "the demo shows a correlation" is a hope. With it, a change to
the generator, the gates, or the statistics that broke the demonstration would
fail a build rather than be discovered in an interview.
"""

from __future__ import annotations

from datetime import date

import pytest

from app.analysis.models import InsightType
from app.demo.design import NEGATIVE_CONTROLS, PLANTED_PATTERNS
from app.demo.generator import generate
from app.demo.validation import EXPECTED_TYPES, validate_dataset

REFERENCE = date(2026, 7, 28)


@pytest.fixture(scope="module")
def dataset():
    return generate(REFERENCE)


@pytest.fixture(scope="module")
def report_90(dataset):
    """The default window — what the dashboard opens on."""
    return validate_dataset(dataset, window_days=90)


@pytest.fixture(scope="module")
def report_180(dataset):
    return validate_dataset(dataset, window_days=180)


class TestNegativeControls:
    """The primary quality bar (07_AI_Architecture.md §8).

    A generator that manufactured a pattern everywhere would prove the engine
    detects noise, which is the opposite of the claim the product makes. This
    matters more than recall on the planted patterns.
    """

    def test_no_false_positive_in_the_default_window(self, report_90) -> None:
        assert report_90.control_false_positives == 0

    def test_no_false_positive_over_a_longer_window(self, report_180) -> None:
        """More weeks means more power, which is exactly when a false positive
        would appear if the controls were not genuinely independent."""
        assert report_180.control_false_positives == 0

    def test_the_controls_were_actually_testable(self, report_90) -> None:
        """A control excluded for low coverage would pass vacuously — it has to
        be tested and found empty, not skipped."""
        assert report_90.hypotheses_tested > len(NEGATIVE_CONTROLS)


class TestPlantedPatterns:
    @pytest.mark.parametrize(
        "pattern", PLANTED_PATTERNS, ids=lambda p: f"{p.habit}-{p.category.value}"
    )
    def test_each_survives_every_gate_in_the_default_window(
        self, report_90, pattern
    ) -> None:
        key = (pattern.habit, pattern.category.value)

        assert key in report_90.found_patterns, (
            f"{pattern.habit} ↔ {pattern.category.value} was planted but not "
            "emitted — it failed one of the five gates."
        )

    @pytest.mark.parametrize(
        "pattern", PLANTED_PATTERNS, ids=lambda p: f"{p.habit}-{p.category.value}"
    )
    def test_each_uses_the_test_its_habit_type_calls_for(
        self, report_90, pattern
    ) -> None:
        found = report_90.found_patterns[(pattern.habit, pattern.category.value)]

        assert found["test"] == pattern.expected_test

    def test_each_is_reported_with_high_confidence(self, report_90) -> None:
        """A demo whose headline finding sits at 60% confidence is a demo that
        invites the wrong question."""
        for found in report_90.found_patterns.values():
            assert found["confidence"] >= 0.9

    def test_they_survive_a_longer_window_too(self, report_180) -> None:
        for pattern in PLANTED_PATTERNS:
            assert (pattern.habit, pattern.category.value) in report_180.found_patterns


class TestCoverage:
    def test_every_expected_insight_type_is_demonstrated(self, report_90) -> None:
        assert report_90.missing_insight_types == frozenset(), (
            f"not demonstrable from the demo data: {sorted(report_90.missing_insight_types)}"
        )

    def test_data_sufficiency_is_deliberately_absent(self, report_90) -> None:
        """The dataset is sufficient on purpose. A notice here would mean a
        gate failed; the honest empty state is demonstrated on a short window
        instead."""
        assert InsightType.DATA_SUFFICIENCY not in EXPECTED_TYPES
        assert "DATA_SUFFICIENCY" not in report_90.insight_types

    def test_the_window_holds_enough_weeks_for_gate_g1(self, report_90) -> None:
        assert report_90.complete_weeks >= 8


class TestTheReportItself:
    def test_it_is_valid_overall(self, report_90) -> None:
        assert report_90.is_valid

    def test_it_fails_loudly_when_a_pattern_is_missing(self, dataset) -> None:
        """Guards the guard: a report that could not fail would prove nothing.
        A fortnight is below gate G1, so nothing should be found."""
        report = validate_dataset(dataset, window_days=14)

        assert not report.is_valid
        assert not report.all_patterns_found


class TestDeterminism:
    def test_two_validations_agree(self, dataset) -> None:
        first = validate_dataset(dataset, window_days=90)
        second = validate_dataset(dataset, window_days=90)

        assert first.found_patterns == second.found_patterns
        assert first.insight_types == second.insight_types
