"""Registration and login.

The service owns the account rules; it knows nothing about HTTP, cookies or
tokens (those live in the route). It raises domain errors the API layer maps to
status codes, exactly like every other service — so the isolation guarantee is
uniform: an authenticated user is resolved the same way a profile was, and
every downstream query is still scoped by ``user.id``.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.core.unit_of_work import atomic
from app.domain.errors import AuthError, ConflictError
from app.models.user import User


class AuthService:
    """Creates accounts and verifies credentials."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def register(
        self, *, email: str, password: str, display_name: str | None
    ) -> User:
        """Create a new account, or raise :class:`ConflictError` if the email
        is already taken.

        ``email`` is expected already normalised by the schema. The password is
        hashed with Argon2id and the plaintext is discarded — it is never
        stored, never logged, never held beyond this call.
        """
        if self._find_by_email(email) is not None:
            # Registration legitimately reveals that an email is taken — the
            # user needs to know to log in instead. This is different from
            # login, which stays opaque.
            raise ConflictError("An account with this email already exists.")

        user = User(
            email=email,
            password_hash=hash_password(password),
            display_name=(display_name or _default_display_name(email)),
            is_demo=False,
        )
        # The email pre-check above is friendly, not authoritative: the partial
        # unique index is what actually prevents two accounts racing the same
        # address, and ``atomic`` maps that collision back to the same 409.
        with atomic(self._session):
            self._session.add(user)
        self._session.refresh(user)
        return user

    def authenticate(self, *, email: str, password: str) -> User:
        """Return the account for valid credentials, or raise :class:`AuthError`.

        The error is identical whether the email is unknown or the password is
        wrong, and :func:`verify_password` burns equal time in both cases, so
        neither the message nor the timing distinguishes them. The demo account
        (null hash) can never authenticate here — it is entered by a separate,
        passwordless path.
        """
        user = self._find_by_email(email)
        if not verify_password(password, user.password_hash if user else None):
            raise AuthError("Invalid email or password.")
        assert user is not None  # verify_password is False for a null hash
        return user

    def get_by_id(self, user_id: str) -> User | None:
        """Resolve an account by id, or None. Used to turn a token into a user."""
        return self._session.get(User, user_id)

    def _find_by_email(self, email: str) -> User | None:
        return self._session.scalars(
            select(User).where(User.email == email)
        ).first()


def _default_display_name(email: str) -> str:
    """A friendly default from the email's local part (``ada@x.com`` → ``ada``)."""
    return email.split("@", 1)[0]
