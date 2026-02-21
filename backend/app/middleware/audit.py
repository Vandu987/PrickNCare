"""Security audit logging middleware — task 16.1.

Records security-relevant events to both a Python logger and the database:
  - All POST / PUT / DELETE / PATCH requests (data-mutating operations)
  - Authentication events (login, logout, OTP paths)
  - 401 / 403 responses (permission denials)

Database writes are fire-and-forget (background task) so they never block the
response pipeline.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.database import get_session_factory
from app.services.audit import AuditService

audit_logger = logging.getLogger("prickncare.audit")

# Paths that are always audited regardless of HTTP method.
_ALWAYS_AUDIT_PREFIXES: tuple[str, ...] = ("/api/v1/auth/",)

# HTTP methods whose calls are always audited.
_AUDIT_METHODS: frozenset[str] = frozenset({"POST", "PUT", "PATCH", "DELETE"})

# Status codes that trigger an audit entry (security-relevant).
_AUDIT_STATUS_CODES: frozenset[int] = frozenset({401, 403})


def _derive_action(method: str, path: str) -> str:
    """Derive a human-readable action from method + path."""
    method = method.upper()
    if "/auth/" in path:
        if "login" in path or "otp" in path:
            return "login"
        if "logout" in path:
            return "logout"
        return "auth"
    return {
        "POST": "create",
        "PUT": "update",
        "PATCH": "update",
        "DELETE": "delete",
    }.get(method, method.lower())


def _derive_entity_type(path: str) -> str:
    """Extract entity type from the URL path (best-effort)."""
    parts = [p for p in path.strip("/").split("/") if p]
    # Skip api/v1 prefix segments
    for i, part in enumerate(parts):
        if part == "v1" and i + 1 < len(parts):
            return parts[i + 1].rstrip("s").capitalize()
    return parts[-1].capitalize() if parts else "Unknown"


class AuditMiddleware(BaseHTTPMiddleware):
    """Logs security-relevant requests to logger and database."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Coroutine[Any, Any, Response]],
    ) -> Response:
        response = await call_next(request)

        if self._should_audit(request, response):
            self._write_log(request, response)
            asyncio.create_task(self._write_db(request, response))

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
    def _get_client_ip(request: Request) -> str:
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    @staticmethod
    def _write_log(request: Request, response: Response) -> None:
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

    @staticmethod
    async def _write_db(request: Request, response: Response) -> None:
        """Fire-and-forget database write in a separate session."""
        try:
            factory = get_session_factory()
            if factory is None:
                return
            async with factory() as session:
                svc = AuditService(session=session)
                user_id = getattr(request.state, "user_id", None)

                forwarded_for = request.headers.get("X-Forwarded-For")
                client_ip = (
                    forwarded_for.split(",")[0].strip()
                    if forwarded_for
                    else (request.client.host if request.client else "unknown")
                )

                await svc.log(
                    action=_derive_action(request.method, request.url.path),
                    entity_type=_derive_entity_type(request.url.path),
                    request_method=request.method,
                    request_path=request.url.path,
                    response_status=response.status_code,
                    user_id=user_id,
                    ip_address=client_ip,
                    user_agent=request.headers.get("User-Agent"),
                )
                await session.commit()
        except Exception:
            audit_logger.exception("Failed to persist audit log to database")
