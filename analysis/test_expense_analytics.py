"""Expense analytics."""

from __future__ import annotations

from datetime import date, datetime

import pytest

from app.analysis import expenses as analytics
from app.analysis.models import InsightTier, InsightType
from app.analysis.window import AnalysisWindow
from app.domain.enums import Category, PaymentMethod
from tests.analysis.conftest import dataset, expense

JUNE = AnalysisWindow(date(2026, 6, 1), date(2026, 6, 30))


class TestTotalSpending:
    def test_sums_the_window(self, now: datetime) -> None:
        data = dataset(
            window=JUNE,
            expenses=(
                expense(date(2026, 6, 1), 45000),
                expense(date(2026, 6, 2), 15000),
            ),
        )

        insight = analytics.total_spending(data, now)

        assert insight.type is InsightType.SPENDING_TOTAL
        assert insight.tier is InsightTier.T1_DESCRIPTIVE
        assert insight.metrics["total_paise"] == 60000
        assert insight.metrics["expense_count"] == 2

    def test_transfers_and_income_are_excluded(self, now: datetime) -> None:
        """Moving money between your own accounts is not consumption, and
        counting it would inflate every figure downstream."""
        data = dataset(
            window=JUNE,
            expenses=(
                expense(date(2026, 6, 1), 45000, Category.FOOD_DINING),
                expense(date(2026, 6, 2), 900000, Category.TRANSFERS),
                expense(date(2026, 6, 3), 5000000, Category.INCOME),
            ),
        )

        insight = analytics.total_spending(data, now)

        assert insight.metrics["total_paise"] == 45000
        assert insight.metrics["excluded_non_spending_paise"] == 5900000
        assert insight.metrics["excluded_non_spending_count"] == 2

    def test_an_empty_window_still_produces_a_fact(self, now: datetime) -> None:
        insight = analytics.total_spending(dataset(window=JUNE), now)

        assert insight.metrics["total_paise"] == 0
        assert insight.metrics["active_days"] == 0
        assert insight.evidence, "an insight always carries evidence"

    def test_averages_use_exact_integer_paise(self, now: datetime) -> None:
        # 100 over 30 days is 3.33 paise/day, which must round to 3, not 3.33.
        data = dataset(window=JUNE, expenses=(expense(date(2026, 6, 1), 100),))

        insight = analytics.total_spending(data, now)

        assert insight.metrics["average_per_day_paise"] == 3
        assert isinstance(insight.metrics["average_per_day_paise"], int)

    def test_active_day_average_ignores_days_with_no_spending(
        self, now: datetime
    ) -> None:
        data = dataset(
            window=JUNE,
            expenses=(
                expense(date(2026, 6, 1), 10000),
                expense(date(2026, 6, 1), 20000),
                expense(date(2026, 6, 5), 30000),
            ),
        )

        insight = analytics.total_spending(data, now)

        assert insight.metrics["active_days"] == 2
        assert insight.metrics["average_per_active_day_paise"] == 30000

    def test_payment_methods_are_broken_out(self, now: datetime) -> None:
        data = dataset(
            window=JUNE,
            expenses=(
                expense(date(2026, 6, 1), 10000, payment_method=PaymentMethod.UPI),
                expense(date(2026, 6, 2), 20000, payment_method=PaymentMethod.CASH),
                expense(date(2026, 6, 3), 5000, payment_method=PaymentMethod.UPI),
            ),
        )

        insight = analytics.total_spending(data, now)

        assert insight.metrics["by_payment_method"] == {"CASH": 20000, "UPI": 15000}

    def test_the_largest_expenses_are_carried_as_evidence(self, now: datetime) -> None:
        data = dataset(
            window=JUNE,
            expenses=(
                expense(date(2026, 6, 1), 10000, record_id="small"),
                expense(date(2026, 6, 2), 99000, record_id="big"),
            ),
        )

        insight = analytics.total_spending(data, now)
        refs = [e.ref_id for e in insight.evidence if e.ref_id]

        assert refs[0] == "big"


