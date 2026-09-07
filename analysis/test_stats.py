"""Statistics primitives.

Reference values come from published worked examples and from closed forms,
not from a prior run of this code — a test that asserts the implementation
against itself proves only that it is deterministic.
"""

from __future__ import annotations

import math

import pytest

from app.analysis.stats import (
    benjamini_hochberg,
    chi_square_sf,
    kruskal_wallis,
    mann_whitney_u,
    mean_paise,
    median,
    median_paise,
    normal_sf,
    rank,
    round_half_up,
    spearman,
)


class TestRank:
    def test_ranks_are_one_based(self) -> None:
        assert rank([10, 20, 30]) == [1.0, 2.0, 3.0]

    def test_ties_take_the_average_rank(self) -> None:
        # Positions 2 and 3 tie, so both take rank 2.5.
        assert rank([10, 20, 20, 30]) == [1.0, 2.5, 2.5, 4.0]

    def test_all_tied_values_share_the_midpoint(self) -> None:
        assert rank([5, 5, 5, 5]) == [2.5, 2.5, 2.5, 2.5]

    def test_ranks_follow_value_order_not_input_order(self) -> None:
        assert rank([30, 10, 20]) == [3.0, 1.0, 2.0]


class TestDistributions:
    def test_normal_survival_at_zero_is_one_half(self) -> None:
        assert normal_sf(0.0) == pytest.approx(0.5)

    def test_normal_survival_matches_known_quantiles(self) -> None:
        assert normal_sf(1.959964) == pytest.approx(0.025, abs=1e-6)
        assert normal_sf(2.575829) == pytest.approx(0.005, abs=1e-6)

    def test_chi_square_df2_is_a_closed_form(self) -> None:
        assert chi_square_sf(0.0, df=2) == 1.0
        assert chi_square_sf(5.991, df=2) == pytest.approx(0.05, abs=1e-4)

    def test_chi_square_df1_matches_the_normal_two_sided_tail(self) -> None:
        assert chi_square_sf(3.8415, df=1) == pytest.approx(0.05, abs=1e-4)

    def test_higher_degrees_of_freedom_fail_loudly(self) -> None:
        """A categorical habit with >3 levels would need a real gamma function.
        Better a crash than a silently wrong p-value."""
        with pytest.raises(NotImplementedError):
            chi_square_sf(1.0, df=3)


class TestIntegerMoneyHelpers:
    @pytest.mark.parametrize(
        ("numerator", "denominator", "expected"),
        [(5, 2, 3), (4, 2, 2), (3, 2, 2), (1, 3, 0), (2, 3, 1), (-5, 2, -3), (0, 7, 0)],
    )
    def test_round_half_up(self, numerator: int, denominator: int, expected: int) -> None:
        assert round_half_up(numerator, denominator) == expected

    def test_mean_stays_exact_beyond_float_precision(self) -> None:
        """Where ``sum(v) / n`` would already have lost paise."""
        huge = [9_007_199_254_740_993, 9_007_199_254_740_995]
        assert mean_paise(huge) == 9_007_199_254_740_994

    def test_median_of_even_count_rounds_half_up_not_down(self) -> None:
        # Naive `//` would give 150, biasing every even-length median low.
        assert median_paise([100, 201]) == 151

    def test_median_of_odd_count_is_the_middle_value(self) -> None:
        assert median_paise([300, 100, 200]) == 200

    def test_median_of_empty_raises(self) -> None:
        with pytest.raises(ValueError):
            median([])


class TestMannWhitney:
    def test_perfectly_separated_groups_are_highly_significant(self) -> None:
        result = mann_whitney_u([1, 2, 3, 4, 5, 6], [10, 11, 12, 13, 14, 15])

        assert result.test == "mann_whitney_u"
        assert result.statistic == 0.0
        assert result.p_value < 0.01
        assert result.n == 12

    def test_identical_groups_show_no_evidence(self) -> None:
        result = mann_whitney_u([5, 5, 5, 5], [5, 5, 5, 5])

        assert result.p_value == 1.0

    def test_interleaved_groups_are_not_significant(self) -> None:
        result = mann_whitney_u([1, 3, 5, 7, 9, 11], [2, 4, 6, 8, 10, 12])

        assert result.p_value > 0.5

    def test_the_statistic_is_symmetric_in_the_arguments(self) -> None:
        a, b = [1, 2, 3, 4, 5, 6], [4, 5, 6, 7, 8, 9]

        assert mann_whitney_u(a, b).statistic == mann_whitney_u(b, a).statistic

    def test_heavy_cross_group_ties_show_little_evidence(self) -> None:
        """Eleven identical observations and one outlier is not a difference
        between groups, and the tie-corrected variance has to say so."""
        result = mann_whitney_u([5, 5, 5, 5, 5, 5], [5, 5, 5, 5, 5, 6])

        assert result.p_value > 0.3

    def test_an_empty_group_is_an_error_not_a_p_value(self) -> None:
        with pytest.raises(ValueError):
            mann_whitney_u([], [1, 2, 3])


