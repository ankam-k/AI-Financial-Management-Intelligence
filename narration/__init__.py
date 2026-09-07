"""Narration — turning finished insights into explanations.

The layer the governing principle names: *the analysis engine is the source of
truth, the LLM is a renderer of truth already established* (PDR-031).

Nothing here computes a financial figure. Every number that reaches a user was
fixed by ``app/analysis/`` before this package ran, which is what makes the
provenance validator possible: it has an authoritative set to check generated
prose against.

This package performs no I/O. The model client is injected through the
``LLMClient`` protocol, so the prompt builder, the validators and the template
renderer are all testable without a model — and the product runs without one.
"""

from app.narration.models import (
    Narration,
    NarrationRun,
    NarrationSource,
    ValidationFailure,
)
from app.narration.payload import allowed_numbers, build_payload
from app.narration.prompts import OUTPUT_SCHEMA, build_prompt
from app.narration.renderer import NarrationRenderer
from app.narration.validators import validate

__all__ = [
    "Narration",
    "NarrationRenderer",
    "NarrationRun",
    "NarrationSource",
    "OUTPUT_SCHEMA",
    "ValidationFailure",
    "allowed_numbers",
    "build_payload",
    "build_prompt",
    "validate",
]
