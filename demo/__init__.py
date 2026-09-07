"""Deterministic demo data.

Exists to close OEQ-004. Two approved requirements work against each other:
check-in backfill is capped at 30 days (SRS-5.6/5.7), while a behavioural
association needs ≥ 8 complete weeks of history at ≥ 60% per-habit coverage.
A new user can therefore log at most ~4.3 weeks retroactively, so **no T3
insight is reachable through the public API at all** — not for a new user in
their first month, and not for anyone demonstrating the product.

The fix V1 scope already anticipated (PDR-012, ``datasets/``,
``data_source.is_synthetic``): a synthetic dataset written **below** the API,
where the backfill rule does not apply because no check-in endpoint is
involved. The rule stays intact for real user input; the demo bypasses the
transport, not the schema.

Three properties this generator holds to:

**Deterministic.** Same seed and same reference date produce byte-identical
data. A demo that shifted under you between runs would make every screenshot
and every number in the README a lie by the next morning.

**Planted, not random.** The patterns are declared in ``design.py`` and the
generator is built to produce them. ``tests/demo/`` runs the real analysis
engine over generated data and asserts each planted pattern survives all five
gates — so "the demo shows a correlation" is a test result, not a hope.

**Carries negative controls.** ``alcohol`` and ``work_mode`` are generated
independently of every spending category (07_AI_Architecture.md §8). The
primary quality bar is **zero T3 insights from them**: a generator that
manufactured a pattern everywhere would prove the engine detects noise, which
is the opposite of the claim being made.
"""

from app.demo.design import (
    DEMO_SEED,
    NEGATIVE_CONTROLS,
    PLANTED_PATTERNS,
    PERSONA,
    DemoPersona,
    PlantedPattern,
)
from app.demo.generator import DemoDataset, generate
from app.demo.loader import DemoStatus, clear_demo_data, describe, load_demo_data

__all__ = [
    "DEMO_SEED",
    "DemoDataset",
    "DemoPersona",
    "DemoStatus",
    "NEGATIVE_CONTROLS",
    "PERSONA",
    "PLANTED_PATTERNS",
    "PlantedPattern",
    "clear_demo_data",
    "describe",
    "generate",
    "load_demo_data",
]
