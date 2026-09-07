"""The FDR family is every hypothesis tested, not a post-effect-size subset.

V1.1 corrected the Benjamini-Hochberg step to run over the full candidate set,
matching ADR-007 decision #4 ("FDR at q = 0.10 across every hypothesis in a
run"). Before the fix, the correction ran only over G4 survivors, which is a
smaller, effect-selected family and therefore a weaker correction.

These golden values pin the corrected behaviour. A revert to the survivor
family would shrink the divisor and drop the q-values (exercise ↔ Food would
fall from ~0.047 back to ~0.007), failing this test.
"""

from __future__ import annotations

from datetime import date

import pytest

from app.demo.generator import generate
from app.demo.validation import validate_dataset

REFERENCE = date(2026, 7, 28)


@pytest.fixture(scope="module")
def report():
    return validate_dataset(generate(REFERENCE), window_days=90)


def test_the_family_is_larger_than_the_number_of_findings(report) -> None:
    # The correction divisor is the full family, which is far larger than the
    # handful of associations that ultimately surface.
    assert report.hypotheses_tested >= 50
    assert len(report.found_patterns) < report.hypotheses_tested


def test_exercise_food_q_reflects_full_family_correction(report) -> None:
    found = report.found_patterns[("exercise", "FOOD_DINING")]
    # Corrected over all ~56 hypotheses. Under the old survivor-only family the
    # same raw p-value produced q ≈ 0.007; the full family lifts it to ≈ 0.047.
    assert found["q_value"] == pytest.approx(0.047, abs=0.01)
    assert found["q_value"] > 0.02, "a survivor-family regression would drop below this"


def test_planted_patterns_still_clear_the_stricter_correction(report) -> None:
    # The stricter family must not silence the genuine planted signals.
    for key in [
        ("exercise", "FOOD_DINING"),
        ("sleep_minutes", "TRANSPORT"),
        ("home_cooked_meals", "FOOD_DINING"),
    ]:
        assert report.found_patterns[key]["q_value"] <= 0.10


def test_negative_controls_stay_silent_under_the_full_family(report) -> None:
    assert report.control_false_positives == 0
