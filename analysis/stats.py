"""Deterministic non-parametric statistics, on the standard library alone.

## Why these tests

Weekly spending is right-skewed with heavy tails — one wedding, one flight —
and n is small. Parametric assumptions do not hold, so the tests are
rank-based throughout (ADR-007):

| Habit type | Habits | Test |
|---|---|---|
| Binary | `exercise`, `alcohol` | Mann–Whitney U |
| Ordinal | `stress_level`, `home_cooked_meals` | Spearman ρ |
| Numeric | `sleep_minutes` | Spearman ρ |
| Categorical | `work_mode` | Kruskal–Wallis H |

## Why not SciPy

SciPy would be the production choice and gives exact small-sample p-values.
It is not added here because Sprint 2 was scoped to add no dependency unless
necessary, and the approximations below are adequate **given gate G2**, which
requires n ≥ 6 per group before any test runs. The p-values are approximate;
where that matters it is stated on the function.

If exact small-sample p-values ever become load-bearing — a published claim, a
regulatory context — swap these three functions for `scipy.stats`. The
signatures are chosen to make that a drop-in change.

Every function is pure and deterministic: no randomness, no iteration over
unordered collections, no wall clock.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True, slots=True)
class TestResult:
    """The outcome of one hypothesis test."""

    #: Machine name of the test used, recorded on the insight for audit.
    test: str
    statistic: float
    #: Two-sided p-value.
    p_value: float
    #: Total observations across all compared groups.
    n: int


# ── Distribution helpers ────────────────────────────────────────────────────


def normal_sf(z: float) -> float:
    """Upper-tail probability of the standard normal, P(Z > z)."""
    return 0.5 * math.erfc(z / math.sqrt(2.0))


def chi_square_sf(x: float, df: int) -> float:
    """Upper-tail probability of chi-square, for **df ∈ {1, 2} only**.

    Both have closed forms in elementary functions, which is why no incomplete
    gamma implementation appears in this file. df is bounded at 2 because the
    only categorical habit is ``work_mode`` with three levels, giving k−1 ≤ 2.
    A wider categorical habit would need a real gamma function — the guard
    below makes that a loud failure rather than a wrong number.
    """
    if x <= 0:
        return 1.0
    if df == 1:
        return math.erfc(math.sqrt(x / 2.0))
    if df == 2:
        return math.exp(-x / 2.0)
    raise NotImplementedError(
        f"chi_square_sf supports df 1 and 2, got {df}. A categorical habit with "
        "more than three levels needs an incomplete gamma function."
    )


def rank(values: Sequence[float]) -> list[float]:
    """Competition-free ranks with **average ranks for ties**, 1-based.

    Tie handling is not cosmetic: it feeds the variance correction in
    Mann–Whitney and Kruskal–Wallis. Weekly spending buckets tie often enough
    (two zero-spend weeks) that ignoring it inflates significance.
    """
    indexed = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    position = 0
    while position < len(indexed):
        end = position
        while end + 1 < len(indexed) and values[indexed[end + 1]] == values[indexed[position]]:
            end += 1
        average = (position + end) / 2.0 + 1.0
        for i in range(position, end + 1):
            ranks[indexed[i]] = average
        position = end + 1
    return ranks


def _tie_correction(values: Sequence[float]) -> float:
    """Σ(t³ − t) over tie groups, used by both rank-sum variance formulas."""
    counts: dict[float, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return sum(t**3 - t for t in counts.values() if t > 1)


# ── Descriptive helpers ─────────────────────────────────────────────────────


def median(values: Sequence[float]) -> float:
    if not values:
        raise ValueError("median of an empty sequence")
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[mid])
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def median_paise(values: Sequence[int]) -> int:
    """Median of money, kept in integer paise.

    An even-length median averages two values; ``//`` would silently round a
    half-paise down every time, biasing every reported median low.
    """
    if not values:
        raise ValueError("median of an empty sequence")
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return round_half_up(ordered[mid - 1] + ordered[mid], 2)


def round_half_up(numerator: int, denominator: int) -> int:
    """Integer division rounding halves away from zero.

    Money never becomes a float, not even transiently for an average
    (SRS-3.10). ``round(a / b)`` would be shorter, would use banker's
    rounding, and would lose exactness past 2⁵³ paise.
    """
    if denominator == 0:
        raise ZeroDivisionError("division by zero in round_half_up")
    if denominator < 0:
        numerator, denominator = -numerator, -denominator
    if numerator >= 0:
        return (2 * numerator + denominator) // (2 * denominator)
    return -((-2 * numerator + denominator) // (2 * denominator))


def mean_paise(values: Sequence[int]) -> int:
    """Arithmetic mean of money, in exact integer paise."""
    if not values:
        raise ValueError("mean of an empty sequence")
    return round_half_up(sum(values), len(values))


# ── Hypothesis tests ────────────────────────────────────────────────────────


def mann_whitney_u(group_a: Sequence[float], group_b: Sequence[float]) -> TestResult:
    """Two-sided Mann–Whitney U via the normal approximation.

    Tie-corrected variance and a continuity correction. Approximate for small
    n; gate G2 (n ≥ 6 per group) keeps it in the range where the
    approximation is serviceable.
    """
    n_a, n_b = len(group_a), len(group_b)
    if n_a == 0 or n_b == 0:
        raise ValueError("Mann-Whitney requires both groups to be non-empty")

    combined = list(group_a) + list(group_b)
    ranks = rank(combined)
    rank_sum_a = sum(ranks[:n_a])

    u_a = rank_sum_a - n_a * (n_a + 1) / 2.0
    u_b = n_a * n_b - u_a
    u = min(u_a, u_b)

    total = n_a + n_b
    mean_u = n_a * n_b / 2.0
    tie_term = _tie_correction(combined)
    variance = (n_a * n_b / (total * (total - 1.0))) * (
        (total**3 - total - tie_term) / 12.0
    )

    if variance <= 0:
        # Every observation identical — no evidence of a difference.
        return TestResult(test="mann_whitney_u", statistic=u, p_value=1.0, n=total)

    z = (u - mean_u + 0.5) / math.sqrt(variance)
    p_value = min(1.0, 2.0 * normal_sf(abs(z)))
    return TestResult(test="mann_whitney_u", statistic=u, p_value=p_value, n=total)


def spearman(xs: Sequence[float], ys: Sequence[float]) -> TestResult:
    """Two-sided Spearman rank correlation.

    p-value from the Fisher z transform, which needs n ≥ 4 and is a normal
    approximation. The statistic reported is ρ itself.
    """
    if len(xs) != len(ys):
        raise ValueError("spearman requires paired sequences")
    n = len(xs)
    if n < 4:
        raise ValueError("spearman requires at least 4 pairs")

    rank_x, rank_y = rank(xs), rank(ys)
    mean_x = sum(rank_x) / n
    mean_y = sum(rank_y) / n

    covariance = sum((a - mean_x) * (b - mean_y) for a, b in zip(rank_x, rank_y))
    variance_x = sum((a - mean_x) ** 2 for a in rank_x)
    variance_y = sum((b - mean_y) ** 2 for b in rank_y)

    if variance_x <= 0 or variance_y <= 0:
        # One side is constant — correlation is undefined, not zero-with-evidence.
        return TestResult(test="spearman", statistic=0.0, p_value=1.0, n=n)

    rho = covariance / math.sqrt(variance_x * variance_y)
    rho = max(-1.0, min(1.0, rho))

    if abs(rho) >= 1.0:
        return TestResult(test="spearman", statistic=rho, p_value=0.0, n=n)

    z = math.sqrt((n - 3) / 1.06) * math.atanh(rho)
    p_value = min(1.0, 2.0 * normal_sf(abs(z)))
    return TestResult(test="spearman", statistic=rho, p_value=p_value, n=n)


def kruskal_wallis(groups: Sequence[Sequence[float]]) -> TestResult:
    """Kruskal–Wallis H across k groups, tie-corrected.

    p-value from the chi-square approximation with k−1 degrees of freedom.
    Restricted to k ≤ 3 by :func:`chi_square_sf`, which is exactly the range
    ``work_mode`` occupies.
    """
    present = [list(g) for g in groups if len(g) > 0]
    if len(present) < 2:
        raise ValueError("Kruskal-Wallis requires at least two non-empty groups")

    combined = [value for group in present for value in group]
    total = len(combined)
    ranks = rank(combined)

    h = 0.0
    offset = 0
    for group in present:
        size = len(group)
        rank_sum = sum(ranks[offset : offset + size])
        h += (rank_sum**2) / size
        offset += size
    h = 12.0 / (total * (total + 1.0)) * h - 3.0 * (total + 1.0)

    tie_term = _tie_correction(combined)
    divisor = 1.0 - tie_term / (total**3 - total) if total > 1 else 1.0
    if divisor > 0:
        h /= divisor

    h = max(0.0, h)
    p_value = chi_square_sf(h, df=len(present) - 1)
    return TestResult(test="kruskal_wallis", statistic=h, p_value=p_value, n=total)


# ── Multiplicity correction ─────────────────────────────────────────────────


def benjamini_hochberg(p_values: Sequence[float], q: float = 0.10) -> list[float]:
    """Benjamini–Hochberg adjusted p-values (q-values), input order preserved.

    Six habits against fourteen spending categories is roughly ninety
    hypotheses per run. At α = 0.05 and no correction, four or five would clear
    the bar by chance alone — and each would be presented to the user as a
    discovered pattern about their life. This function is what makes gate G5
    possible; ``q`` itself is applied by the caller.
    """
    count = len(p_values)
    if count == 0:
        return []
    if not 0.0 < q <= 1.0:
        raise ValueError("q must be in (0, 1]")

    order = sorted(range(count), key=lambda i: p_values[i])
    adjusted = [0.0] * count
    running_min = 1.0
    # Walk from the largest p-value down, enforcing monotonicity: a q-value
    # may never exceed that of a less significant hypothesis.
    for position in range(count - 1, -1, -1):
        index = order[position]
        candidate = p_values[index] * count / (position + 1)
        running_min = min(running_min, candidate)
        adjusted[index] = min(1.0, running_min)
    return adjusted
