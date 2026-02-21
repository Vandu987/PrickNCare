"""Request logging + correlation ID middleware — task 3.7.

Every request receives a unique X-Correlation-ID header (UUID4).
Structured JSON log lines capture:
  - Incoming: method, path, query_string, client_ip, user_agent
  - Outgoing: status_code, duration_ms, content_length
  - When available: user_id (stored on request.state by RBAC deps)

Usage::

    app.add_middleware(RequestLoggingMiddleware)
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger("prickncare.request")

CORRELATION_ID_HEADER = "X-Correlation-ID"


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Adds correlation ID + structured request/response logging."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Coroutine[Any, Any, Response]],
    ) -> Response:
        correlation_id = str(uuid.uuid4())
        request.state.correlation_id = correlation_id

        client_ip = self._get_client_ip(request)
        start_time = time.perf_counter()

        logger.info(
            "request_started",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "path": request.url.path,
                "query_string": str(request.url.query),
                "client_ip": client_ip,
                "user_agent": request.headers.get("User-Agent", ""),
            },
        )

        response = await call_next(request)

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        user_id: str | None = getattr(request.state, "user_id", None)

        logger.info(
            "request_finished",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "content_length": response.headers.get("content-length"),
                "user_id": user_id,
            },
        )

        response.headers[CORRELATION_ID_HEADER] = correlation_id
        return response

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
