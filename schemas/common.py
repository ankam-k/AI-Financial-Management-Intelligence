"""Shared field types.

Whitespace is stripped *before* the length check, so ``"   "`` fails
``min_length=1`` rather than passing validation and reaching a NOT NULL column
as an empty string. Normalising input is the schema layer's job; doing it in
each service instead is how the two drift apart.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import StringConstraints


def trimmed(max_length: int, *, min_length: int = 1) -> object:
    """A required string, whitespace-stripped and length-bounded."""
    return Annotated[
        str,
        StringConstraints(
            strip_whitespace=True, min_length=min_length, max_length=max_length
        ),
    ]


#: Concrete aliases, so a column's limit is declared in exactly one place.
DisplayName = trimmed(120)
TimezoneName = trimmed(64)
EventTitle = trimmed(200)
