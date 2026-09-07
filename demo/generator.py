"""Deterministic generation of the demo dataset.

Pure: no database, no clock. It takes a seed and a reference date and returns
plain records. Everything about the output is a function of those two inputs,
which is what lets ``tests/demo/`` run the real analysis engine over generated
data and assert the planted patterns survive every gate.

The planted patterns are created as **weekly budgets**, then distributed into
individual transactions. Planting an effect per-transaction and hoping it
survives weekly aggregation is how a synthetic dataset ends up not
demonstrating the thing it was built for.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, timedelta

from app.demo.design import (
    CATEGORY_SPECS,
    CHECK_IN_SKIP_RATE,
    DEMO_DAYS,
    DEMO_SEED,
    EVENTS,
    FOOD_WEEKLY_WITH_EXERCISE,
    FOOD_WEEKLY_WITHOUT_EXERCISE,
    PERSONA,
    PHASES,
    RECURRING,
    SLEEP_MINUTES_BEST,
    SLEEP_MINUTES_WORST,
    TRANSPORT_WEEKLY_AT_BEST_SLEEP,
    TRANSPORT_WEEKLY_AT_WORST_SLEEP,
    CategorySpec,
    DemoPersona,
)
from app.domain.enums import Category, EventType, PaymentMethod, WorkMode


@dataclass(frozen=True, slots=True)
class ExpenseSeed:
    expense_date: date
    amount_paise: int
    category: Category
    payment_method: PaymentMethod
    merchant: str | None
    notes: str | None = None


@dataclass(frozen=True, slots=True)
class CheckInSeed:
    log_date: date
    sleep_minutes: int | None
    exercise: bool | None
    home_cooked_meals: int | None
    stress_level: int | None
    alcohol: bool | None
    work_mode: WorkMode | None


@dataclass(frozen=True, slots=True)
class EventSeed:
    event_type: EventType
    title: str
    start_date: date
    end_date: date | None
    notes: str | None


@dataclass(frozen=True, slots=True)
class DemoDataset:
    persona: DemoPersona
    start_date: date
    end_date: date
    expenses: tuple[ExpenseSeed, ...] = ()
    check_ins: tuple[CheckInSeed, ...] = ()
    events: tuple[EventSeed, ...] = ()
    #: What was planted, for the CLI to report and tests to assert against.
    manifest: dict[str, object] = field(default_factory=dict)


def _week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


def _jitter(rng: random.Random, amount: int, variability: float) -> int:
    """Multiplicative noise, floored so nothing becomes a zero-rupee expense."""
    factor = 1.0 + rng.gauss(0, variability)
    return max(1_500, int(amount * max(0.35, min(1.9, factor))))


def _split(rng: random.Random, total: int, parts: int) -> list[int]:
    """Break a weekly total into ``parts`` transactions that sum to it exactly.

    Exact, not approximate: the weekly figure is the planted signal, and a
    rounding drift of a few hundred rupees per week is enough to blunt it.
    """
    if parts <= 1:
        return [total]
    cuts = sorted(rng.uniform(0.35, 1.0) for _ in range(parts))
    scale = sum(cuts)
    amounts = [max(1_500, int(total * cut / scale)) for cut in cuts]
    amounts[-1] += total - sum(amounts)
    return [max(1_500, amount) for amount in amounts]


def _weekday_weights(rng: random.Random, days: list[date], count: int) -> list[date]:
    """Pick transaction days, weighted towards the weekend."""
    weights = [2.4 if day.weekday() >= 5 else 1.0 for day in days]
    return rng.choices(days, weights=weights, k=count)


def generate(
    reference_date: date,
    *,
    seed: int = DEMO_SEED,
    days: int = DEMO_DAYS,
    persona: DemoPersona = PERSONA,
) -> DemoDataset:
    """Build the dataset ending on ``reference_date``.

    Same seed and same reference date produce byte-identical output.
    """
    rng = random.Random(seed)

    end = reference_date
    start = _week_start(end - timedelta(days=days - 1))
    total_weeks = ((end - start).days // 7) + 1

    expenses: list[ExpenseSeed] = []
    check_ins: list[CheckInSeed] = []

    # ── Habit phases, anchored to the END of the window ─────────────────────
    #
    # PHASES is declared most-recent-first and laid down backwards, so the
    # last twelve complete weeks always hold six exercise weeks and six rest
    # weeks whatever the reference date. Tiling forward from the start leaves
    # that to chance, and gate G2 needs ≥ 6 in each group — an off-by-one here
    # silently removes the product's headline pattern from the default window.
    recent_first: list[tuple[str, float, int, float]] = []
    index = 0
    while len(recent_first) < total_weeks:
        phase = PHASES[index % len(PHASES)]
        for _ in range(phase.weeks):
            if len(recent_first) >= total_weeks:
                break
            recent_first.append(
                (phase.label, phase.exercise_rate, phase.sleep_minutes, phase.home_cooked)
            )
        index += 1

    chronological = list(reversed(recent_first))
    phase_by_week = [item[0] for item in chronological]
    exercise_rate_by_week = [item[1] for item in chronological]
    sleep_by_week = [item[2] for item in chronological]
    home_cooked_by_week = [item[3] for item in chronological]

    # ── Check-ins ───────────────────────────────────────────────────────────
    weekly_exercise_any: list[bool] = []
    weekly_sleep_mean: list[float] = []

    for week in range(total_weeks):
        monday = start + timedelta(days=week * 7)
        exercised_this_week = False
        sleep_values: list[int] = []

        for offset in range(7):
            day = monday + timedelta(days=offset)
            if day > end:
                break

            if rng.random() < CHECK_IN_SKIP_RATE:
                continue  # a day with no check-in at all — UNKNOWN, not zero

            exercise = rng.random() < exercise_rate_by_week[week]
            # Rest days on the weekend even inside a consistent phase.
            if day.weekday() == 6 and rng.random() < 0.5:
                exercise = False
            exercised_this_week = exercised_this_week or exercise

            sleep = int(rng.gauss(sleep_by_week[week], 26))
            sleep = max(300, min(540, sleep))
            sleep_values.append(sleep)

            check_ins.append(
                CheckInSeed(
                    log_date=day,
                    sleep_minutes=sleep,
                    exercise=exercise,
                    home_cooked_meals=max(
                        0, min(3, int(round(rng.gauss(home_cooked_by_week[week], 0.7))))
                    ),
                    stress_level=rng.choice([1, 2, 2, 3, 3, 4, 5]),
                    # ── Negative controls: independent of everything ────────
                    alcohol=rng.random() < 0.18,
                    work_mode=(
                        WorkMode.LEAVE
                        if day.weekday() >= 5
                        else rng.choice([WorkMode.OFFICE, WorkMode.REMOTE, WorkMode.REMOTE])
                    ),
                )
            )

        weekly_exercise_any.append(exercised_this_week)
        weekly_sleep_mean.append(
            sum(sleep_values) / len(sleep_values) if sleep_values else sleep_by_week[week]
        )

    # ── Spending ────────────────────────────────────────────────────────────
    specs_by_category = {spec.category: spec for spec in CATEGORY_SPECS}

    for week in range(total_weeks):
        monday = start + timedelta(days=week * 7)
        week_days = [monday + timedelta(days=n) for n in range(7)]
        week_days = [day for day in week_days if start <= day <= end]
        if not week_days:
            continue

        # Planted pattern 1: exercise → food.
        food_weekly = (
            FOOD_WEEKLY_WITH_EXERCISE
            if weekly_exercise_any[week]
            else FOOD_WEEKLY_WITHOUT_EXERCISE
        )
        # Planted pattern 2: sleep → transport, monotonic.
        span = SLEEP_MINUTES_BEST - SLEEP_MINUTES_WORST
        position = (weekly_sleep_mean[week] - SLEEP_MINUTES_WORST) / span
        position = max(0.0, min(1.0, position))
        transport_weekly = int(
            TRANSPORT_WEEKLY_AT_WORST_SLEEP
            + position * (TRANSPORT_WEEKLY_AT_BEST_SLEEP - TRANSPORT_WEEKLY_AT_WORST_SLEEP)
        )

        for spec in CATEGORY_SPECS:
            if spec.category is Category.FOOD_DINING:
                weekly = _jitter(rng, food_weekly, spec.variability)
            elif spec.category is Category.TRANSPORT:
                weekly = _jitter(rng, transport_weekly, spec.variability)
            else:
                weekly = _jitter(rng, spec.weekly_paise, spec.variability)

            count = max(1, min(len(week_days), spec.frequency))
            for day, amount in zip(
                _weekday_weights(rng, week_days, count), _split(rng, weekly, count)
            ):
                expenses.append(
                    ExpenseSeed(
                        expense_date=day,
                        amount_paise=amount,
                        category=spec.category,
                        payment_method=rng.choice(spec.methods),
                        merchant=rng.choice(spec.merchants),
                    )
                )

    # ── Recurring charges ───────────────────────────────────────────────────
    cursor = date(start.year, start.month, 1)
    while cursor <= end:
        for recurring in RECURRING:
            try:
                day = cursor.replace(day=recurring.day_of_month)
            except ValueError:  # pragma: no cover - day 29-31 in a short month
                continue
            if start <= day <= end:
                expenses.append(
                    ExpenseSeed(
                        expense_date=day,
                        amount_paise=recurring.amount_paise,
                        category=recurring.category,
                        payment_method=recurring.method,
                        merchant=recurring.merchant,
                    )
                )
        cursor = date(cursor.year + (cursor.month // 12), (cursor.month % 12) + 1, 1)

    # ── Life events, with the spending that goes with them ──────────────────
    events: list[EventSeed] = []
    for spec in EVENTS:
        event_start = end - timedelta(days=spec.starts_days_ago)
        if event_start < start:
            continue
        event_end = (
            event_start + timedelta(days=spec.length_days - 1) if spec.length_days else None
        )
        events.append(
            EventSeed(
                event_type=spec.event_type,
                title=spec.title,
                start_date=event_start,
                end_date=event_end,
                notes=spec.notes,
            )
        )

        covered = [
            event_start + timedelta(days=n) for n in range(spec.length_days or 1)
        ]
        covered = [day for day in covered if start <= day <= end]
        for category, surcharge in spec.surcharge.items():
            spec_for = specs_by_category.get(category)
            merchants = (
                spec_for.merchants
                if spec_for
                else ("MakeMyTrip", "IndiGo", "Myntra", "Amazon")
            )
            count = max(1, min(len(covered), 3))
            for day, amount in zip(
                rng.choices(covered, k=count), _split(rng, surcharge, count)
            ):
                expenses.append(
                    ExpenseSeed(
                        expense_date=day,
                        amount_paise=amount,
                        category=category,
                        payment_method=PaymentMethod.CREDIT_CARD,
                        merchant=rng.choice(merchants),
                        notes=spec.title,
                    )
                )

    expenses.sort(key=lambda item: (item.expense_date, item.category.value, item.amount_paise))
    check_ins.sort(key=lambda item: item.log_date)
    events.sort(key=lambda item: item.start_date)

    return DemoDataset(
        persona=persona,
        start_date=start,
        end_date=end,
        expenses=tuple(expenses),
        check_ins=tuple(check_ins),
        events=tuple(events),
        manifest={
            "seed": seed,
            "reference_date": end.isoformat(),
            "weeks": total_weeks,
            "expense_count": len(expenses),
            "check_in_count": len(check_ins),
            "event_count": len(events),
            "exercise_weeks": sum(weekly_exercise_any),
            "non_exercise_weeks": total_weeks - sum(weekly_exercise_any),
            "phases": phase_by_week,
        },
    )
