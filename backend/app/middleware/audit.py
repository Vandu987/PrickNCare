"""Security audit logging middleware — task 3.7.

Records security-relevant events to a dedicated ``prickncare.audit`` logger:
  - All POST / PUT / DELETE requests (data-mutating operations)
  - Authentication events (login, logout, OTP paths)
  - 401 / 403 responses (permission denials)

Each audit record contains:
  correlation_id, user_id, method, path, status_code, client_ip

The audit logger is intentionally separate from the request logger so that
audit records can be routed to a dedicated sink (file, SIEM, database) via
standard Python logging configuration without mixing them with debug noise.

Usage::

    app.add_middleware(AuditMiddleware)
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

audit_logger = logging.getLogger("prickncare.audit")

# Paths that are always audited regardless of HTTP method.
_ALWAYS_AUDIT_PREFIXES: tuple[str, ...] = ("/api/v1/auth/",)

# HTTP methods whose calls are always audited.
_AUDIT_METHODS: frozenset[str] = frozenset({"POST", "PUT", "PATCH", "DELETE"})

# Status codes that trigger an audit entry (security-relevant).
_AUDIT_STATUS_CODES: frozenset[int] = frozenset({401, 403})


class AuditMiddleware(BaseHTTPMiddleware):
    """Logs security-relevant requests to the ``prickncare.audit`` logger."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Coroutine[Any, Any, Response]],
    ) -> Response:
        response = await call_next(request)

        if self._should_audit(request, response):
            self._write_audit(request, response)

        return response

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _should_audit(request: Request, response: Response) -> bool:
        method = request.method.upper()
        path = request.url.path

        if method in _AUDIT_METHODS:
            return True
        if any(path.startswith(p) for p in _ALWAYS_AUDIT_PREFIXES):
            return True
        if response.status_code in _AUDIT_STATUS_CODES:
            return True
        return False

    @staticmethod
    def _write_audit(request: Request, response: Response) -> None:
        correlation_id: str | None = getattr(request.state, "correlation_id", None)
        user_id: str | None = getattr(request.state, "user_id", None)

        forwarded_for = request.headers.get("X-Forwarded-For")
        client_ip = (
            forwarded_for.split(",")[0].strip()
            if forwarded_for
            else (request.client.host if request.client else "unknown")
        )

        audit_logger.info(
            "audit_event",
            extra={
                "correlation_id": correlation_id,
                "user_id": user_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "client_ip": client_ip,
            },
        )