class TestSpearman:
    def test_perfect_monotonic_increase_gives_rho_one(self) -> None:
        result = spearman([1, 2, 3, 4, 5], [10, 20, 30, 40, 50])

        assert result.statistic == pytest.approx(1.0)
        assert result.p_value == 0.0

    def test_perfect_monotonic_decrease_gives_rho_minus_one(self) -> None:
        result = spearman([1, 2, 3, 4, 5], [50, 40, 30, 20, 10])

        assert result.statistic == pytest.approx(-1.0)

    def test_rank_correlation_ignores_non_linear_scaling(self) -> None:
        """Spearman is rank-based, so a cubic relationship is still ρ = 1."""
        result = spearman([1, 2, 3, 4, 5], [1, 8, 27, 64, 125])

        assert result.statistic == pytest.approx(1.0)

    def test_a_constant_series_yields_no_evidence(self) -> None:
        result = spearman([1, 2, 3, 4, 5], [7, 7, 7, 7, 7])

        assert result.statistic == 0.0
        assert result.p_value == 1.0

    def test_mismatched_lengths_are_an_error(self) -> None:
        with pytest.raises(ValueError):
            spearman([1, 2, 3], [1, 2])

    def test_too_few_pairs_is_an_error(self) -> None:
        with pytest.raises(ValueError):
            spearman([1, 2, 3], [3, 2, 1])


class TestKruskalWallis:
    def test_well_separated_groups_are_significant(self) -> None:
        result = kruskal_wallis([[1, 2, 3, 4], [10, 11, 12, 13], [20, 21, 22, 23]])

        assert result.test == "kruskal_wallis"
        assert result.p_value < 0.05
        assert result.n == 12

    def test_identical_groups_show_no_evidence(self) -> None:
        result = kruskal_wallis([[1, 2, 3], [1, 2, 3], [1, 2, 3]])

        assert result.statistic == pytest.approx(0.0, abs=1e-9)
        assert result.p_value == pytest.approx(1.0)

    def test_two_groups_use_one_degree_of_freedom(self) -> None:
        result = kruskal_wallis([[1, 2, 3, 4], [10, 11, 12, 13]])

        assert result.p_value == pytest.approx(chi_square_sf(result.statistic, df=1))

    def test_a_single_group_is_an_error(self) -> None:
        with pytest.raises(ValueError):
            kruskal_wallis([[1, 2, 3]])


class TestBenjaminiHochberg:
    def test_empty_input_returns_empty(self) -> None:
        assert benjamini_hochberg([]) == []

    def test_a_single_hypothesis_is_uncorrected(self) -> None:
        assert benjamini_hochberg([0.03]) == [pytest.approx(0.03)]

    def test_q_values_never_decrease_with_rank(self) -> None:
        p_values = [0.001, 0.008, 0.039, 0.041, 0.042, 0.06, 0.074, 0.205]
        adjusted = benjamini_hochberg(p_values)

        ordered = [adjusted[i] for i in sorted(range(len(p_values)), key=lambda i: p_values[i])]
        assert ordered == sorted(ordered), "monotonicity is what makes BH valid"

    def test_input_order_is_preserved(self) -> None:
        adjusted = benjamini_hochberg([0.9, 0.001, 0.5])

        assert adjusted[1] < adjusted[2] < adjusted[0]

    def test_correction_scales_with_the_number_of_hypotheses(self) -> None:
        """The reason this function exists: 84 hypotheses per run means a raw
        p of 0.01 is unremarkable."""
        alone = benjamini_hochberg([0.01])[0]
        among_many = benjamini_hochberg([0.01] + [0.5] * 83)[0]

        assert alone == pytest.approx(0.01)
        # 0.01 raw becomes 0.5 adjusted — comfortably above the q = 0.10 gate,
        # so this hypothesis is rejected once its 83 companions are accounted
        # for. Uncorrected it would have been shown to the user as a finding.
        assert among_many == pytest.approx(0.5)
        assert among_many > 0.10

    def test_q_values_are_capped_at_one(self) -> None:
        assert all(value <= 1.0 for value in benjamini_hochberg([0.9, 0.95, 0.99]))

    def test_invalid_q_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            benjamini_hochberg([0.1], q=0.0)


class TestDeterminism:
    def test_repeated_runs_are_identical(self) -> None:
        a = [3, 1, 4, 1, 5, 9, 2, 6]
        b = [2, 7, 1, 8, 2, 8, 1, 8]

        first = mann_whitney_u(a, b)
        second = mann_whitney_u(a, b)

        assert (first.statistic, first.p_value) == (second.statistic, second.p_value)
        assert not math.isnan(first.p_value)