class TestSpendingByCategory:
    def test_orders_categories_by_amount(self, now: datetime) -> None:
        data = dataset(
            window=JUNE,
            expenses=(
                expense(date(2026, 6, 1), 10000, Category.TRANSPORT),
                expense(date(2026, 6, 2), 90000, Category.FOOD_DINING),
                expense(date(2026, 6, 3), 50000, Category.GROCERIES),
            ),
        )

        insight = analytics.spending_by_category(data, now)

        assert [row["category"] for row in insight.metrics["categories"]] == [
            "FOOD_DINING",
            "GROCERIES",
            "TRANSPORT",
        ]
        assert insight.metrics["top_category"] == "FOOD_DINING"
        assert insight.subject == "FOOD_DINING"

    def test_shares_sum_to_one(self, now: datetime) -> None:
        data = dataset(
            window=JUNE,
            expenses=(
                expense(date(2026, 6, 1), 25000, Category.TRANSPORT),
                expense(date(2026, 6, 2), 75000, Category.FOOD_DINING),
            ),
        )

        insight = analytics.spending_by_category(data, now)
        shares = [row["share_ratio"] for row in insight.metrics["categories"]]

        assert sum(shares) == pytest.approx(1.0)
        assert shares[0] == pytest.approx(0.75)

    def test_no_spending_means_no_breakdown(self, now: datetime) -> None:
        """``None`` is 'nothing truthful to say', not an error."""
        assert analytics.spending_by_category(dataset(window=JUNE), now) is None

    def test_every_category_appears_as_evidence(self, now: datetime) -> None:
        data = dataset(
            window=JUNE,
            expenses=(
                expense(date(2026, 6, 1), 100, Category.TRANSPORT),
                expense(date(2026, 6, 2), 200, Category.FOOD_DINING),
            ),
        )

        insight = analytics.spending_by_category(data, now)

        assert len(insight.evidence) == 2


class TestMonthlyComparison:
    def test_compares_the_two_most_recent_complete_months(self, now: datetime) -> None:
        window = AnalysisWindow(date(2026, 4, 1), date(2026, 6, 30))
        data = dataset(
            window=window,
            expenses=(
                expense(date(2026, 4, 10), 10000),
                expense(date(2026, 5, 10), 20000),
                expense(date(2026, 6, 10), 50000),
            ),
        )

        insight = analytics.monthly_comparison(data, now)

        assert insight.metrics["current_period"] == "2026-06"
        assert insight.metrics["previous_period"] == "2026-05"
        assert insight.metrics["current_paise"] == 50000
        assert insight.metrics["previous_paise"] == 20000
        assert insight.metrics["difference_paise"] == 30000
        assert insight.metrics["relative_change"] == pytest.approx(1.5)
        assert insight.metrics["direction"] == "INCREASED"

    def test_partial_months_are_not_compared(self, now: datetime) -> None:
        """Half of July against all of June is a fact about the window."""
        window = AnalysisWindow(date(2026, 6, 1), date(2026, 7, 15))
        data = dataset(window=window, expenses=(expense(date(2026, 6, 10), 10000),))

        assert analytics.monthly_comparison(data, now) is None

    def test_a_single_complete_month_has_nothing_to_compare(self, now: datetime) -> None:
        data = dataset(window=JUNE, expenses=(expense(date(2026, 6, 10), 10000),))

        assert analytics.monthly_comparison(data, now) is None

    def test_a_small_move_is_reported_as_stable(self, now: datetime) -> None:
        window = AnalysisWindow(date(2026, 5, 1), date(2026, 6, 30))
        data = dataset(
            window=window,
            expenses=(
                expense(date(2026, 5, 10), 100000),
                expense(date(2026, 6, 10), 102000),
            ),
        )

        insight = analytics.monthly_comparison(data, now)

        assert insight.metrics["direction"] == "STABLE"
        assert insight.metrics["stable_band"] == 0.05

    def test_a_zero_baseline_yields_no_relative_change(self, now: datetime) -> None:
        """Percent change against zero is unbounded, so none is claimed."""
        window = AnalysisWindow(date(2026, 5, 1), date(2026, 6, 30))
        data = dataset(window=window, expenses=(expense(date(2026, 6, 10), 100000),))

        insight = analytics.monthly_comparison(data, now)

        assert insight.metrics["previous_paise"] == 0
        assert insight.metrics["relative_change"] is None
        assert insight.metrics["direction"] == "INCREASED"


class TestWeeklyComparison:
    def test_compares_the_two_most_recent_complete_weeks(self, now: datetime) -> None:
        # 2026-06-01 is a Monday, so June holds four complete ISO weeks.
        data = dataset(
            window=JUNE,
            expenses=(
                expense(date(2026, 6, 16), 30000),  # week of 15th
                expense(date(2026, 6, 23), 70000),  # week of 22nd
            ),
        )

        insight = analytics.weekly_comparison(data, now)

        assert insight.tier is InsightTier.T2_COMPARATIVE
        assert insight.metrics["current_paise"] == 70000
        assert insight.metrics["previous_paise"] == 30000
        assert insight.metrics["complete_periods_available"] == 4

    def test_fewer_than_two_complete_weeks_yields_nothing(self, now: datetime) -> None:
        window = AnalysisWindow(date(2026, 6, 1), date(2026, 6, 9))
        data = dataset(window=window, expenses=(expense(date(2026, 6, 2), 100),))

        assert analytics.weekly_comparison(data, now) is None


