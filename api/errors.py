"""Domain error → HTTP status mapping.

Registered once on the app. Routers therefore contain no ``try/except`` and
no ``raise HTTPException``: they call a service and return the result. The
service decides *what* went wrong; this file decides how that looks over HTTP.
"""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.domain.errors import (
    AuthError,
    ConflictError,
    DomainError,
    NotFoundError,
    ValidationError,
)

#: 422 is spelled as a literal: Starlette renamed its constant for that code
#: and deprecated the old name, so referencing either couples us to a version.
_STATUS_BY_ERROR: dict[type[DomainError], int] = {
    NotFoundError: status.HTTP_404_NOT_FOUND,
    ConflictError: status.HTTP_409_CONFLICT,
    ValidationError: 422,
    AuthError: status.HTTP_401_UNAUTHORIZED,
}


def register_error_handlers(app: FastAPI) -> None:
    """Attach the domain error handler to the application."""

    @app.exception_handler(DomainError)
    async def _handle_domain_error(_: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=_STATUS_BY_ERROR.get(type(exc), status.HTTP_400_BAD_REQUEST),
            content={"detail": exc.message, "error": type(exc).__name__},
        )
