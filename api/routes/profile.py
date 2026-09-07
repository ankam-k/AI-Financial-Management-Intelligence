"""Profile endpoints."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, ProfileServiceDep
from app.schemas.profile import OnboardingSubmit, ProfileRead, ProfileUpdate

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("", response_model=ProfileRead, summary="Get the local profile")
def read_profile(user: CurrentUser) -> ProfileRead:
    """Return the profile, including onboarding state and personalisation."""
    return ProfileRead.from_model(user)


@router.patch("", response_model=ProfileRead, summary="Update the local profile")
def update_profile(
    payload: ProfileUpdate, user: CurrentUser, profiles: ProfileServiceDep
) -> ProfileRead:
    """Update settings, the budget, or personalisation. Omitted fields are
    unchanged; the Settings page edits any subset of them."""
    updated = profiles.update(user, payload.to_column_updates())
    return ProfileRead.from_model(updated)


@router.post(
    "/onboarding",
    response_model=ProfileRead,
    summary="Complete onboarding and record personalisation",
)
def complete_onboarding(
    payload: OnboardingSubmit, user: CurrentUser, profiles: ProfileServiceDep
) -> ProfileRead:
    """Record the onboarding answers and mark the account onboarded.

    The answers are optional — onboarding sets expectations and captures
    preferences, it never gates the product — so an empty submission still
    flips ``onboarding_completed`` to true. These preferences drive UI
    prominence only; they never influence analysis (ADR-007).
    """
    updated = profiles.complete_onboarding(user, payload.to_column_updates())
    return ProfileRead.from_model(updated)


@router.delete(
    "/data",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete all data the account owns (keeps the account)",
)
def delete_all_data(user: CurrentUser, profiles: ProfileServiceDep) -> None:
    """Hard-delete every expense, check-in and event this account owns.

    Deletion is real and cascading — there is no soft-delete flag on user data
    (05_Database_Design.md §8). The **account itself is kept**: the user stays
    signed in and lands on the empty first-run state (Phase 18).
    """
    profiles.delete_all_data(user)