class TestDailyTrend:
    def test_days_without_spending_appear_as_zero(self, now: datetime) -> None:
        """A gap in a series reads as missing data; here it is a recorded fact."""
        window = AnalysisWindow(date(2026, 6, 1), date(2026, 6, 3))
        data = dataset(window=window, expenses=(expense(date(2026, 6, 2), 5000),))

        insight = analytics.daily_trend(data, now)

        assert insight.metrics["series"] == [
            {"date": "2026-06-01", "total_paise": 0},
            {"date": "2026-06-02", "total_paise": 5000},
            {"date": "2026-06-03", "total_paise": 0},
        ]
        assert insight.metrics["zero_spend_days"] == 2

    def test_reports_the_busiest_day(self, now: datetime) -> None:
        window = AnalysisWindow(date(2026, 6, 1), date(2026, 6, 4))
        data = dataset(
            window=window,
            expenses=(
                expense(date(2026, 6, 2), 5000),
                expense(date(2026, 6, 3), 8000),
                expense(date(2026, 6, 3), 1000),
            ),
        )

        insight = analytics.daily_trend(data, now)

        assert insight.metrics["busiest_day"] == "2026-06-03"
        assert insight.metrics["busiest_day_paise"] == 9000

    def test_halves_are_compared_for_direction(self, now: datetime) -> None:
        window = AnalysisWindow(date(2026, 6, 1), date(2026, 6, 4))
        data = dataset(
            window=window,
            expenses=(
                expense(date(2026, 6, 1), 1000),
                expense(date(2026, 6, 4), 9000),
            ),
        )

        insight = analytics.daily_trend(data, now)

        assert insight.metrics["first_half_paise"] == 1000
        assert insight.metrics["second_half_paise"] == 9000
        assert insight.metrics["direction"] == "INCREASED"

    def test_no_spending_yields_nothing(self, now: datetime) -> None:
        assert analytics.daily_trend(dataset(window=JUNE), now) is None


class TestBudgetUtilization:
    def test_suppressed_entirely_when_no_budget_is_set(self, now: datetime) -> None:
        """Inventing a budget from average spend would measure the user
        against a number they never chose."""
        data = dataset(window=JUNE, expenses=(expense(date(2026, 6, 1), 10000),))

        assert analytics.budget_utilization(data, now) is None

    def test_reports_utilisation_against_the_set_budget(self, now: datetime) -> None:
        data = dataset(
            window=JUNE,
            expenses=(expense(date(2026, 6, 10), 250000),),
            monthly_budget_paise=1000000,
        )

        insight = analytics.budget_utilization(data, now)

        assert insight.metrics["budget_paise"] == 1000000
        assert insight.metrics["spent_paise"] == 250000
        assert insight.metrics["remaining_paise"] == 750000
        assert insight.metrics["utilization_ratio"] == pytest.approx(0.25)
        assert insight.metrics["status"] == "WITHIN_BUDGET"

    @pytest.mark.parametrize(
        ("spent", "status"),
        [(500000, "WITHIN_BUDGET"), (850000, "NEAR_LIMIT"), (1100000, "OVER_BUDGET")],
    )
    def test_status_thresholds(self, now: datetime, spent: int, status: str) -> None:
        data = dataset(
            window=JUNE,
            expenses=(expense(date(2026, 6, 10), spent),),
            monthly_budget_paise=1000000,
        )

        assert analytics.budget_utilization(data, now).metrics["status"] == status

    def test_over_budget_reports_a_negative_remainder(self, now: datetime) -> None:
        data = dataset(
            window=JUNE,
            expenses=(expense(date(2026, 6, 10), 1200000),),
            monthly_budget_paise=1000000,
        )

        assert analytics.budget_utilization(data, now).metrics["remaining_paise"] == -200000

    def test_a_window_starting_mid_month_says_so(self, now: datetime) -> None:
        """The spend figure then counts only the covered part, and a renderer
        needs to know before presenting it as the month's total."""
        window = AnalysisWindow(date(2026, 6, 15), date(2026, 6, 30))
        data = dataset(
            window=window,
            expenses=(expense(date(2026, 6, 20), 10000),),
            monthly_budget_paise=1000000,
        )

        insight = analytics.budget_utilization(data, now)

        assert insight.metrics["covers_full_month_to_date"] is False
        assert insight.metrics["month"] == "2026-06"

    def test_only_the_ending_month_is_counted(self, now: datetime) -> None:
        window = AnalysisWindow(date(2026, 5, 1), date(2026, 6, 30))
        data = dataset(
            window=window,
            expenses=(
                expense(date(2026, 5, 10), 900000),
                expense(date(2026, 6, 10), 100000),
            ),
            monthly_budget_paise=1000000,
        )

        insight = analytics.budget_utilization(data, now)

        assert insight.metrics["spent_paise"] == 100000
