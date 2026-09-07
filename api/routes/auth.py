"""Authentication endpoints.

The token is delivered as an **HttpOnly cookie** (ADR-011), not a JSON body:
page JavaScript can never read it, so a cross-site script cannot exfiltrate a
session. The cookie is ``SameSite=Lax`` (the app is same-origin behind the
nginx proxy, so a lax cookie rides normal navigations and same-site fetches but
not cross-site form posts) and ``Secure`` in production. There is no refresh
token in V1.2 — the access token *is* the session, and logout simply clears it.
"""

from __future__ import annotations

from fastapi import APIRouter, Response, status

from app.api.deps import (
    AuthSecretDep,
    AuthServiceDep,
    ClockDep,
    RequireUser,
    SessionDep,
)
from app.core.config import settings
from app.core.security import create_access_token
from app.demo.generator import generate
from app.demo.loader import describe, get_or_create_demo_user, load_demo_data
from app.domain.errors import ValidationError
from app.models.user import User
from app.schemas.auth import AuthUser, LoginRequest, RegisterRequest

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _issue_session(response: Response, user: User, *, secret: str, now) -> None:
    """Mint an access token for ``user`` and attach it as the session cookie."""
    token = create_access_token(
        subject=user.id,
        secret=secret,
        issued_at=now,
        ttl_minutes=settings.access_token_ttl_minutes,
    )
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        max_age=settings.access_token_ttl_minutes * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


@router.post(
    "/register",
    response_model=AuthUser,
    status_code=status.HTTP_201_CREATED,
    summary="Create an account and start a session",
)
def register(
    payload: RegisterRequest,
    response: Response,
    auth: AuthServiceDep,
    clock: ClockDep,
    secret: AuthSecretDep,
) -> AuthUser:
    """Register a new user. On success the caller is logged straight in.

    A brand-new account owns nothing — no expenses, check-ins, events or demo
    data. The first-run experience (Phase 5) is built on exactly this empty
    starting state.
    """
    user = auth.register(
        email=payload.email,
        password=payload.password,
        display_name=payload.display_name,
    )
    _issue_session(response, user, secret=secret, now=clock.now())
    return AuthUser.from_model(user)


@router.post(
    "/login",
    response_model=AuthUser,
    summary="Authenticate and start a session",
)
def login(
    payload: LoginRequest,
    response: Response,
    auth: AuthServiceDep,
    clock: ClockDep,
    secret: AuthSecretDep,
) -> AuthUser:
    """Verify credentials and set the session cookie.

    Invalid credentials return 401 with a single generic message — the response
    never reveals whether the email exists.
    """
    user = auth.authenticate(email=payload.email, password=payload.password)
    _issue_session(response, user, secret=secret, now=clock.now())
    return AuthUser.from_model(user)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="End the session",
)
def logout(response: Response) -> None:
    """Clear the session cookie. Idempotent — logging out twice is fine.

    With no server-side session store there is nothing to invalidate; deleting
    the cookie removes the client's only copy of the token. (A leaked token
    stays valid until it expires — the short lifetime is what bounds that, and
    it is the reason V1.2's token is short-lived; see the ADR.)
    """
    response.delete_cookie(
        key=settings.auth_cookie_name,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


@router.get(
    "/me",
    response_model=AuthUser,
    summary="The current authenticated account",
)
def me(user: RequireUser) -> AuthUser:
    """Return the signed-in account, or 401 if there is no valid session.

    The frontend calls this on load to decide between the app and the login
    screen, and to validate a still-present cookie against an expired token.
    """
    return AuthUser.from_model(user)


@router.post(
    "/demo",
    response_model=AuthUser,
    summary="Enter the shared demo account (passwordless)",
)
def enter_demo(
    session: SessionDep,
    response: Response,
    clock: ClockDep,
    secret: AuthSecretDep,
) -> AuthUser:
    """Start a session as the dedicated demo account, seeding it if empty.

    This is the "Explore demo" path (§9). It is a **separate account** from any
    real user — nobody who signs up ever inherits the demo person's finances,
    and exploring the demo never touches a real user's rows. The account is
    passwordless, so it is reachable only here, never through login.

    Gated by ``AFI_DEMO_MODE`` exactly like the other demo operations: with the
    switch off there is no demo to enter, and the endpoint refuses rather than
    silently creating an empty account.
    """
    if not settings.demo_mode:
        raise ValidationError(
            "Demo mode is disabled. Set AFI_DEMO_MODE=true to enable the demo "
            "account, or use the CLI: python -m app.demo seed"
        )
    user = get_or_create_demo_user(session)
    # Seed on first entry so the demo is never an empty account. Idempotent:
    # once seeded, re-entering leaves the single dataset untouched.
    if describe(session).is_empty:
        load_demo_data(session, generate(clock.today()))
        session.refresh(user)
    _issue_session(response, user, secret=secret, now=clock.now())
    return AuthUser.from_model(user)
