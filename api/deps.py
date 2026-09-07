"""FastAPI dependencies.

Everything a router needs is assembled here and injected, so a test can swap
the database or freeze the clock without touching a single route.

``get_current_user`` is the authentication seam. It now reads the session token
and resolves the authenticated account (:func:`require_user`); through V1.1 it
returned the single local profile. Nothing downstream changed when it flipped —
routers, services and queries were already written against "the current user"
rather than "the only user", so authentication and per-user isolation composed
without a single query being touched.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.clock import Clock, SystemClock
from app.core.config import settings
from app.core.database import get_session
from app.core.security import decode_access_token, resolve_auth_secret
from app.chat.service import ChatEngine
from app.domain.errors import AuthError
from app.llm.base import LLMClient
from app.llm.factory import build_llm_client
from app.models.user import User
from app.narration.renderer import NarrationRenderer
from app.services.analysis_service import AnalysisService
from app.services.auth_service import AuthService
from app.services.chat_service import ChatService
from app.services.check_in_service import CheckInService
from app.services.expense_service import ExpenseService
from app.services.life_event_service import LifeEventService
from app.services.narration_service import NarrationService
from app.services.profile_service import ProfileService


def get_clock() -> Clock:
    """Return the application clock. Overridden in tests with a fixed clock."""
    return SystemClock()


SessionDep = Annotated[Session, Depends(get_session)]
ClockDep = Annotated[Clock, Depends(get_clock)]


def get_profile_service(session: SessionDep) -> ProfileService:
    return ProfileService(session)


ProfileServiceDep = Annotated[ProfileService, Depends(get_profile_service)]


def get_auth_service(session: SessionDep) -> AuthService:
    return AuthService(session)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def get_auth_secret() -> str:
    """The JWT signing secret, resolved once through the fail-closed rule."""
    return resolve_auth_secret(settings)


AuthSecretDep = Annotated[str, Depends(get_auth_secret)]


def _read_token(request: Request) -> str | None:
    """Extract the access token from the request.

    Preference order: the ``Authorization: Bearer`` header (for API clients and
    tests), then the HttpOnly session cookie (how the browser app sends it).
    """
    header = request.headers.get("Authorization")
    if header and header.lower().startswith("bearer "):
        return header[7:].strip() or None
    return request.cookies.get(settings.auth_cookie_name)


def require_user(
    request: Request,
    auth: AuthServiceDep,
    clock: ClockDep,
    secret: AuthSecretDep,
) -> User:
    """Resolve the authenticated account from the request, or raise 401.

    This is the real authentication seam. A missing token, a bad or expired
    one, or a token whose user no longer exists all raise the same opaque
    :class:`AuthError`. The resolved ``User`` flows into the same service
    methods that already scope every query by ``user.id`` — so authentication
    and isolation compose without any query changing.
    """
    token = _read_token(request)
    if not token:
        raise AuthError("Not authenticated")

    user_id = decode_access_token(token, secret=secret, now=clock.now())
    user = auth.get_by_id(user_id)
    if user is None:
        # The token was validly signed but its subject is gone (deleted
        # account). Treat it as unauthenticated rather than a server error.
        raise AuthError("Not authenticated")
    return user


RequireUser = Annotated[User, Depends(require_user)]


def get_current_user(user: RequireUser) -> User:
    """Resolve the acting user — now the **authenticated** user (V1.2).

    Through V1.1 this returned the single auto-created local profile. It now
    delegates to :func:`require_user`, so every route that depends on
    ``CurrentUser`` became authenticated the moment this one line changed —
    exactly the seam the architecture was built around (see this module's
    docstring). The routes, services and queries did not change: they were
    always written against "the current user", and every query is still scoped
    by ``user.id``.
    """
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_expense_service(session: SessionDep, clock: ClockDep) -> ExpenseService:
    return ExpenseService(session, clock)


def get_check_in_service(session: SessionDep, clock: ClockDep) -> CheckInService:
    return CheckInService(session, clock, backfill_days=settings.checkin_backfill_days)


def get_life_event_service(session: SessionDep, clock: ClockDep) -> LifeEventService:
    return LifeEventService(session, clock)


def get_analysis_service(session: SessionDep, clock: ClockDep) -> AnalysisService:
    return AnalysisService(session, clock)


ExpenseServiceDep = Annotated[ExpenseService, Depends(get_expense_service)]
CheckInServiceDep = Annotated[CheckInService, Depends(get_check_in_service)]
LifeEventServiceDep = Annotated[LifeEventService, Depends(get_life_event_service)]
AnalysisServiceDep = Annotated[AnalysisService, Depends(get_analysis_service)]


def get_llm_client() -> LLMClient:
    """The configured model client. Overridden in tests with a fake.

    Constructed per request rather than once at import: the adapters hold no
    connection, so there is nothing to reuse, and a per-request client keeps a
    configuration change one restart away rather than one deploy away.
    """
    return build_llm_client(settings)


LLMClientDep = Annotated[LLMClient, Depends(get_llm_client)]


def get_narration_service(
    analysis: AnalysisServiceDep, client: LLMClientDep
) -> NarrationService:
    return NarrationService(
        analysis, NarrationRenderer(client, max_generated=settings.llm_max_generated)
    )


NarrationServiceDep = Annotated[NarrationService, Depends(get_narration_service)]


def get_chat_service(analysis: AnalysisServiceDep, client: LLMClientDep) -> ChatService:
    return ChatService(
        analysis,
        NarrationRenderer(client, max_generated=settings.llm_max_generated),
        ChatEngine(client),
    )


ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]
