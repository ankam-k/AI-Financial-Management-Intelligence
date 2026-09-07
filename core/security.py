"""Password hashing and access-token minting — the cryptographic primitives.

Two deliberate boundaries:

1. **Nothing here is hand-rolled.** Passwords are hashed with Argon2id via
   ``argon2-cffi``; tokens are JWTs signed with ``PyJWT`` (HS256). ADR-011
   mandates both, and reinventing either is exactly the mistake that makes
   auth code dangerous.

2. **These are pure functions.** They take the secret and the current time as
   arguments rather than reaching for global settings or the wall clock. That
   is what makes them testable against the frozen clock the rest of the suite
   uses, and it keeps the fail-closed secret rule (:func:`resolve_auth_secret`)
   in one place instead of scattered across call sites.

Neither a password nor the signing secret is ever logged. A password never
leaves this module except as a hash; the secret never leaves it at all.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app.core.config import Settings
from app.domain.errors import AuthError

_log = logging.getLogger("app.auth")

#: One hasher instance, reused. Its defaults are Argon2id with the library's
#: current cost parameters — memory-hard, no bcrypt-style input truncation.
_hasher = PasswordHasher()

#: JWT signing algorithm. Symmetric HMAC-SHA256: one secret signs and verifies,
#: which is right for a single-service deployment. RS256 would matter only if a
#: separate party needed to verify without being able to mint.
_ALGORITHM = "HS256"

#: A stable, *obviously* insecure development secret. It exists so a fresh clone
#: runs without configuration; it is never a real secret because it is right
#: here in the source. Production never reaches it — :func:`resolve_auth_secret`
#: fails closed first.
_DEV_INSECURE_SECRET = "afi-development-only-insecure-secret-do-not-use-in-production"

#: A pre-computed hash to verify against when no user matched, so a login for a
#: non-existent email costs the same time as one for a real email. Without it,
#: response timing distinguishes "no such user" from "wrong password".
_DUMMY_HASH = _hasher.hash("timing-equalisation-placeholder")


def resolve_auth_secret(settings: Settings) -> str:
    """Return the JWT signing secret, failing closed in production.

    - An explicit ``AFI_AUTH_SECRET`` is always honoured.
    - In production with no secret set, this raises — the app must not start
      signing tokens with a guessable key.
    - In development with no secret set, a clearly-marked insecure fallback is
      used and a loud warning is emitted. The secret itself is never logged.
    """
    if settings.auth_secret:
        return settings.auth_secret

    if settings.is_production:
        raise RuntimeError(
            "AFI_AUTH_SECRET is not set but AFI_ENVIRONMENT=production. "
            "Refusing to start with a guessable signing key. Generate one with "
            "`python -c \"import secrets; print(secrets.token_urlsafe(48))\"` "
            "and set AFI_AUTH_SECRET."
        )

    _log.warning(
        "AFI_AUTH_SECRET is not set — using the INSECURE development fallback. "
        "This MUST NOT be used in production. Set AFI_AUTH_SECRET and "
        "AFI_ENVIRONMENT=production before deploying."
    )
    return _DEV_INSECURE_SECRET


def hash_password(password: str) -> str:
    """Return an Argon2id hash of ``password``. The plaintext is never stored."""
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    """Return True iff ``password`` matches ``password_hash``.

    When ``password_hash`` is ``None`` (a profile that predates auth, or the
    demo account) verification still burns the same time against a dummy hash,
    then fails — no early return that a timing attacker could measure.
    """
    try:
        _hasher.verify(password_hash or _DUMMY_HASH, password)
        return password_hash is not None
    except (VerifyMismatchError, InvalidHashError):
        return False


def create_access_token(
    *, subject: str, secret: str, issued_at: datetime, ttl_minutes: int
) -> str:
    """Mint a signed access token whose ``sub`` is ``subject`` (the user id).

    ``issued_at`` comes from the injected clock, so token lifetime is
    deterministic in tests rather than tied to the wall clock.
    """
    expires_at = issued_at + timedelta(minutes=ttl_minutes)
    payload = {
        "sub": subject,
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    return jwt.encode(payload, secret, algorithm=_ALGORITHM)


def decode_access_token(token: str, *, secret: str, now: datetime) -> str:
    """Verify ``token`` and return its subject, or raise :class:`AuthError`.

    Expiry is checked explicitly against the injected ``now`` rather than
    PyJWT's wall-clock check, so a frozen-clock test can assert both a valid
    and an expired token deterministically. Every failure — bad signature,
    malformed token, expired — surfaces as the same opaque ``AuthError``: the
    caller learns "not authenticated", never why.
    """
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[_ALGORITHM],
            options={"verify_exp": False},
        )
    except jwt.InvalidTokenError as exc:  # bad signature, malformed, etc.
        raise AuthError("Not authenticated") from exc

    subject = payload.get("sub")
    expiry = payload.get("exp")
    if not isinstance(subject, str) or not isinstance(expiry, (int, float)):
        raise AuthError("Not authenticated")

    if now.timestamp() >= expiry:
        raise AuthError("Session expired")

    return subject
