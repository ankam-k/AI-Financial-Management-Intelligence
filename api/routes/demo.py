"""Demo-mode endpoints.

The same three operations the CLI offers, exposed so a demo can be loaded from
the UI without dropping to a terminal mid-interview.

**These are destructive and gated.** `AFI_DEMO_MODE` defaults to **off**: the
routes wipe and replace all data with no authentication, so the safe default is
disabled. Enable it explicitly (`AFI_DEMO_MODE=true`) for a local demo — the
single-local-profile assumption (ADR-014) is what makes that opt-in acceptable.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter

from app.api.deps import ClockDep, SessionDep
from app.core.config import settings
from app.demo.design import DEMO_DAYS, DEMO_SEED, NEGATIVE_CONTROLS, PLANTED_PATTERNS
from app.demo.generator import generate
from app.demo.loader import clear_demo_data, describe, load_demo_data
from app.domain.errors import ValidationError
from app.schemas.demo import DemoDesignRead, DemoStatusRead

router = APIRouter(prefix="/api/demo", tags=["demo"])


def _require_enabled() -> None:
    if not settings.demo_mode:
        raise ValidationError(
            "Demo mode is disabled. Set AFI_DEMO_MODE=true to enable seeding, "
            "or use the CLI: python -m app.demo seed"
        )


@router.get("/status", response_model=DemoStatusRead, summary="What is loaded")
def read_status(session: SessionDep) -> DemoStatusRead:
    """Non-destructive, and available whether or not demo mode is on."""
    return DemoStatusRead.from_domain(describe(session), enabled=settings.demo_mode)


@router.get("/design", response_model=DemoDesignRead, summary="What the dataset plants")
def read_design() -> DemoDesignRead:
    """The declared design: persona, planted patterns, negative controls.

    Exposed so a reviewer can check that the associations on screen are the
    ones the generator set out to create, rather than taking it on trust.
    """
    return DemoDesignRead(
        seed=DEMO_SEED,
        days=DEMO_DAYS,
        planted_patterns=[
            {
                "habit": pattern.habit,
                "category": pattern.category.value,
                "expected_test": pattern.expected_test,
                "description": pattern.description,
            }
            for pattern in PLANTED_PATTERNS
        ],
        negative_controls=list(NEGATIVE_CONTROLS),
    )


@router.post("/seed", response_model=DemoStatusRead, summary="Load the demo dataset")
def seed(session: SessionDep, clock: ClockDep, reference_date: date | None = None) -> DemoStatusRead:
    """Replace whatever is loaded with the demo dataset.

    Idempotent: it clears first, so seeding twice leaves one dataset rather
    than two overlapping ones that would double every total.
    """
    _require_enabled()
    dataset = generate(reference_date or clock.today())
    status = load_demo_data(session, dataset)
    return DemoStatusRead.from_domain(status, enabled=True)


@router.delete("", response_model=DemoStatusRead, summary="Clear every record")
def clear(session: SessionDep) -> DemoStatusRead:
    """Remove every expense, check-in and event. The profile itself is kept."""
    _require_enabled()
    return DemoStatusRead.from_domain(clear_demo_data(session), enabled=True)
