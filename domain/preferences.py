"""Closed vocabularies for onboarding and personalisation (V1.2, M5).

These describe *who the user is* and *what they want to pay attention to*. They
exist to **shape the UI** — which categories a check-in surfaces first, which
insight themes lead the dashboard, how onboarding introduces the product — and
for **nothing else**.

    A preference here NEVER enters the analysis engine.

That is a hard boundary, and it is structural rather than remembered: the engine
receives a plain dataset built from expenses, check-ins and life events
(``app/services/analysis_service.py``), never the ``User`` row, so a
personalisation field has no path into a statistical threshold, a gate, or a
hypothesis. The five gates (ADR-007) are the same for every user regardless of
what they selected here. ``tests/test_profile.py`` asserts the engine's source
never even mentions these fields.

Why closed sets, like the rest of the domain vocabulary (``enums.py``): a
personalisation field drives branching in the UI, and a bounded set keeps that
branching enumerable and testable. Adding a member is a schema decision, not a
free-text user action. These are deliberately coarse — enough to personalise,
not so fine that they become a survey.
"""

from __future__ import annotations

from enum import Enum


class LifeStage(str, Enum):
    """Roughly where the user is in life. Personalises copy and defaults only."""

    STUDENT = "STUDENT"
    EARLY_CAREER = "EARLY_CAREER"
    ESTABLISHED = "ESTABLISHED"
    FAMILY = "FAMILY"


class IncomePattern(str, Enum):
    """How income tends to arrive. Used to frame spending, never to predict it."""

    SALARIED_FIXED = "SALARIED_FIXED"
    SALARIED_VARIABLE = "SALARIED_VARIABLE"
    SELF_EMPLOYED = "SELF_EMPLOYED"
    IRREGULAR = "IRREGULAR"


class WorkContext(str, Enum):
    """The user's usual working arrangement.

    Distinct from :class:`app.domain.enums.WorkMode`, which is a *daily* fact
    recorded on a check-in. This is a stable preference set once at onboarding.
    """

    OFFICE = "OFFICE"
    REMOTE = "REMOTE"
    HYBRID = "HYBRID"
    FIELD = "FIELD"


class HouseholdContext(str, Enum):
    """Who the user shares expenses and daily life with."""

    LIVING_ALONE = "LIVING_ALONE"
    WITH_FAMILY = "WITH_FAMILY"
    WITH_PARTNER = "WITH_PARTNER"
    SHARED = "SHARED"


class FocusArea(str, Enum):
    """What the user says they want the product to help with.

    Coarse themes, not categories or habits — those are chosen separately
    (``tracked_categories`` / ``tracked_habits``). A focus area only changes
    which cards lead and which language onboarding uses.
    """

    UNDERSTAND_SPENDING = "UNDERSTAND_SPENDING"
    BUILD_HEALTHY_HABITS = "BUILD_HEALTHY_HABITS"
    REDUCE_STRESS_SPENDING = "REDUCE_STRESS_SPENDING"
    SAVE_MORE = "SAVE_MORE"
