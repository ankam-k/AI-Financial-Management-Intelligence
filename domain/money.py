"""Money handling (ADR-003, SRS-3.10).

**Money is an integer number of paise. There is no float anywhere in its
lifecycle** — not in the column, not in the Pydantic model, not in the
formatter below. ``0.1 + 0.2 != 0.3`` is a bug the analysis engine cannot
afford, because a rupee of drift in an aggregate becomes a false claim in an
insight the user is invited to check.

Rupees exist only as a *display* concern, produced here by integer division.
"""

from __future__ import annotations

PAISE_PER_RUPEE = 100


def format_paise(paise: int) -> str:
    """Render paise as a plain decimal rupee string, e.g. ``"4120.50"``.

    Integer arithmetic only. ``float(paise) / 100`` would be shorter and would
    round wrongly for large values.

    >>> format_paise(412050)
    '4120.50'
    >>> format_paise(-5)
    '-0.05'
    """
    sign = "-" if paise < 0 else ""
    magnitude = abs(paise)
    return f"{sign}{magnitude // PAISE_PER_RUPEE}.{magnitude % PAISE_PER_RUPEE:02d}"


def rupees_to_paise(rupees: int) -> int:
    """Convert whole rupees to paise. Convenience for fixtures and seeds."""
    return rupees * PAISE_PER_RUPEE
