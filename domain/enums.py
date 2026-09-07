"""Fixed vocabularies for V1.

These are closed sets on purpose. A free-text category column would make the
analysis engine's hypothesis count unbounded and its multiple-comparison
correction unsizeable (ADR-007). Adding a member is a schema decision, not a
user action.
"""

from __future__ import annotations

from enum import Enum


class Category(str, Enum):
    """The fixed V1 spending taxonomy (05_Database_Design.md §4).

    Sixteen members: fifteen spending categories plus ``UNCATEGORIZED``.
    ``TRANSFERS`` and ``INCOME`` are retained for completeness but are excluded
    from behavioural correlation when the analysis engine lands.
    """

    FOOD_DINING = "FOOD_DINING"
    GROCERIES = "GROCERIES"
    TRANSPORT = "TRANSPORT"
    SHOPPING = "SHOPPING"
    ENTERTAINMENT = "ENTERTAINMENT"
    UTILITIES = "UTILITIES"
    RENT_HOUSING = "RENT_HOUSING"
    HEALTH_FITNESS = "HEALTH_FITNESS"
    EDUCATION = "EDUCATION"
    TRAVEL = "TRAVEL"
    PERSONAL_CARE = "PERSONAL_CARE"
    SUBSCRIPTIONS = "SUBSCRIPTIONS"
    TRANSFERS = "TRANSFERS"
    INCOME = "INCOME"
    FEES_CHARGES = "FEES_CHARGES"
    UNCATEGORIZED = "UNCATEGORIZED"


class PaymentMethod(str, Enum):
    """How the money moved (SRS-3.12).

    ``CASH`` extends the documented instrument list, which was written for
    imported bank statements. V1 is manual entry, where cash spending is real
    and would otherwise be unrecordable.
    """

    UPI = "UPI"
    CASH = "CASH"
    DEBIT_CARD = "DEBIT_CARD"
    CREDIT_CARD = "CREDIT_CARD"
    BANK = "BANK"
    WALLET = "WALLET"


class WorkMode(str, Enum):
    """Where the user worked on a given day."""

    OFFICE = "OFFICE"
    REMOTE = "REMOTE"
    LEAVE = "LEAVE"


class EventType(str, Enum):
    """Life event taxonomy (SRS-5.9)."""

    TRAVEL = "TRAVEL"
    ILLNESS = "ILLNESS"
    JOB_CHANGE = "JOB_CHANGE"
    RELOCATION = "RELOCATION"
    FESTIVAL = "FESTIVAL"
    FAMILY_EVENT = "FAMILY_EVENT"
    OTHER = "OTHER"
