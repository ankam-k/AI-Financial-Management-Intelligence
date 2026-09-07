"""Authentication schemas.

Email is validated with a deliberately small regex rather than Pydantic's
``EmailStr``, which would pull in the ``email-validator`` package. V1.2 keeps
the dependency footprint to the two auth libraries ADR-011 actually needs; a
pragmatic "something@something.tld" check is enough to reject obvious garbage
at the edge, and the real uniqueness guarantee lives in the database.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.user import User
from app.schemas.common import DisplayName

#: Pragmatic email shape: non-space local part, "@", a dotted domain. Not RFC
#: 5322 — it is a sanity gate, not an authority on deliverability.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

#: Passwords are length-bounded only. A minimum keeps out the trivially weak;
#: the maximum is a denial-of-service guard — Argon2id hashing a megabyte-long
#: "password" is real CPU. No composition rules: length beats character classes.
Password = Annotated[str, Field(min_length=8, max_length=200)]


def _normalise_email(value: str) -> str:
    """Lower-case and trim, so ``Foo@Bar.com`` and ``foo@bar.com`` are one."""
    cleaned = value.strip().lower()
    if not _EMAIL_RE.match(cleaned):
        raise ValueError("Enter a valid email address.")
    return cleaned


class RegisterRequest(BaseModel):
    """Create an account."""

    model_config = ConfigDict(extra="forbid")

    email: str
    password: Password
    display_name: DisplayName | None = None

    _normalise = field_validator("email")(staticmethod(_normalise_email))


class LoginRequest(BaseModel):
    """Authenticate an existing account."""

    model_config = ConfigDict(extra="forbid")

    email: str
    password: str

    _normalise = field_validator("email")(staticmethod(_normalise_email))


class AuthUser(BaseModel):
    """The authenticated account, as returned to the client. No secrets."""

    id: str
    email: str | None
    display_name: str
    is_demo: bool
    created_at: datetime

    @classmethod
    def from_model(cls, user: User) -> "AuthUser":
        return cls(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            is_demo=user.is_demo,
            created_at=user.created_at,
        )
