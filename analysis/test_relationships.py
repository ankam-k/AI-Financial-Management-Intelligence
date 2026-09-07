"""Behaviour relationships — the five gates and the four tests.

Two tests here carry more weight than the rest.

``test_a_real_signal_survives_every_gate`` proves the pipeline can actually
emit something. Without it, a gate bug that suppressed everything would look
identical to correct conservative behaviour, and every other test in this file
would still pass.

``test_the_same_signal_vanishes_when_the_habit_is_unlogged`` proves the
missing-data rule is load-bearing. It uses the same spending data with
``exercise=None`` instead of ``exercise=False``, and nothing is emitted.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from app.analysis.gates import DEFAULT_GATES, Gate, GateConfig
from app.analysis.models import InsightTier, InsightType
from app.analysis.relationships import behaviour_relationships, build_weeks
from app.analysis.window import AnalysisWindow
from app.domain.enums import Category, WorkMode
from tests.analysis.conftest import check_in, dataset, expense

#: 2026-03-02 is a Monday. Sixteen whole weeks, so gate G1 (≥ 8) is satisfied
#: and every test below is exercising a later gate.
START = date(2026, 3, 2)
WEEKS = 16
WINDOW = AnalysisWindow(START, START + timedelta(days=WEEKS * 7 - 1))


def week_days(index: int) -> list[date]:
    """The seven dates of week ``index`` (0-based)."""
    monday = START + timedelta(days=index * 7)
    return [monday + timedelta(days=offset) for offset in range(7)]


def signal_dataset(*, exercise_recorded: bool = True, **kwargs):
    """Weeks alternate exercise/no-exercise, with food spending to match.

    Exercise weeks: ~₹4,000 food. Non-exercise weeks: ~₹6,000. The gap is
    ₹2,000/week — comfortably past G4's ₹500 and 15% floors — and the groups
    separate perfectly, so Mann-Whitney has something real to find.
    """
    expenses = []
    check_ins = []

    for index in range(WEEKS):
        exercising = index % 2 == 0
        base = 400_000 if exercising else 600_000
        days = week_days(index)

        expenses.append(expense(days[0], base + index * 1_000, Category.FOOD_DINING))
        for offset, current in enumerate(days):
            value = exercising if exercise_recorded else None
            check_ins.append(
                check_in(current, exercise=value, sleep_minutes=420 + offset)
            )

    return dataset(
        window=WINDOW,
        expenses=tuple(expenses),
        check_ins=tuple(check_ins),
        **kwargs,
    )


class TestTheSignalPath:
    """The tests that prove the pipeline works end to end."""

    def test_a_real_signal_survives_every_gate(self, now: datetime) -> None:
        run = behaviour_relationships(signal_dataset(), now, DEFAULT_GATES)

        assert len(run.insights) == 1, "exactly one association is real here"
        insight = run.insights[0]

        assert insight.type is InsightType.BEHAVIOR_RELATIONSHIP
        assert insight.tier is InsightTier.T3_CORRELATIONAL
        assert insight.metrics["habit"] == "exercise"
        assert insight.metrics["category"] == "FOOD_DINING"
        assert insight.subject == "exercise:FOOD_DINING"

    def test_the_same_signal_vanishes_when_the_habit_is_unlogged(
        self, now: datetime
    ) -> None:
        """⭐ Identical spending, identical dates — only the habit values are
        UNKNOWN instead of recorded. Nothing may be claimed."""
        run = behaviour_relationships(
            signal_dataset(exercise_recorded=False), now, DEFAULT_GATES
        )

        assert run.insights == ()
        assert any(entry["gate"] == Gate.G3_COVERAGE.value for entry in run.suppressed)

    def test_the_emitted_insight_reports_both_groups(self, now: datetime) -> None:
        insight = behaviour_relationships(signal_dataset(), now, DEFAULT_GATES).insights[0]

        assert insight.metrics["group_a"]["n"] == 8
        assert insight.metrics["group_b"]["n"] == 8
        assert insight.metrics["group_b"]["median_paise"] > insight.metrics["group_a"]["median_paise"]
        assert insight.metrics["difference_paise"] > 0
        assert insight.metrics["relative_difference"] >= DEFAULT_GATES.min_relative_effect

    def test_it_reports_its_statistics_for_audit(self, now: datetime) -> None:
        insight = behaviour_relationships(signal_dataset(), now, DEFAULT_GATES).insights[0]
        statistics = insight.metrics["statistics"]

        assert statistics["test"] == "mann_whitney_u"
        assert 0.0 <= statistics["p_value"] <= 1.0
        assert statistics["q_value"] <= DEFAULT_GATES.fdr_q
        assert statistics["hypotheses_tested"] >= 1

    def test_it_reports_what_it_excluded(self, now: datetime) -> None:
        insight = behaviour_relationships(signal_dataset(), now, DEFAULT_GATES).insights[0]

        assert insight.metrics["observations"]["included"] == 16
        assert insight.metrics["observations"]["excluded_unknown"] == 0
        assert insight.metrics["observations"]["coverage_ratio"] == 1.0

    def test_the_claim_is_marked_correlational_and_tentative(
        self, now: datetime
    ) -> None:
        """The renderer is bound by these flags: no causal language, and no
        claim of an established pattern on a first observation (SRS-6.7)."""
        insight = behaviour_relationships(signal_dataset(), now, DEFAULT_GATES).insights[0]

        assert insight.metrics["claim_type"] == "ASSOCIATION"
        assert insight.metrics["stability_status"] == "TENTATIVE"

    def test_confidence_is_the_complement_of_the_q_value(self, now: datetime) -> None:
        insight = behaviour_relationships(signal_dataset(), now, DEFAULT_GATES).insights[0]

        assert insight.confidence == pytest.approx(
            1.0 - insight.metrics["statistics"]["q_value"], abs=1e-3
        )

    def test_it_carries_checkable_evidence(self, now: datetime) -> None:
        insight = behaviour_relationships(signal_dataset(), now, DEFAULT_GATES).insights[0]
        labels = {e.label for e in insight.evidence}

        assert {"group_a", "group_b"} <= labels
        assert any(e.kind.value == "CHECK_IN" for e in insight.evidence)


class TestGateOne:
    def test_too_little_history_suppresses_everything(self, now: datetime) -> None:
        short = AnalysisWindow(START, START + timedelta(days=27))  # 4 weeks
        data = dataset(
            window=short,
            expenses=(expense(START, 500_000),),
            check_ins=(check_in(START, exercise=True),),
        )

        run = behaviour_relationships(data, now, DEFAULT_GATES)

        assert run.insights == ()
        assert run.hypotheses_tested == 0

    def test_it_says_what_is_missing_rather_than_going_silent(
        self, now: datetime
    ) -> None:
        """PDR-030: under-claiming costs a session, over-claiming costs the user
        — but saying nothing at all costs both."""
        short = AnalysisWindow(START, START + timedelta(days=27))
        run = behaviour_relationships(dataset(window=short), now, DEFAULT_GATES)

        assert len(run.notices) == 1
        notice = run.notices[0]
        assert notice.type is InsightType.DATA_SUFFICIENCY
        assert notice.metrics["failed_gate"] == Gate.G1_HISTORY.value
        assert notice.metrics["current_value"] == 4
        assert notice.metrics["required_value"] == 8


class TestGateTwo:
    def test_a_group_below_the_minimum_is_not_tested(self, now: datetime) -> None:
        """Fifteen exercise weeks and one rest week is not a comparison."""
        expenses = []
        check_ins = []
        for index in range(WEEKS):
            exercising = index > 0
            days = week_days(index)
            expenses.append(
                expense(days[0], 400_000 if exercising else 900_000, Category.FOOD_DINING)
            )
            check_ins.extend(check_in(day, exercise=exercising) for day in days)

        data = dataset(
            window=WINDOW, expenses=tuple(expenses), check_ins=tuple(check_ins)
        )
        run = behaviour_relationships(data, now, DEFAULT_GATES)

        assert run.insights == ()
        assert any(entry["gate"] == Gate.G2_GROUP_SIZE.value for entry in run.suppressed)


class TestGateThree:
    def test_sparse_logging_suppresses_the_habit(self, now: datetime) -> None:
        """Exercise recorded in 4 of 16 weeks is 25% coverage, under the 60%
        floor — regardless of how clean the association looks."""
        expenses = []
        check_ins = []
        for index in range(WEEKS):
            exercising = index % 2 == 0
            days = week_days(index)
            expenses.append(
                expense(days[0], 400_000 if exercising else 600_000, Category.FOOD_DINING)
            )
            if index < 4:
                check_ins.extend(check_in(day, exercise=exercising) for day in days)

        data = dataset(
            window=WINDOW, expenses=tuple(expenses), check_ins=tuple(check_ins)
        )
        run = behaviour_relationships(data, now, DEFAULT_GATES)

        assert run.insights == ()
        assert any(entry["gate"] == Gate.G3_COVERAGE.value for entry in run.suppressed)

    def test_a_coverage_notice_names_the_habit(self, now: datetime) -> None:
        run = behaviour_relationships(
            signal_dataset(exercise_recorded=False), now, DEFAULT_GATES
        )

        subjects = {notice.subject for notice in run.notices}
        assert "exercise" in subjects


class TestGateFour:
    def test_a_statistically_clean_but_trivial_difference_is_discarded(
        self, now: datetime
    ) -> None:
        """₹5/week separates the groups perfectly. Significance is necessary,
        never sufficient."""
        expenses = []
        check_ins = []
        for index in range(WEEKS):
            exercising = index % 2 == 0
            days = week_days(index)
            expenses.append(
                expense(days[0], 100_000 if exercising else 100_500, Category.FOOD_DINING)
            )
            check_ins.extend(check_in(day, exercise=exercising) for day in days)

        data = dataset(
            window=WINDOW, expenses=tuple(expenses), check_ins=tuple(check_ins)
        )
        run = behaviour_relationships(data, now, DEFAULT_GATES)

        assert run.insights == ()
        assert any(entry["gate"] == Gate.G4_EFFECT_SIZE.value for entry in run.suppressed)

    def test_effect_size_is_checked_before_significance(self, now: datetime) -> None:
        """G4 runs first so a trivial difference does not consume an FDR slot
        and make a real finding harder to detect."""
        run = behaviour_relationships(signal_dataset(), now, DEFAULT_GATES)
        gates_hit = {entry["gate"] for entry in run.suppressed}

        assert Gate.G4_EFFECT_SIZE.value in gates_hit
        # Everything that failed G4 was dropped before the FDR pass, so the
        # tested count seen by G5 is smaller than the candidate count.
        assert run.hypotheses_tested > len(run.insights)


class TestGateFive:
    def test_a_strict_fdr_rejects_a_borderline_finding(self, now: datetime) -> None:
        strict = GateConfig(fdr_q=0.0001)

        run = behaviour_relationships(signal_dataset(), now, strict)

        assert run.insights == ()
        assert any(entry["gate"] == Gate.G5_SIGNIFICANCE.value for entry in run.suppressed)

    def test_suppression_records_both_p_and_q(self, now: datetime) -> None:
        run = behaviour_relationships(signal_dataset(), now, GateConfig(fdr_q=0.0001))
        rejected = next(
            e for e in run.suppressed if e["gate"] == Gate.G5_SIGNIFICANCE.value
        )

        assert "p_value" in rejected and "q_value" in rejected
        assert rejected["q_value"] >= rejected["p_value"]


class TestWeeklyAggregation:
    def test_only_complete_weeks_are_bucketed(self, now: datetime) -> None:
        window = AnalysisWindow(date(2026, 6, 3), date(2026, 6, 23))
        data = dataset(window=window)

        assert len(build_weeks(data)) == 2

    def test_a_week_is_an_exercise_week_if_any_day_recorded_one(
        self, now: datetime
    ) -> None:
        expenses = []
        check_ins = []
        for index in range(WEEKS):
            exercising = index % 2 == 0
            days = week_days(index)
            expenses.append(
                expense(days[0], 400_000 if exercising else 600_000, Category.FOOD_DINING)
            )
            # Only one day per week is logged, but it decides the week.
            check_ins.append(check_in(days[0], exercise=exercising))

        data = dataset(
            window=WINDOW, expenses=tuple(expenses), check_ins=tuple(check_ins)
        )
        run = behaviour_relationships(data, now, DEFAULT_GATES)

        assert len(run.insights) == 1


class TestOtherTestTypes:
    def test_a_numeric_habit_uses_spearman(self, now: datetime) -> None:
        """Sleep rises steadily while food spending falls — a monotonic
        relationship, which is what a rank correlation is for."""
        expenses = []
        check_ins = []
        for index in range(WEEKS):
            days = week_days(index)
            expenses.append(
                expense(days[0], 900_000 - index * 50_000, Category.FOOD_DINING)
            )
            check_ins.extend(
                check_in(day, sleep_minutes=300 + index * 10) for day in days
            )

        data = dataset(
            window=WINDOW, expenses=tuple(expenses), check_ins=tuple(check_ins)
        )
        run = behaviour_relationships(data, now, DEFAULT_GATES)

        assert len(run.insights) == 1
        assert run.insights[0].metrics["habit"] == "sleep_minutes"
        assert run.insights[0].metrics["statistics"]["test"] == "spearman"

    def test_a_categorical_habit_uses_kruskal_wallis(self, now: datetime) -> None:
        modes = [WorkMode.OFFICE, WorkMode.REMOTE]
        expenses = []
        check_ins = []
        for index in range(WEEKS):
            mode = modes[index % 2]
            days = week_days(index)
            amount = 300_000 if mode is WorkMode.REMOTE else 800_000
            expenses.append(expense(days[0], amount + index * 1_000, Category.TRANSPORT))
            check_ins.extend(check_in(day, work_mode=mode) for day in days)

        data = dataset(
            window=WINDOW, expenses=tuple(expenses), check_ins=tuple(check_ins)
        )
        run = behaviour_relationships(data, now, DEFAULT_GATES)

        assert len(run.insights) == 1
        assert run.insights[0].metrics["statistics"]["test"] == "kruskal_wallis"
        assert run.insights[0].metrics["habit"] == "work_mode"


class TestHypothesisSpace:
    def test_transfers_and_income_are_never_tested(self, now: datetime) -> None:
        run = behaviour_relationships(signal_dataset(), now, DEFAULT_GATES)
        tested = {entry["category"] for entry in run.suppressed}

        assert "TRANSFERS" not in tested
        assert "INCOME" not in tested

    def test_the_emitted_count_is_capped(self, now: datetime) -> None:
        capped = GateConfig(max_relationships=1)

        run = behaviour_relationships(signal_dataset(), now, capped)

        assert len(run.insights) <= 1


class TestDeterminism:
    def test_two_runs_over_the_same_data_are_identical(self, now: datetime) -> None:
        data = signal_dataset()

        first = behaviour_relationships(data, now, DEFAULT_GATES)
        second = behaviour_relationships(data, now, DEFAULT_GATES)

        assert [i.id for i in first.insights] == [i.id for i in second.insights]
        assert [i.metrics for i in first.insights] == [i.metrics for i in second.insights]
