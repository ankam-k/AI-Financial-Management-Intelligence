"""Profile schemas.

The profile carries three kinds of field, and they behave differently on a
partial update:

* **Account settings** — ``display_name``, ``timezone``: NOT NULL. An update
  may omit them; it may not null them.
* **Budget** — ``monthly_budget_paise``: nullable on purpose. ``null`` *clears*
  it (which suppresses budget insights); omitting it leaves it alone. The two
  are different requests, so ``exclude_unset`` (not ``exclude_none``) is what
  separates them.
* **Personalisation** (V1.2, M5) — life-context answers and multi-select
  preferences captured at onboarding. Closed vocabularies
  (``app/domain/preferences.py``); they shape the UI and never reach the
  analysis engine. Members are validated and de-duplicated here.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.enums import Category
from app.domain.preferences import (
    FocusArea,
    HouseholdContext,
    IncomePattern,
    LifeStage,
    WorkContext,
)
from app.models.check_in import CheckIn
from app.models.user import User
from app.schemas.common import DisplayName, TimezoneName

#: Columns that are NOT NULL. An update may omit them; it may not null them.
_NON_NULLABLE = {"display_name", "timezone"}

#: The valid ``tracked_habits`` members — the six check-in habit fields, from a
#: single source of truth so this never drifts from the schema.
_HABIT_FIELDS = frozenset(CheckIn.HABIT_FIELDS)

#: NOT NULL JSON columns: an empty list is their "nothing selected" value, so a
#: client-sent ``null`` is stored as ``[]`` rather than violating NOT NULL.
_LIST_FIELDS = ("focus_areas", "tracked_categories", "tracked_habits")


def _dedupe(values: list | None) -> list | None:
    """Drop duplicates while preserving first-seen order. ``None`` passes through."""
    if values is None:
        return None
    seen: list = []
    for value in values:
        if value not in seen:
            seen.append(value)
    return seen


class _Personalisation(BaseModel):
    """The onboarding / personalisation fields, shared by update and onboarding.

    Every field is optional so a partial edit — or a skipped onboarding step —
    is expressible. A sent ``null`` clears a scalar; a sent ``null`` or ``[]``
    empties a list; an omitted field is left untouched.
    """

    model_config = ConfigDict(extra="forbid")

    life_stage: LifeStage | None = None
    income_pattern: IncomePattern | None = None
    work_context: WorkContext | None = None
    household_context: HouseholdContext | None = None
    focus_areas: list[FocusArea] | None = None
    tracked_categories: list[Category] | None = None
    tracked_habits: list[str] | None = None

    @field_validator("focus_areas", "tracked_categories", "tracked_habits")
    @classmethod
    def _no_duplicates(cls, values: list | None) -> list | None:
        return _dedupe(values)

    @field_validator("tracked_habits")
    @classmethod
    def _known_habits(cls, values: list[str] | None) -> list[str] | None:
        if values is None:
            return None
        unknown = [v for v in values if v not in _HABIT_FIELDS]
        if unknown:
            raise ValueError(
                f"unknown habit(s): {unknown}. "
                f"valid habits are {sorted(_HABIT_FIELDS)}"
            )
        return values

    def to_column_updates(self) -> dict[str, object]:
        """Only the fields the client actually sent, mapped onto columns.

        ``mode='json'`` renders enum members as their string values (what the
        columns store); ``exclude_unset`` keeps "leave alone" distinct from
        "clear". A ``null`` for a NOT NULL list column becomes ``[]``.
        """
        updates = self.model_dump(mode="json", exclude_unset=True)
        for name in _LIST_FIELDS:
            if name in updates and updates[name] is None:
                updates[name] = []
        return updates


class ProfileUpdate(_Personalisation):
    """Partial update of the profile. Omitted fields are left untouched.

    Covers account settings, the budget, and personalisation in one PATCH — the
    Settings page edits any subset of them.
    """

    display_name: DisplayName | None = None
    timezone: TimezoneName | None = None
    #: Sent as null to clear the budget, which suppresses budget insights.
    monthly_budget_paise: int | None = Field(
        default=None, gt=0, description="Monthly budget in paise. Null clears it."
    )

    @model_validator(mode="after")
    def _reject_explicit_nulls(self) -> "ProfileUpdate":
        for name in self.model_fields_set & _NON_NULLABLE:
            if getattr(self, name) is None:
                raise ValueError(f"'{name}' cannot be set to null")
        return self


class OnboardingSubmit(_Personalisation):
    """The onboarding payload.

    Just the personalisation fields — submitting it records the answers and
    marks the account onboarded (``onboarding_completed = True``), even when the
    user skipped every question. Onboarding sets expectations and captures
    preferences; it never *gates* the product, so an empty submission is valid.
    """


class ProfileRead(BaseModel):
    """The profile as returned to the client."""

    id: str
    display_name: str
    timezone: str
    currency: str
    monthly_budget_paise: int | None
    onboarding_completed: bool
    life_stage: str | None
    income_pattern: str | None
    work_context: str | None
    household_context: str | None
    focus_areas: list[str]
    tracked_categories: list[str]
    tracked_habits: list[str]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, user: User) -> "ProfileRead":
        return cls(
            id=user.id,
            display_name=user.display_name,
            timezone=user.timezone,
            currency=user.currency,
            monthly_budget_paise=user.monthly_budget_paise,
            onboarding_completed=user.onboarding_completed,
            life_stage=user.life_stage,
            income_pattern=user.income_pattern,
            work_context=user.work_context,
            household_context=user.household_context,
            focus_areas=list(user.focus_areas or []),
            tracked_categories=list(user.tracked_categories or []),
            tracked_habits=list(user.tracked_habits or []),
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
