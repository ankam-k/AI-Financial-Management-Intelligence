r"""What the model is allowed to see, and the numbers it is held to.

Two jobs, deliberately in one file because they must not drift apart:

1. **Build the payload.** Only the structured insight — never a transaction
   list, never the ledger, never a database handle (SRS-7.2). Long arrays are
   truncated: a 90-day daily series is thousands of tokens the model cannot
   use in three sentences of prose.

2. **Build the allowed-number set.** Every numeric literal the generated text
   may legitimately contain, in every formatting the model might reasonably
   choose. ``412000`` paise licenses ``4120``, ``4120.00`` and ``4,120``;
   a ratio of ``0.4939`` licenses ``49.39``, ``49.4`` and ``49``.

The set is built from the **trimmed** payload, not the full insight. The model
may only cite what it was actually given — a number that was truncated away is
a number it cannot have read, and citing it would be a fabrication that
happened to be true.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any, Mapping

from app.analysis.models import Insight

#: Arrays longer than this are truncated before the model sees them.
MAX_ARRAY_ITEMS = 6

#: Metric keys whose values are money, in integer paise.
_MONEY_SUFFIX = "_paise"

#: Metric keys whose values are fractions that a reader will see as percents.
_RATIO_KEYS = frozenset(
    {
        "coverage_ratio",
        "completion_ratio",
        "frequency_ratio",
        "missed_ratio",
        "share_ratio",
        "utilization_ratio",
        "relative_change",
        "relative_difference",
        "average_habit_coverage_ratio",
        "top_category_share_ratio",
        "min_coverage_ratio",
        "min_relative_effect",
        "near_limit_threshold",
        "stable_band",
        "current_value",
        "required_value",
    }
)

#: Matches 1,234.56 · 1234.56 · 1234 — the shapes a model writes money in.
_NUMBER_PATTERN = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?")


def canonical(text: str) -> str:
    """Reduce a numeric literal to a comparable form.

    ``"4,120.00"``, ``"4120.0"`` and ``"4120"`` all become ``"4120"``, so a
    formatting choice by the model is never mistaken for a fabrication.
    """
    cleaned = text.replace(",", "").strip()
    if "." in cleaned:
        cleaned = cleaned.rstrip("0").rstrip(".")
    return cleaned or "0"


def _add(allowed: set[str], value: Any) -> None:
    if isinstance(value, (int, float, Decimal)) and not isinstance(value, bool):
        allowed.add(canonical(f"{value:.6f}" if isinstance(value, float) else str(value)))


def _license_number(allowed: set[str], key: str, value: float | int) -> None:
    """Register every representation a reader could reasonably see."""
    _add(allowed, value)

    if key.endswith(_MONEY_SUFFIX) and isinstance(value, int):
        rupees = Decimal(abs(value)) / 100
        allowed.add(canonical(f"{rupees:.2f}"))
        allowed.add(canonical(f"{rupees:.0f}"))
        # Rounded to the nearest hundred/thousand rupees, which is how a
        # person actually says an amount out loud.
        allowed.add(canonical(f"{round(float(rupees), -2):.0f}"))
        allowed.add(canonical(f"{round(float(rupees) / 1000, 1)}"))
        return

    if key in _RATIO_KEYS and isinstance(value, (int, float)):
        percent = abs(float(value)) * 100
        for places in (2, 1, 0):
            allowed.add(canonical(f"{percent:.{places}f}"))
        return

    if isinstance(value, float):
        # p-values, q-values, statistics: allow a few sensible roundings.
        for places in (6, 4, 3, 2, 1):
            allowed.add(canonical(f"{abs(value):.{places}f}"))


def _walk(node: Any, key: str, allowed: set[str]) -> None:
    if isinstance(node, Mapping):
        for child_key, child in node.items():
            _walk(child, str(child_key), allowed)
    elif isinstance(node, (list, tuple)):
        for child in node:
            _walk(child, key, allowed)
    elif isinstance(node, bool):
        return
    elif isinstance(node, (int, float, Decimal)):
        _license_number(allowed, key, node)
    elif isinstance(node, str):
        # ISO dates and week keys carry digits a narration will quote back.
        for match in _NUMBER_PATTERN.findall(node):
            allowed.add(canonical(match))


def _trim(node: Any) -> Any:
    """Shorten long arrays so the payload stays a prompt, not a dataset."""
    if isinstance(node, Mapping):
        return {key: _trim(value) for key, value in node.items()}
    if isinstance(node, (list, tuple)):
        items = [_trim(item) for item in node[:MAX_ARRAY_ITEMS]]
        if len(node) > MAX_ARRAY_ITEMS:
            items.append(f"... {len(node) - MAX_ARRAY_ITEMS} more omitted")
        return items
    return node


def build_payload(insight: Insight) -> dict[str, Any]:
    """The exact object handed to the model.

    No database handle, no transaction list, no ledger — only the finished
    insight (SRS-7.2). Evidence is summarised rather than passed whole:
    record ids are opaque to a model and would only spend tokens.
    """
    return {
        "insight_type": insight.type.value,
        "tier": insight.tier.value,
        "subject": insight.subject,
        "window": insight.window.as_dict(),
        "metrics": _trim(dict(insight.metrics)),
        "evidence": [
            {"kind": item.kind.value, "label": item.label, "detail": _trim(dict(item.payload))}
            for item in insight.evidence[:MAX_ARRAY_ITEMS]
        ],
        "currency": insight.metrics.get("currency", "INR"),
    }


def allowed_numbers(payload: Mapping[str, Any]) -> frozenset[str]:
    """Every numeric literal the generated text may contain.

    Anything else is a fabrication, and the provenance validator rejects the
    generation that produced it (SRS-7.3).
    """
    allowed: set[str] = set()
    _walk(payload, "", allowed)
    return frozenset(allowed)


def extract_numbers(text: str) -> list[str]:
    """Every numeric literal in generated prose, in canonical form."""
    return [canonical(match) for match in _NUMBER_PATTERN.findall(text)]
