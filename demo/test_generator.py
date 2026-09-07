"""The generator: deterministic, realistic, and correct at the boundaries."""

from __future__ import annotations

from collections import Counter
from datetime import date, timedelta

import pytest

from app.demo.design import DEMO_SEED, NEGATIVE_CONTROLS, PERSONA, PLANTED_PATTERNS
from app.demo.generator import generate
from app.domain.enums import Category

REFERENCE = date(2026, 7, 28)


@pytest.fixture(scope="module")
def dataset():
    return generate(REFERENCE)


class TestDeterminism:
    def test_the_same_seed_and_date_produce_identical_data(self) -> None:
        """A demo that shifted between runs would make every screenshot and
        every number in the README a lie by the next morning."""
        first = generate(REFERENCE)
        second = generate(REFERENCE)

        assert first.expenses == second.expenses
        assert first.check_ins == second.check_ins
        assert first.events == second.events

    def test_a_different_seed_produces_different_data(self) -> None:
        assert generate(REFERENCE).expenses != generate(REFERENCE, seed=DEMO_SEED + 1).expenses

    def test_the_manifest_records_the_seed(self, dataset) -> None:
        assert dataset.manifest["seed"] == DEMO_SEED
        assert dataset.manifest["reference_date"] == REFERENCE.isoformat()


class TestShape:
    def test_it_ends_on_the_reference_date(self, dataset) -> None:
        assert dataset.end_date == REFERENCE

    def test_it_spans_enough_history_for_the_gates(self, dataset) -> None:
        # Gate G1 needs ≥ 8 complete weeks; the default window is 90 days.
        assert (dataset.end_date - dataset.start_date).days >= 180

    def test_every_record_falls_inside_the_window(self, dataset) -> None:
        for expense in dataset.expenses:
            assert dataset.start_date <= expense.expense_date <= dataset.end_date
        for check_in in dataset.check_ins:
            assert dataset.start_date <= check_in.log_date <= dataset.end_date

    def test_every_amount_is_a_positive_integer(self, dataset) -> None:
        """The schema's CHECK constraint would reject anything else, and money
        is integer paise throughout."""
        for expense in dataset.expenses:
            assert isinstance(expense.amount_paise, int)
            assert expense.amount_paise > 0

    def test_no_two_check_ins_share_a_date(self, dataset) -> None:
        """`uq_checkin_user_date` would reject a duplicate at insert time."""
        dates = [check_in.log_date for check_in in dataset.check_ins]

        assert len(dates) == len(set(dates))

    def test_no_expense_is_categorised_as_income_or_transfer(self, dataset) -> None:
        categories = {expense.category for expense in dataset.expenses}

        assert Category.INCOME not in categories
        assert Category.TRANSFERS not in categories


class TestRealism:
    def test_some_days_have_no_check_in(self, dataset) -> None:
        """A dataset logged perfectly every day would make the missed-days card
        and the coverage gate meaningless."""
        window_days = (dataset.end_date - dataset.start_date).days + 1

        assert len(dataset.check_ins) < window_days

    def test_coverage_still_clears_the_analysis_gate(self, dataset) -> None:
        window_days = (dataset.end_date - dataset.start_date).days + 1

        assert len(dataset.check_ins) / window_days > 0.6

    def test_rent_lands_once_a_month_at_a_fixed_amount(self, dataset) -> None:
        rent = [e for e in dataset.expenses if e.category is Category.RENT_HOUSING]
        months = {e.expense_date.strftime("%Y-%m") for e in rent}

        assert len(rent) == len(months), "one rent charge per month"
        assert {e.amount_paise for e in rent} == {PERSONA.monthly_rent_paise}

    def test_spending_is_spread_across_many_merchants(self, dataset) -> None:
        merchants = {e.merchant for e in dataset.expenses if e.merchant}

        assert len(merchants) >= 15

    def test_weekends_carry_more_transactions_than_weekdays(self, dataset) -> None:
        by_weekday = Counter(e.expense_date.weekday() for e in dataset.expenses)
        weekend = (by_weekday[5] + by_weekday[6]) / 2
        weekday = sum(by_weekday[d] for d in range(5)) / 5

        assert weekend > weekday

    def test_life_events_land_inside_the_window(self, dataset) -> None:
        assert dataset.events
        for event in dataset.events:
            assert dataset.start_date <= event.start_date <= dataset.end_date

    def test_a_point_event_has_no_end_date(self, dataset) -> None:
        assert any(event.end_date is None for event in dataset.events)


class TestPlantedPatterns:
    """The generator has to actually create what `design.py` declares."""

    def test_food_spending_is_higher_in_weeks_without_exercise(self, dataset) -> None:
        weeks: dict[date, dict[str, object]] = {}
        for check_in in dataset.check_ins:
            monday = check_in.log_date - timedelta(days=check_in.log_date.weekday())
            bucket = weeks.setdefault(monday, {"exercise": False, "food": 0})
            if check_in.exercise:
                bucket["exercise"] = True
        for expense in dataset.expenses:
            if expense.category is not Category.FOOD_DINING:
                continue
            monday = expense.expense_date - timedelta(days=expense.expense_date.weekday())
            if monday in weeks:
                weeks[monday]["food"] = int(weeks[monday]["food"]) + expense.amount_paise

        with_gym = [int(w["food"]) for w in weeks.values() if w["exercise"]]
        without = [int(w["food"]) for w in weeks.values() if not w["exercise"]]

        assert with_gym and without
        assert sum(without) / len(without) > sum(with_gym) / len(with_gym)

    def test_both_exercise_groups_are_large_enough_for_gate_g2(self, dataset) -> None:
        """⭐ Gate G2 needs ≥ 6 weeks in each group. The first version tiled
        phases forward from the start, which left ~5 exercise weeks in the
        default 90-day window and silently removed the product's headline
        pattern from the view the dashboard opens on."""
        recent = REFERENCE - timedelta(days=90)
        weeks: dict[date, bool] = {}
        for check_in in dataset.check_ins:
            if check_in.log_date < recent:
                continue
            monday = check_in.log_date - timedelta(days=check_in.log_date.weekday())
            weeks[monday] = weeks.get(monday, False) or bool(check_in.exercise)

        with_gym = sum(1 for value in weeks.values() if value)
        without = sum(1 for value in weeks.values() if not value)

        assert with_gym >= 6, f"only {with_gym} exercise weeks in the default window"
        assert without >= 6, f"only {without} rest weeks in the default window"

    def test_every_declared_pattern_names_a_real_habit(self, dataset) -> None:
        habits = {"sleep_minutes", "exercise", "home_cooked_meals", "stress_level",
                  "alcohol", "work_mode"}

        for pattern in PLANTED_PATTERNS:
            assert pattern.habit in habits


class TestNegativeControls:
    def test_the_controls_are_declared(self) -> None:
        assert set(NEGATIVE_CONTROLS) == {"alcohol", "work_mode"}

    def test_alcohol_is_recorded_but_uncorrelated_with_the_calendar(
        self, dataset
    ) -> None:
        """It must be *present* — an all-null control proves nothing, because
        the engine would exclude it for coverage rather than for finding
        nothing."""
        recorded = [c for c in dataset.check_ins if c.alcohol is not None]

        assert len(recorded) == len(dataset.check_ins)
        assert 0.05 < sum(1 for c in recorded if c.alcohol) / len(recorded) < 0.40

    def test_work_mode_is_recorded_throughout(self, dataset) -> None:
        assert all(c.work_mode is not None for c in dataset.check_ins)
