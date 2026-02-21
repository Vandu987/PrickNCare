"""Centralised exception handlers — task 3.7.

Registers handlers on the FastAPI app that convert all unhandled exceptions
into a consistent JSON envelope::

    {
        "error": {
            "code":    "VALIDATION_ERROR",
            "message": "Human-readable summary",
            "details": { ... }   # only when additional context is safe to expose
        },
        "correlation_id": "<uuid>"   # echoed from request.state when available
    }

Sensitive data (passwords, tokens, full stack traces) is logged server-side but
never returned to callers.

Usage::

    from app.middleware.error_handler import register_exception_handlers
    register_exception_handlers(app)
"""

from __future__ import annotations

import logging
import traceback

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("prickncare.error")

# ---------------------------------------------------------------------------
# Response builder
# ---------------------------------------------------------------------------


def _error_response(
    request: Request,
    status_code: int,
    code: str,
    message: str,
    details: dict | None = None,
) -> JSONResponse:
    correlation_id: str | None = getattr(request.state, "correlation_id", None)
    body: dict = {
        "error": {
            "code": code,
            "message": message,
        }
    }
    if details:
        body["error"]["details"] = details
    if correlation_id:
        body["correlation_id"] = correlation_id
    return JSONResponse(status_code=status_code, content=body)


# ---------------------------------------------------------------------------
# Individual handlers
# ---------------------------------------------------------------------------


async def _http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Handle HTTPException (raised by FastAPI/Starlette and our own code)."""
    code = _status_to_code(exc.status_code)
    logger.warning(
        "http_exception",
        extra={
            "correlation_id": getattr(request.state, "correlation_id", None),
            "status_code": exc.status_code,
            "detail": exc.detail,
            "path": request.url.path,
        },
    )
    return _error_response(request, exc.status_code, code, str(exc.detail))


async def _validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic request validation errors (422)."""
    # Flatten validation errors into a safe list — no raw input values.
    field_errors = [
        {"field": ".".join(str(p) for p in err["loc"]), "msg": err["msg"]}
        for err in exc.errors()
    ]
    logger.warning(
        "validation_error",
        extra={
            "correlation_id": getattr(request.state, "correlation_id", None),
            "path": request.url.path,
            "errors": field_errors,
        },
    )
    return _error_response(
        request,
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        "VALIDATION_ERROR",
        "Request validation failed",
        details={"fields": field_errors},
    )


async def _unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Catch-all for unexpected server errors (500)."""
    correlation_id: str | None = getattr(request.state, "correlation_id", None)
    # Log full traceback server-side; never expose it to the caller.
    logger.error(
        "unhandled_exception",
        extra={
            "correlation_id": correlation_id,
            "path": request.url.path,
            "exc_type": type(exc).__name__,
            "traceback": traceback.format_exc(),
        },
    )
    return _error_response(
        request,
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "INTERNAL_SERVER_ERROR",
        "An unexpected error occurred. Please try again later.",
    )


# ---------------------------------------------------------------------------
# Registration helper
# ---------------------------------------------------------------------------


def register_exception_handlers(app: FastAPI) -> None:
    """Attach all exception handlers to *app*."""
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)
    app.add_exception_handler(RequestValidationError, _validation_exception_handler)
    app.add_exception_handler(Exception, _unhandled_exception_handler)


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def _status_to_code(status_code: int) -> str:
    """Map common HTTP status codes to short string codes."""
    _MAP = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        429: "TOO_MANY_REQUESTS",
        500: "INTERNAL_SERVER_ERROR",
        502: "BAD_GATEWAY",
        503: "SERVICE_UNAVAILABLE",
    }
    return _MAP.get(status_code, f"HTTP_{status_code}")
