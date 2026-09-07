"""The dataset design, declared rather than emergent.

Everything the generator is *supposed* to produce is stated here, so the
validation tests can assert against a specification instead of against
whatever the generator happened to do.

## The persona

A 26-year-old software engineer in Bengaluru on ₹1.1L/month take-home, which
is the ``01_Product_Vision.md`` persona. Rent and subscriptions are fixed and
land on the same days each month; food, transport and shopping vary; UPI
dominates because the market is UPI-first.

## Planted patterns

Two associations the engine must find, chosen because they are the ones the
product's own README claims:

| Habit | Category | Test | Shape |
|---|---|---|---|
| ``exercise`` | ``FOOD_DINING`` | Mann–Whitney U | weeks without the gym cost more |
| ``sleep_minutes`` | ``TRANSPORT`` | Spearman ρ | less sleep, more cabs |

Both are generated as *weekly budgets* rather than per-transaction noise,
because the unit of observation is the ISO week — planting an effect at the
transaction level and hoping it survives aggregation is how a synthetic
dataset ends up not demonstrating the thing it was built to demonstrate.

Habits move in **phases**, not alternation. A person has a month where they go
to the gym and a month where they don't; they do not alternate weekly. Phases
also keep ≥ 6 weeks in each group inside a 90-day window, which gate G2
requires.

## Negative controls

``alcohol`` and ``work_mode`` are generated independently of every category.
The engine must find **nothing** in them. This is the primary quality bar
(07_AI_Architecture.md §8): a false positive here would mean the gates do not
work, which matters more than any true positive they let through.

``stress_level`` and ``home_cooked_meals`` are also independent — they exist
to make coverage realistic and to give the hypothesis space its real size.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.enums import Category, EventType, PaymentMethod

#: Fixed. Changing it changes every screenshot and every number in the README.
DEMO_SEED = 20260728

#: Nine months, so a 90-day window is dense and a 180-day window is richer.
DEMO_DAYS = 273


@dataclass(frozen=True, slots=True)
class DemoPersona:
    display_name: str
    monthly_budget_paise: int
    monthly_rent_paise: int


PERSONA = DemoPersona(
    display_name="Pranay",
    # Sized against measured output, not guessed: a typical generated month
    # runs ₹67,000–79,000, and the current month lands just over. A budget
    # card that always reads "within budget" demonstrates nothing, and one
    # reading 210% — which the first draft produced — reads as broken.
    monthly_budget_paise=8_200_000,
    monthly_rent_paise=2_400_000,
)


@dataclass(frozen=True, slots=True)
class PlantedPattern:
    """An association the generator creates and the engine must find."""

    habit: str
    category: Category
    #: Machine name of the test the engine should reach for.
    expected_test: str
    description: str


PLANTED_PATTERNS: tuple[PlantedPattern, ...] = (
    PlantedPattern(
        habit="exercise",
        category=Category.FOOD_DINING,
        expected_test="mann_whitney_u",
        description="Weeks without exercise carry higher food and dining spending.",
    ),
    PlantedPattern(
        habit="sleep_minutes",
        category=Category.TRANSPORT,
        expected_test="spearman",
        description="Shorter sleep goes with more spending on cabs.",
    ),
    PlantedPattern(
        habit="home_cooked_meals",
        category=Category.FOOD_DINING,
        expected_test="spearman",
        description="Weeks with more home cooking carry less takeaway spending.",
    ),
)

#: Habits generated independently of every category. The engine must find
#: nothing in them, and `tests/demo/` asserts exactly that.
NEGATIVE_CONTROLS: tuple[str, ...] = ("alcohol", "work_mode")


# ── Weekly spending model ───────────────────────────────────────────────────

#: Weekly paise for the planted food pattern, by whether the week had exercise.
FOOD_WEEKLY_WITH_EXERCISE = 410_000
FOOD_WEEKLY_WITHOUT_EXERCISE = 620_000

#: Transport responds to sleep. Weekly paise at the two ends of the range.
TRANSPORT_WEEKLY_AT_BEST_SLEEP = 105_000
TRANSPORT_WEEKLY_AT_WORST_SLEEP = 290_000

#: Sleep range in minutes. Wide enough for Spearman to have signal, narrow
#: enough to be a person rather than a test fixture.
SLEEP_MINUTES_BEST = 480
SLEEP_MINUTES_WORST = 330


@dataclass(frozen=True, slots=True)
class CategorySpec:
    """A spending category the generator produces, with its merchants."""

    category: Category
    #: Weekly paise, before noise. Ignored for the planted categories, which
    #: take their weekly total from the pattern.
    weekly_paise: int
    #: Fractional spread applied as noise.
    variability: float
    merchants: tuple[str, ...]
    methods: tuple[PaymentMethod, ...] = (PaymentMethod.UPI,)
    #: Transactions per week, before weekend weighting.
    frequency: int = 3


#: Independent categories — noise only, no habit relationship. Their weekly
#: totals stay stable enough that no spurious effect clears gate G4.
CATEGORY_SPECS: tuple[CategorySpec, ...] = (
    CategorySpec(
        Category.FOOD_DINING,
        weekly_paise=0,  # driven by the planted pattern
        variability=0.10,
        merchants=("Swiggy", "Zomato", "Third Wave Coffee", "Truffles", "Meghana Foods"),
        methods=(PaymentMethod.UPI, PaymentMethod.UPI, PaymentMethod.CREDIT_CARD),
        frequency=5,
    ),
    CategorySpec(
        Category.TRANSPORT,
        weekly_paise=0,  # driven by the planted pattern
        variability=0.12,
        merchants=("Uber", "Ola", "Namma Metro", "Rapido"),
        methods=(PaymentMethod.UPI, PaymentMethod.UPI, PaymentMethod.DEBIT_CARD),
        frequency=4,
    ),
    CategorySpec(
        Category.GROCERIES,
        weekly_paise=190_000,
        variability=0.14,
        merchants=("BigBasket", "Zepto", "More Supermarket", "Blinkit"),
        frequency=2,
    ),
    CategorySpec(
        Category.ENTERTAINMENT,
        weekly_paise=52_000,
        variability=0.22,
        merchants=("BookMyShow", "PVR Cinemas", "Toit"),
        methods=(PaymentMethod.UPI, PaymentMethod.CREDIT_CARD),
        frequency=1,
    ),
    CategorySpec(
        Category.PERSONAL_CARE,
        weekly_paise=34_000,
        variability=0.18,
        merchants=("Nykaa", "Bombay Shaving Company", "Urban Company"),
        frequency=1,
    ),
    CategorySpec(
        Category.HEALTH_FITNESS,
        weekly_paise=41_000,
        variability=0.16,
        merchants=("Cult.fit", "Apollo Pharmacy", "PharmEasy"),
        frequency=1,
    ),
)


@dataclass(frozen=True, slots=True)
class RecurringSpec:
    """A fixed monthly charge, on the same day each month."""

    category: Category
    merchant: str
    amount_paise: int
    day_of_month: int
    method: PaymentMethod = PaymentMethod.BANK


#: Billing days are **deliberately spread across the month**, so no category
#: collapses into "one week has everything, three weeks have nothing".
#:
#: The first version clustered both utility bills into the same week. A
#: category whose weekly series is mostly zeros produces a huge apparent
#: effect under any split, and the engine duly reported a
#: ``home_cooked_meals ↔ UTILITIES`` association at a relative difference of
#: 1.0 — arithmetically correct, and entirely an artefact of the billing
#: calendar. Spreading the days is a fix to the *data*, not to the engine.
RECURRING: tuple[RecurringSpec, ...] = (
    RecurringSpec(Category.RENT_HOUSING, "Landlord", PERSONA.monthly_rent_paise, 3),
    RecurringSpec(Category.UTILITIES, "BESCOM", 178_000, 9, PaymentMethod.UPI),
    RecurringSpec(Category.UTILITIES, "ACT Fibernet", 115_000, 22, PaymentMethod.UPI),
    RecurringSpec(Category.SUBSCRIPTIONS, "Spotify", 11_900, 12, PaymentMethod.CREDIT_CARD),
    RecurringSpec(Category.SUBSCRIPTIONS, "Netflix", 64_900, 18, PaymentMethod.CREDIT_CARD),
    RecurringSpec(Category.SUBSCRIPTIONS, "Cult.fit membership", 189_900, 26, PaymentMethod.CREDIT_CARD),
)


@dataclass(frozen=True, slots=True)
class EventSpec:
    """A life event, placed relative to the end of the window."""

    event_type: EventType
    title: str
    #: Days before the reference date that the event starts.
    starts_days_ago: int
    #: ``None`` for a point event.
    length_days: int | None
    notes: str
    #: Extra spending during the event, by category, as weekly-equivalent paise.
    surcharge: dict[Category, int] = field(default_factory=dict)


EVENTS: tuple[EventSpec, ...] = (
    EventSpec(
        EventType.TRAVEL,
        "Goa trip",
        starts_days_ago=38,
        length_days=5,
        notes="Long weekend with college friends.",
        surcharge={
            Category.TRAVEL: 620_000,
            Category.FOOD_DINING: 180_000,
            Category.ENTERTAINMENT: 90_000,
        },
    ),
    EventSpec(
        EventType.ILLNESS,
        "Down with flu",
        starts_days_ago=96,
        length_days=6,
        notes="Worked from bed most of the week.",
        surcharge={Category.HEALTH_FITNESS: 240_000},
    ),
    # Placed inside the last *complete* month on purpose. The month-over-month
    # card compares complete months only, so an event in the current partial
    # month moves no comparison — the first draft put Diwali there and the
    # card read STABLE at 3%, demonstrating nothing.
    EventSpec(
        EventType.FESTIVAL,
        "Diwali",
        starts_days_ago=45,
        length_days=None,
        notes="Gifts and new clothes.",
        surcharge={Category.SHOPPING: 880_000, Category.FOOD_DINING: 120_000},
    ),
    EventSpec(
        EventType.FAMILY_EVENT,
        "Cousin's wedding",
        starts_days_ago=150,
        length_days=3,
        notes="Travel and a gift.",
        surcharge={Category.SHOPPING: 340_000, Category.TRAVEL: 210_000},
    ),
)


# ── Habit phases ────────────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class Phase:
    """A stretch of weeks with a consistent habit posture."""

    weeks: int
    #: Probability of a gym day within the phase.
    exercise_rate: float
    #: Mean sleep in minutes across the phase.
    sleep_minutes: int
    #: Mean home-cooked meals per day. Moves with the phase: a settled month
    #: is one where you cook, a crunch month is one where you order in.
    home_cooked: float
    label: str


#: **Declared most-recent first, and anchored to the end of the window.**
#:
#: The anchoring matters more than it looks. Tiling phases forward from the
#: start leaves whatever falls in the last twelve weeks to chance — and the
#: first version of this file did exactly that, which put ~5 exercise weeks
#: and ~7 rest weeks in the default 90-day window. Gate G2 needs **≥ 6 in
#: each group**, so the product's headline pattern silently failed to appear
#: in the window the dashboard opens on.
#:
#: Six-week phases anchored to the end guarantee 6 and 6 in the most recent
#: twelve complete weeks, whatever the reference date.
PHASES: tuple[Phase, ...] = (
    Phase(weeks=6, exercise_rate=0.05, sleep_minutes=362, home_cooked=0.6, label="festive slump"),
    Phase(weeks=6, exercise_rate=0.80, sleep_minutes=470, home_cooked=2.3, label="back on track"),
    Phase(weeks=6, exercise_rate=0.06, sleep_minutes=352, home_cooked=0.5, label="release crunch"),
    Phase(weeks=6, exercise_rate=0.78, sleep_minutes=466, home_cooked=2.2, label="settled"),
    Phase(weeks=6, exercise_rate=0.04, sleep_minutes=358, home_cooked=0.7, label="deadline month"),
    Phase(weeks=6, exercise_rate=0.76, sleep_minutes=472, home_cooked=2.4, label="good stretch"),
)

#: Days a check-in is skipped, as a rate. Keeps per-habit coverage above the
#: 60% gate while leaving the missed-days card something to report.
CHECK_IN_SKIP_RATE = 0.14
